import json
from database.connection import DatabaseConnection


class PlanTemplates:
    """Управление шаблонами дорожных карт"""

    def __init__(self):
        self.db = DatabaseConnection()

    def save_as_template(self, plan_id: int, template_name: str, description: str = "") -> int:
        """Сохранение плана как шаблона"""
        plan = self.db.query_one("SELECT * FROM transformation_plans WHERE id = ?", (plan_id,))
        if not plan:
            return 0

        org = self.db.query_one("SELECT industry FROM organizations WHERE id = ?", (plan['org_id'],))
        industry = org['industry'] if org else None

        template_id = self.db.execute(
            """INSERT INTO plan_templates (name, description, industry_code, plan_data, created_by) 
               VALUES (?, ?, ?, ?, ?)""",
            (template_name, description, industry, plan['plan_data'], plan['user_id'])
        )

        return template_id

    def get_templates(self, industry_code: str = None) -> list:
        """Получение списка шаблонов"""
        if industry_code:
            templates = self.db.query(
                "SELECT * FROM plan_templates WHERE industry_code = ? ORDER BY usage_count DESC",
                (industry_code,)
            )
        else:
            templates = self.db.query("SELECT * FROM plan_templates ORDER BY usage_count DESC")

        for t in templates:
            t['plan_data'] = json.loads(t['plan_data']) if t['plan_data'] else []

        return templates

    def apply_template(self, template_id: int, org_id: int) -> int:
        """Применение шаблона к организации"""
        template = self.db.query_one("SELECT * FROM plan_templates WHERE id = ?", (template_id,))
        if not template:
            return 0

        # Создаём новый план на основе шаблона
        plan_id = self.db.execute(
            """INSERT INTO transformation_plans (org_id, user_id, plan_data, status, is_template) 
               VALUES (?, ?, ?, ?, ?)""",
            (org_id, None, template['plan_data'], 'active', 0)
        )

        # Увеличиваем счётчик использования шаблона
        self.db.execute(
            "UPDATE plan_templates SET usage_count = usage_count + 1 WHERE id = ?",
            (template_id,)
        )

        return plan_id

    def get_template_recommendations(self, org_id: int, limit: int = 3) -> list:
        """Рекомендация шаблонов на основе отрасли и текущего уровня ЦЗ"""
        org = self.db.query_one("SELECT industry FROM organizations WHERE id = ?", (org_id,))
        if not org:
            return []

        assessment = self.db.query_one(
            "SELECT final_score FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )
        current_score = assessment['final_score'] if assessment else 50

        # Получаем шаблоны той же отрасли
        templates = self.db.query(
            "SELECT * FROM plan_templates WHERE industry_code = ? ORDER BY usage_count DESC",
            (org['industry'],)
        )

        recommendations = []
        for t in templates[:limit]:
            plan_data = json.loads(t['plan_data']) if t['plan_data'] else []
            expected_growth = sum(a.get('base_growth_raw', 0) for a in plan_data)

            recommendations.append({
                'id': t['id'],
                'name': t['name'],
                'description': t['description'],
                'expected_growth': round(expected_growth, 1),
                'target_score': min(100, current_score + expected_growth),
                'steps_count': len(plan_data),
                'usage_count': t['usage_count']
            })

        return recommendations