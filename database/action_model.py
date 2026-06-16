import json
from .connection import DatabaseConnection


class ActionModel:
    """Модель действий с расширенной информацией"""

    _cache = None

    @staticmethod
    def get_all():
        if ActionModel._cache is not None:
            return ActionModel._cache

        db = DatabaseConnection()
        actions = db.query("SELECT * FROM actions ORDER BY id")

        # Добавляем расширенную информацию
        for action in actions:
            extended = db.query_one("SELECT * FROM actions_extended WHERE action_id = ?", (action['id'],))
            if extended:
                action['description'] = extended.get('description', '')
                action['timeframe'] = extended.get('timeframe', '')
                action['prerequisites'] = json.loads(extended.get('prerequisites', '[]'))
                action['success_criteria'] = json.loads(extended.get('success_criteria', '[]'))
                action['affected_indicators'] = json.loads(extended.get('affected_indicators', '[]'))
                action['detailed_instructions'] = extended.get('detailed_instructions', '')
            else:
                action['description'] = action.get('description', '')
                action['timeframe'] = '1-2 месяца'
                action['prerequisites'] = []
                action['success_criteria'] = []
                action['affected_indicators'] = []
                action['detailed_instructions'] = ''

        ActionModel._cache = actions
        return actions

    @staticmethod
    def get_by_id(action_id: int):
        actions = ActionModel.get_all()
        return next((a for a in actions if a['id'] == action_id), None)

    @staticmethod
    def update_extended(action_id: int, description: str = None, timeframe: str = None,
                        prerequisites: list = None, success_criteria: list = None,
                        affected_indicators: list = None, detailed_instructions: str = None):
        """Обновление расширенной информации о действии (для админа)"""
        db = DatabaseConnection()

        existing = db.query_one("SELECT * FROM actions_extended WHERE action_id = ?", (action_id,))

        if existing:
            updates = []
            params = []
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if timeframe is not None:
                updates.append("timeframe = ?")
                params.append(timeframe)
            if prerequisites is not None:
                updates.append("prerequisites = ?")
                params.append(json.dumps(prerequisites, ensure_ascii=False))
            if success_criteria is not None:
                updates.append("success_criteria = ?")
                params.append(json.dumps(success_criteria, ensure_ascii=False))
            if affected_indicators is not None:
                updates.append("affected_indicators = ?")
                params.append(json.dumps(affected_indicators, ensure_ascii=False))
            if detailed_instructions is not None:
                updates.append("detailed_instructions = ?")
                params.append(detailed_instructions)

            if updates:
                params.append(action_id)
                db.execute(f"UPDATE actions_extended SET {', '.join(updates)} WHERE action_id = ?", tuple(params))
        else:
            db.execute(
                '''INSERT INTO actions_extended 
                   (action_id, description, timeframe, prerequisites, success_criteria, affected_indicators, detailed_instructions) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (action_id, description or '', timeframe or '1-2 месяца',
                 json.dumps(prerequisites or [], ensure_ascii=False),
                 json.dumps(success_criteria or [], ensure_ascii=False),
                 json.dumps(affected_indicators or [], ensure_ascii=False),
                 detailed_instructions or '')
            )

        ActionModel._cache = None  # Инвалидация кэша

    @staticmethod
    def initialize_extended_data():
        """Инициализация расширенных данных для всех действий"""
        actions = ActionModel.get_all()

        extended_data = {
            1: {
                'description': 'Автоматизация процессов создания, согласования, хранения и поиска документов',
                'timeframe': '1-2 месяца',
                'prerequisites': ['Назначен ответственный за СЭД', 'Проведён аудит документооборота'],
                'success_criteria': ['Сокращение времени согласования на 70%', '100% документов в электронном виде'],
                'affected_indicators': ['4.3 Степень автоматизации', '8.2 Развитость сервисов']
            },
            2: {
                'description': 'Создание системы для сбора и анализа достижений студентов (проекты, курсы, олимпиады)',
                'timeframe': '2-3 месяца',
                'prerequisites': ['Разработаны критерии оценки достижений', 'Обучены ответственные'],
                'success_criteria': ['80% студентов имеют портфолио', 'Упрощён отбор на программы'],
                'affected_indicators': ['5.1 Участие в создании продуктов', '6.2 Цифровизация траекторий']
            },
            3: {
                'description': 'Разработка и внедрение онлайн-курсов по цифровым компетенциям для всех сотрудников',
                'timeframe': '3-4 месяца',
                'prerequisites': ['Определены целевые компетенции', 'Привлечены эксперты'],
                'success_criteria': ['80% сотрудников прошли обучение', 'Рост цифровых компетенций'],
                'affected_indicators': ['2.1 Компетенции', '2.2 Владение инструментами']
            },
            # ... добавить для всех 25 действий
        }

        for action in actions:
            if action['id'] in extended_data:
                data = extended_data[action['id']]
                ActionModel.update_extended(
                    action['id'],
                    description=data['description'],
                    timeframe=data['timeframe'],
                    prerequisites=data['prerequisites'],
                    success_criteria=data['success_criteria'],
                    affected_indicators=data['affected_indicators']
                )

    @staticmethod
    def get_completed(org_id: int) -> list:
        """Получение списка выполненных действий для организации"""
        db = DatabaseConnection()
        return db.query(
            "SELECT action_id, completed_date, actual_growth, notes FROM completed_actions WHERE org_id = ?",
            (org_id,)
        )

    @staticmethod
    def mark_completed(org_id: int, action_id: int, actual_growth: float = None,
                       actual_cost: float = None, notes: str = None):
        """Отметка действия как выполненного"""
        db = DatabaseConnection()
        return db.execute(
            '''INSERT INTO completed_actions (org_id, action_id, actual_growth, actual_cost, notes) 
               VALUES (?, ?, ?, ?, ?)''',
            (org_id, action_id, actual_growth, actual_cost, notes)
        )
