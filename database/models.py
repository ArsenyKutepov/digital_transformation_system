import json
from .connection import DatabaseConnection


class Organization:
    """Модель организации"""

    @staticmethod
    def create(name: str, description: str = "", org_type: str = "average") -> int:
        db = DatabaseConnection()
        return db.execute(
            "INSERT INTO organizations (name, description, organization_type) VALUES (?, ?, ?)",
            (name, description, org_type)
        )

    @staticmethod
    def get_all():
        db = DatabaseConnection()
        return db.query("SELECT * FROM organizations ORDER BY created_at DESC")

    @staticmethod
    def get_by_id(org_id: int):
        db = DatabaseConnection()
        return db.query_one("SELECT * FROM organizations WHERE id = ?", (org_id,))

    @staticmethod
    def update(org_id: int, name: str = None, description: str = None, org_type: str = None):
        db = DatabaseConnection()
        updates = []
        params = []
        if name:
            updates.append("name = ?")
            params.append(name)
        if description:
            updates.append("description = ?")
            params.append(description)
        if org_type:
            updates.append("organization_type = ?")
            params.append(org_type)
        if updates:
            params.append(org_id)
            db.execute(f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?", tuple(params))

    @staticmethod
    def delete(org_id: int):
        db = DatabaseConnection()
        # Сначала удаляем связанные оценки
        assessments = Assessment.get_by_org(org_id)
        for assessment in assessments:
            db.execute("DELETE FROM assessment_details WHERE assessment_id = ?", (assessment['id'],))
            db.execute("DELETE FROM assessments WHERE id = ?", (assessment['id'],))
        # Затем удаляем организацию
        db.execute("DELETE FROM organizations WHERE id = ?", (org_id,))


class Assessment:
    """Модель оценки цифровой зрелости"""

    @staticmethod
    def create(org_id: int, final_score: float, technical: float, cognitive: float,
               personal: float, details: dict) -> int:
        db = DatabaseConnection()

        assessment_id = db.execute(
            """INSERT INTO assessments (org_id, final_score, technical_factor, 
               cognitive_factor, personal_factor) VALUES (?, ?, ?, ?, ?)""",
            (org_id, final_score, technical, cognitive, personal)
        )

        for code, value in details.items():
            db.execute(
                "INSERT INTO assessment_details (assessment_id, indicator_code, value) VALUES (?, ?, ?)",
                (assessment_id, code, value)
            )

        return assessment_id

    @staticmethod
    def get_by_org(org_id: int, limit: int = 10):
        db = DatabaseConnection()
        assessments = db.query(
            """SELECT * FROM assessments WHERE org_id = ? 
               ORDER BY assessment_date DESC LIMIT ?""",
            (org_id, limit)
        )

        for assessment in assessments:
            details = db.query(
                "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
                (assessment['id'],)
            )
            assessment['details'] = {row['indicator_code']: row['value'] for row in details}

        return assessments

    @staticmethod
    def get_by_id(assessment_id: int):
        db = DatabaseConnection()
        assessment = db.query_one("SELECT * FROM assessments WHERE id = ?", (assessment_id,))
        if assessment:
            details = db.query(
                "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
                (assessment_id,)
            )
            assessment['details'] = {row['indicator_code']: row['value'] for row in details}
        return assessment

    @staticmethod
    def get_latest(org_id: int, user_id: int = None):
        if user_id:
            db = DatabaseConnection()
            result = db.query_one(
                """SELECT * FROM assessments WHERE org_id = ? AND user_id = ? 
                   ORDER BY assessment_date DESC LIMIT 1""",
                (org_id, user_id)
            )
            return result
        else:
            assessments = Assessment.get_by_org(org_id, 1)
            return assessments[0] if assessments else None

    @staticmethod
    def delete(assessment_id: int):
        db = DatabaseConnection()
        db.execute("DELETE FROM assessment_details WHERE assessment_id = ?", (assessment_id,))
        db.execute("DELETE FROM assessments WHERE id = ?", (assessment_id,))


class Action:
    """Модель действия (проекта цифровой трансформации)"""

    _cache = None

    @staticmethod
    def get_all():
        if Action._cache is not None:
            return Action._cache

        db = DatabaseConnection()
        actions = db.query("SELECT * FROM actions ORDER BY id")
        Action._cache = actions
        return actions

    @staticmethod
    def get_by_id(action_id: int):
        actions = Action.get_all()
        return next((a for a in actions if a['id'] == action_id), None)

    @staticmethod
    def create(name: str, base_growth: float, cost: float, risk: float,
               inertia_shock: float, cognitive_load: float, description: str = "",
               resource_type: str = "financial"):
        db = DatabaseConnection()
        action_id = db.execute(
            """INSERT INTO actions (name, description, base_growth, cost, risk, 
               inertia_shock, cognitive_load, resource_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, description, base_growth, cost, risk, inertia_shock, cognitive_load, resource_type)
        )
        Action._cache = None  # Инвалидация кэша
        return action_id

    @staticmethod
    def initialize_default_actions():
        """Инициализация стандартных действий (25 проектов)"""
        db = DatabaseConnection()

        # Проверяем, есть ли уже данные
        existing = db.query("SELECT COUNT(*) as cnt FROM actions")
        if existing and existing[0]['cnt'] > 0:
            return

        actions_data = [
            ("Внедрение системы электронного документооборота", "", 0.12, 0.15, 0.10, 0.25, 0.20, "financial"),
            ("Создание цифрового портфолио студента", "", 0.10, 0.10, 0.08, 0.15, 0.15, "human"),
            ("Разработка онлайн-курсов по цифровым компетенциям", "", 0.15, 0.20, 0.12, 0.20, 0.30, "human"),
            ("Автоматизация приёмной комиссии", "", 0.08, 0.12, 0.15, 0.30, 0.18, "financial"),
            ("Внедрение LMS для поддержки образовательного процесса", "", 0.14, 0.18, 0.10, 0.22, 0.25, "financial"),
            ("Развёртывание аналитической платформы данных", "", 0.11, 0.22, 0.18, 0.28, 0.22, "temporal"),
            ("Цифровая трансформация HR-процессов", "", 0.09, 0.14, 0.12, 0.18, 0.16, "human"),
            ("Внедрение ИИ-ассистента для студентов", "", 0.13, 0.16, 0.14, 0.25, 0.28, "technological"),
            ("Создание единой цифровой среды (экосистемы)", "", 0.20, 0.30, 0.25, 0.35, 0.35, "complex"),
            ("Стандартизация API для интеграции сервисов", "", 0.07, 0.08, 0.05, 0.10, 0.12, "technological"),
            ("Обучение персонала цифровым компетенциям (массовое)", "", 0.18, 0.25, 0.08, 0.12, 0.40, "human"),
            ("Автоматизация учёта нагрузки преподавателей", "", 0.06, 0.10, 0.10, 0.20, 0.10, "temporal"),
            ("Внедрение системы управления проектами", "", 0.08, 0.12, 0.12, 0.22, 0.14, "financial"),
            ("Разработка мобильного приложения для студентов", "", 0.10, 0.14, 0.09, 0.18, 0.20, "technological"),
            ("Создание виртуальных лабораторий", "", 0.12, 0.20, 0.15, 0.20, 0.25, "financial"),
            ("Внедрение системы менеджмента качества (цифровой)", "", 0.09, 0.15, 0.13, 0.20, 0.15, "human"),
            ("Цифровизация библиотеки и доступа к ресурсам", "", 0.07, 0.10, 0.08, 0.12, 0.12, "financial"),
            ("Автоматизация расписания и управления аудиториями", "", 0.08, 0.11, 0.10, 0.18, 0.13, "temporal"),
            ("Внедрение системы сбора обратной связи", "", 0.06, 0.08, 0.07, 0.14, 0.10, "technological"),
            ("Создание цифровых двойников процессов", "", 0.16, 0.28, 0.20, 0.30, 0.28, "technological"),
            ("Миграция в облачную инфраструктуру", "", 0.11, 0.20, 0.14, 0.20, 0.18, "financial"),
            ("Внедрение кибербезопасности нового поколения", "", 0.09, 0.18, 0.18, 0.22, 0.20, "technological"),
            ("Разработка стратегии управления данными", "", 0.13, 0.16, 0.10, 0.15, 0.12, "human"),
            ("Создание центра цифровых компетенций", "", 0.17, 0.22, 0.12, 0.18, 0.30, "human"),
            ("Внедрение Robotic Process Automation", "", 0.14, 0.24, 0.16, 0.25, 0.24, "technological")
        ]

        for action in actions_data:
            db.execute(
                """INSERT INTO actions (name, description, base_growth, cost, risk, 
                   inertia_shock, cognitive_load, resource_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                action
            )


class TransformationPlan:
    """Модель плана трансформации (результат DQN)"""

    @staticmethod
    def create(org_id: int, total_reward: float, final_maturity: float,
               peak_inertia: float, success: bool, plan_data: list) -> int:
        db = DatabaseConnection()
        plan_id = db.execute(
            """INSERT INTO transformation_plans (org_id, total_reward, final_maturity, 
               peak_inertia, success, plan_data) VALUES (?, ?, ?, ?, ?, ?)""",
            (org_id, total_reward, final_maturity, peak_inertia, 1 if success else 0, json.dumps(plan_data))
        )
        return plan_id

    @staticmethod
    def get_by_org(org_id: int, user_id: int = None, limit: int = 10):
        db = DatabaseConnection()

        # Если передан user_id, проверяем принадлежность организации пользователю
        if user_id:
            # Проверяем, имеет ли пользователь доступ к организации
            # Получаем организации, которые создал пользователь или где он является участником
            user_orgs = db.query(
                "SELECT org_id FROM assessments WHERE user_id = ? GROUP BY org_id",
                (user_id,)
            )
            user_org_ids = [o['org_id'] for o in user_orgs]

            if org_id not in user_org_ids:
                # Пользователь не имеет доступа к этой организации
                return []

        assessments = db.query(
            "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT ?",
            (org_id, limit)
        )

        for assessment in assessments:
            details = db.query(
                "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
                (assessment['id'],)
            )
            assessment['details'] = {d['indicator_code']: d['value'] for d in details}

        return assessments

    @staticmethod
    def add_state(plan_id: int, step: int, zreal: str, resources: float,
                  inertia: float, cognitive_load: float, action_id: int, reward: float):
        db = DatabaseConnection()
        db.execute(
            """INSERT INTO state_history (plan_id, step, zreal, resources, inertia, 
               cognitive_load, action_id, reward) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (plan_id, step, zreal, resources, inertia, cognitive_load, action_id, reward)
        )