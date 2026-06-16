from database.connection import DatabaseConnection


class ROIAnalyzer:
    """Анализ возврата инвестиций (ROI) от цифровой трансформации"""

    def __init__(self):
        self.db = DatabaseConnection()

    def calculate_sprint_roi(self, sprint_id: int) -> dict:
        """Расчёт ROI для конкретного спринта"""
        sprint = self.db.query_one("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        if not sprint:
            return {}

        planned_cost = sprint.get('planned_cost', 0)
        actual_cost = sprint.get('actual_cost', 0)
        planned_growth = sprint.get('planned_growth', 0)
        actual_growth = sprint.get('actual_growth', 0)

        # ROI = (фактический рост / фактические затраты) * 100
        if actual_cost and actual_cost > 0:
            roi = (actual_growth / actual_cost) * 100
        elif planned_cost > 0:
            roi = (planned_growth / planned_cost) * 100
        else:
            roi = 0

        # Эффективность затрат
        if planned_cost > 0:
            cost_efficiency = (actual_growth / planned_cost) * 100 if actual_growth else 0
        else:
            cost_efficiency = 0

        return {
            'sprint_id': sprint_id,
            'sprint_number': sprint['number'],
            'planned_cost': planned_cost,
            'actual_cost': actual_cost,
            'cost_variance': actual_cost - planned_cost if actual_cost else 0,
            'planned_growth': planned_growth,
            'actual_growth': actual_growth,
            'growth_variance': actual_growth - planned_growth if actual_growth else 0,
            'roi': round(roi, 1),
            'cost_efficiency': round(cost_efficiency, 1),
            'status': sprint['status']
        }

    def calculate_plan_roi(self, plan_id: int) -> dict:
        """Расчёт ROI для всего плана"""
        sprints = self.db.query("SELECT * FROM sprints WHERE plan_id = ?", (plan_id,))

        total_planned_cost = 0
        total_actual_cost = 0
        total_planned_growth = 0
        total_actual_growth = 0
        completed_sprints = 0

        for sprint in sprints:
            total_planned_cost += sprint.get('planned_cost', 0)
            total_planned_growth += sprint.get('planned_growth', 0)

            if sprint.get('actual_cost'):
                total_actual_cost += sprint['actual_cost']
            if sprint.get('actual_growth'):
                total_actual_growth += sprint['actual_growth']
                completed_sprints += 1

        if total_actual_cost > 0:
            roi = (total_actual_growth / total_actual_cost) * 100
        elif total_planned_cost > 0:
            roi = (total_planned_growth / total_planned_cost) * 100
        else:
            roi = 0

        return {
            'plan_id': plan_id,
            'total_sprints': len(sprints),
            'completed_sprints': completed_sprints,
            'total_planned_cost': total_planned_cost,
            'total_actual_cost': total_actual_cost,
            'total_planned_growth': total_planned_growth,
            'total_actual_growth': total_actual_growth,
            'roi': round(roi, 1),
            'completion_rate': round((completed_sprints / len(sprints)) * 100, 1) if sprints else 0
        }

    def get_organization_roi_summary(self, org_id: int) -> dict:
        """Сводка ROI по организации"""
        plans = self.db.query(
            "SELECT id FROM transformation_plans WHERE org_id = ?",
            (org_id,)
        )

        plan_rois = []
        total_roi = 0

        for plan in plans:
            roi_data = self.calculate_plan_roi(plan['id'])
            plan_rois.append(roi_data)
            total_roi += roi_data['roi']

        avg_roi = total_roi / len(plan_rois) if plan_rois else 0

        # Получаем последнюю оценку для анализа прогресса
        latest_assessment = self.db.query_one(
            "SELECT final_score FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )

        first_assessment = self.db.query_one(
            "SELECT final_score FROM assessments WHERE org_id = ? ORDER BY assessment_date ASC LIMIT 1",
            (org_id,)
        )

        total_growth = 0
        if latest_assessment and first_assessment:
            total_growth = latest_assessment['final_score'] - first_assessment['final_score']

        return {
            'org_id': org_id,
            'total_plans': len(plans),
            'average_roi': round(avg_roi, 1),
            'plan_rois': plan_rois,
            'total_growth': round(total_growth, 1),
            'initial_score': first_assessment['final_score'] if first_assessment else 0,
            'current_score': latest_assessment['final_score'] if latest_assessment else 0
        }

    def update_sprint_costs(self, sprint_id: int, actual_cost: float):
        """Обновление фактических затрат спринта"""
        self.db.execute(
            "UPDATE sprints SET actual_cost = ? WHERE id = ?",
            (actual_cost, sprint_id)
        )

        # Обновляем ROI аналитику
        roi_data = self.calculate_sprint_roi(sprint_id)

        sprint = self.db.query_one(
            "SELECT plan_id, org_id FROM sprints s JOIN transformation_plans p ON s.plan_id = p.id WHERE s.id = ?",
            (sprint_id,))

        if sprint:
            self.db.execute(
                """INSERT INTO roi_analytics 
                   (org_id, sprint_id, planned_cost, actual_cost, planned_growth, actual_growth, roi) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sprint['org_id'], sprint_id, roi_data['planned_cost'], roi_data['actual_cost'],
                 roi_data['planned_growth'], roi_data['actual_growth'], roi_data['roi'])
            )