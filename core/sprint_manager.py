import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database.connection import DatabaseConnection


class SprintManager:
    """Управление спринтами для пошаговой реализации плана"""

    def __init__(self):
        self.db = DatabaseConnection()

    def create_sprints_from_plan(self, plan_id: int, actions: List[Dict],
                                 start_date: datetime = None) -> List[int]:
        """Создание спринтов из плана действий, возвращает список ID созданных спринтов"""
        if start_date is None:
            start_date = datetime.now()

        settings = self._get_settings()
        sprint_weeks = int(settings.get('sprint_default_weeks', 2))
        sprint_duration = timedelta(weeks=sprint_weeks)

        sprints_ids = []
        current_date = start_date

        # Группируем действия в спринты (по 1-2 действия на спринт)
        actions_per_sprint = 2
        for i in range(0, len(actions), actions_per_sprint):
            sprint_actions = actions[i:i + actions_per_sprint]
            action_ids = [a.get('action_id', a.get('id')) for a in sprint_actions]
            planned_growth = sum(a.get('base_growth_raw', float(a.get('base_growth', 0))) for a in sprint_actions)

            sprint_id = self.db.execute(
                '''INSERT INTO sprints 
                   (plan_id, number, action_ids, planned_start, planned_end, planned_growth, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (plan_id, i // actions_per_sprint + 1,
                 json.dumps(action_ids),
                 current_date.strftime('%Y-%m-%d'),
                 (current_date + sprint_duration).strftime('%Y-%m-%d'),
                 planned_growth, 'planned')
            )
            sprints_ids.append(sprint_id)
            current_date += sprint_duration

        return sprints_ids

    def start_sprint(self, sprint_id: int) -> bool:
        """Начало спринта"""
        sprint = self.db.query_one("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        if not sprint or sprint['status'] != 'planned':
            return False

        self.db.execute(
            "UPDATE sprints SET actual_start = ?, status = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d'), 'active', sprint_id)
        )

        # Создаём уведомление о начале спринта
        plan = self.db.query_one("SELECT org_id FROM transformation_plans WHERE id = ?", (sprint['plan_id'],))
        if plan:
            self._create_notification(
                user_id=None,
                title=f"Спринт {sprint['number']} начат",
                message=f"Начало спринта {sprint['number']}. Запланированные действия: {sprint['action_ids']}",
                type='sprint_start',
                related_entity_type='sprint',
                related_entity_id=sprint_id
            )

        return True

    def complete_sprint(self, sprint_id: int, actual_growth: float,
                        notes: str = None) -> bool:
        """Завершение спринта с вводом фактических результатов"""
        sprint = self.db.query_one("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        if not sprint or sprint['status'] != 'active':
            return False

        action_ids = json.loads(sprint['action_ids'])

        # Обновляем спринт
        self.db.execute(
            """UPDATE sprints 
               SET actual_end = ?, actual_growth = ?, status = ?, notes = ? 
               WHERE id = ?""",
            (datetime.now().strftime('%Y-%m-%d'), actual_growth, 'completed', notes, sprint_id)
        )

        # Отмечаем действия как выполненные
        for action_id in action_ids:
            self.db.execute(
                """INSERT INTO completed_actions (org_id, action_id, sprint_id, actual_growth, notes)
                   SELECT org_id, ?, ?, ?, ? FROM transformation_plans WHERE id = ?""",
                (action_id, sprint_id, actual_growth, notes, sprint['plan_id'])
            )

        # Проверяем отклонение от плана
        deviation = actual_growth - sprint['planned_growth']

        # Создаём уведомление о завершении
        self._create_notification(
            user_id=None,
            title=f"Спринт {sprint['number']} завершён",
            message=f"Фактический рост: {actual_growth:.1f}%. Отклонение от плана: {deviation:+.1f}%",
            type='sprint_complete',
            related_entity_type='sprint',
            related_entity_id=sprint_id
        )

        return True

    def get_active_sprint(self, plan_id: int) -> Optional[Dict]:
        """Получение активного спринта для плана"""
        return self.db.query_one(
            "SELECT * FROM sprints WHERE plan_id = ? AND status = 'active'",
            (plan_id,)
        )

    def get_upcoming_sprints(self, plan_id: int, days_ahead: int = 7) -> List[Dict]:
        """Получение предстоящих спринтов"""
        today = datetime.now().strftime('%Y-%m-%d')
        future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        return self.db.query(
            """SELECT * FROM sprints 
               WHERE plan_id = ? AND status = 'planned' 
               AND planned_start BETWEEN ? AND ?
               ORDER BY planned_start""",
            (plan_id, today, future_date)
        )

    def get_sprint_history(self, plan_id: int) -> List[Dict]:
        """Получение истории спринтов для плана"""
        return self.db.query(
            "SELECT * FROM sprints WHERE plan_id = ? ORDER BY number",
            (plan_id,)
        )

    def reschedule_remaining_sprints(self, plan_id: int, new_start_date: datetime) -> bool:
        """Перенос оставшихся спринтов после отклонения"""
        remaining = self.db.query(
            "SELECT * FROM sprints WHERE plan_id = ? AND status = 'planned' ORDER BY number",
            (plan_id,)
        )

        current_date = new_start_date
        settings = self._get_settings()
        sprint_weeks = int(settings.get('sprint_default_weeks', 2))
        sprint_duration = timedelta(weeks=sprint_weeks)

        for sprint in remaining:
            self.db.execute(
                "UPDATE sprints SET planned_start = ?, planned_end = ? WHERE id = ?",
                (current_date.strftime('%Y-%m-%d'),
                 (current_date + sprint_duration).strftime('%Y-%m-%d'),
                 sprint['id'])
            )
            current_date += sprint_duration

        return True

    def _get_settings(self) -> Dict:
        """Получение системных настроек"""
        settings = self.db.query("SELECT setting_key, setting_value FROM system_settings")
        return {s['setting_key']: s['setting_value'] for s in settings}

    def _create_notification(self, user_id: int = None, title: str = "",
                             message: str = "", type: str = "",
                             related_entity_type: str = None,
                             related_entity_id: int = None):
        """Создание уведомления"""
        if user_id is None:
            # Рассылаем всем аналитикам и администраторам
            users = self.db.query("SELECT id FROM users WHERE role IN ('admin', 'analyst')")
            for user in users:
                self.db.execute(
                    '''INSERT INTO notifications 
                       (user_id, title, message, type, related_entity_type, related_entity_id) 
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (user['id'], title, message, type, related_entity_type, related_entity_id)
                )
        else:
            self.db.execute(
                '''INSERT INTO notifications 
                   (user_id, title, message, type, related_entity_type, related_entity_id) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, title, message, type, related_entity_type, related_entity_id)
            )

    def check_overdue_sprints(self) -> List[Dict]:
        """Проверка просроченных спринтов"""
        today = datetime.now().strftime('%Y-%m-%d')
        overdue = self.db.query(
            "SELECT * FROM sprints WHERE status = 'active' AND planned_end < ?",
            (today,)
        )

        for sprint in overdue:
            self._create_notification(
                title=f"Спринт {sprint['number']} просрочен!",
                message=f"Спринт {sprint['number']} должен был закончиться {sprint['planned_end']}. Пожалуйста, завершите его.",
                type='sprint_overdue',
                related_entity_type='sprint',
                related_entity_id=sprint['id']
            )

        return overdue