from datetime import datetime, timedelta
from database.connection import DatabaseConnection


class NotificationManager:
    """Управление уведомлениями пользователей"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_unread_count(self, user_id: int) -> int:
        """Количество непрочитанных уведомлений"""
        result = self.db.query_one(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )
        return result['cnt'] if result else 0

    def get_notifications(self, user_id: int, limit: int = 20) -> list:
        """Получение уведомлений пользователя"""
        return self.db.query(
            """SELECT * FROM notifications 
               WHERE user_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        )

    def mark_as_read(self, notification_id: int) -> bool:
        """Отметить уведомление как прочитанное"""
        self.db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        return True

    def mark_all_as_read(self, user_id: int) -> bool:
        """Отметить все уведомления как прочитанные"""
        self.db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        return True

    def send_sprint_reminders(self):
        """Отправка напоминаний о предстоящих спринтах"""
        settings = self.db.query("SELECT setting_key, setting_value FROM system_settings")
        settings_dict = {s['setting_key']: s['setting_value'] for s in settings}

        if settings_dict.get('notification_enabled', 'true') != 'true':
            return

        days_before = int(settings_dict.get('notification_days_before', 3))
        target_date = (datetime.now() + timedelta(days=days_before)).strftime('%Y-%m-%d')

        upcoming_sprints = self.db.query(
            """SELECT s.*, p.org_id, o.name as org_name 
               FROM sprints s
               JOIN transformation_plans p ON s.plan_id = p.id
               JOIN organizations o ON p.org_id = o.id
               WHERE s.status = 'planned' AND s.planned_start = ?""",
            (target_date,)
        )

        for sprint in upcoming_sprints:
            users = self.db.query("SELECT id FROM users WHERE role IN ('admin', 'analyst')")
            for user in users:
                self.db.execute(
                    '''INSERT INTO notifications 
                       (user_id, title, message, type, related_entity_type, related_entity_id) 
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (user['id'],
                     f"Спринт {sprint['number']} начинается {sprint['planned_start']}",
                     f"По плану для организации '{sprint['org_name']}' через {days_before} дня начинается спринт {sprint['number']}.",
                     'sprint_reminder',
                     'sprint',
                     sprint['id'])
                )

    def delete_notification(self, notification_id: int) -> bool:
        """Удаление уведомления"""
        self.db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        return True