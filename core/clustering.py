import json
import math
from database.connection import DatabaseConnection


class OrganizationClustering:
    """Кластеризация организаций по профилям цифровой зрелости"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_all_organization_profiles(self) -> list:
        """Получение профилей всех организаций для кластеризации"""
        # Получаем последнюю оценку для каждой организации
        orgs = self.db.query("SELECT id, name, industry FROM organizations")

        profiles = []
        for org in orgs:
            assessment = self.db.query_one(
                "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
                (org['id'],)
            )
            if assessment:
                # Получаем детали оценки по блокам
                details = self.db.query(
                    "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
                    (assessment['id'],)
                )

                # Группируем по блокам
                block_map = {
                    '1.1': 1, '1.2': 1, '1.3': 1,
                    '2.1': 2, '2.2': 2, '2.3': 2,
                    '3.1': 3, '3.2': 3, '3.3': 3,
                    '4.1': 4, '4.2': 4, '4.3': 4,
                    '5.1': 5, '5.2': 5, '5.3': 5,
                    '6.1': 6, '6.2': 6,
                    '7.1': 7, '7.2': 7, '7.3': 7,
                    '8.1': 8, '8.2': 8, '8.3': 8,
                    '9.1': 9, '9.2': 9
                }

                block_scores = {i: [] for i in range(1, 10)}
                for d in details:
                    block_id = block_map.get(d['indicator_code'], 1)
                    block_scores[block_id].append(d['value'])

                # Усредняем по блокам
                block_averages = {}
                for block_id in range(1, 10):
                    if block_scores[block_id]:
                        block_averages[block_id] = sum(block_scores[block_id]) / len(block_scores[block_id])
                    else:
                        block_averages[block_id] = 0

                profiles.append({
                    'org_id': org['id'],
                    'org_name': org['name'],
                    'industry': org.get('industry', 'education'),
                    'final_score': assessment['final_score'],
                    'technical': assessment['technical_factor'],
                    'cognitive': assessment['cognitive_factor'],
                    'personal': assessment['personal_factor'],
                    'blocks': block_averages
                })

        return profiles

    def euclidean_distance(self, profile1: dict, profile2: dict) -> float:
        """Расчёт евклидова расстояния между профилями"""
        # Основные метрики
        distance = 0.0
        distance += (profile1['final_score'] - profile2['final_score']) ** 2
        distance += (profile1['technical'] - profile2['technical']) ** 2
        distance += (profile1['cognitive'] - profile2['cognitive']) ** 2
        distance += (profile1['personal'] - profile2['personal']) ** 2

        # Блоки
        for block_id in range(1, 10):
            b1 = profile1['blocks'].get(block_id, 0)
            b2 = profile2['blocks'].get(block_id, 0)
            distance += (b1 - b2) ** 2

        return math.sqrt(distance)

    def find_similar_organizations(self, org_id: int, limit: int = 5) -> list:
        """Поиск организаций, похожих на заданную"""
        profiles = self.get_all_organization_profiles()

        target = None
        for p in profiles:
            if p['org_id'] == org_id:
                target = p
                break

        if not target:
            return []

        # Вычисляем расстояния до всех организаций
        distances = []
        for p in profiles:
            if p['org_id'] != org_id:
                dist = self.euclidean_distance(target, p)
                distances.append({
                    'org_id': p['org_id'],
                    'org_name': p['org_name'],
                    'industry': p['industry'],
                    'final_score': p['final_score'],
                    'distance': round(dist, 2)
                })

        # Сортируем по расстоянию
        distances.sort(key=lambda x: x['distance'])

        return distances[:limit]

    def get_cluster_leader(self, industry_code: str) -> dict:
        """Получение организации-лидера в отрасли"""
        profiles = [p for p in self.get_all_organization_profiles() if p['industry'] == industry_code]

        if not profiles:
            return None

        # Сортируем по итоговому баллу
        profiles.sort(key=lambda x: x['final_score'], reverse=True)

        leader = profiles[0]

        # Получаем бенчмарк лидера
        benchmark = self.db.query_one(
            "SELECT leader_value FROM benchmarks WHERE industry_code = ? AND metric_name = 'final_score'",
            (industry_code,)
        )

        return {
            'org_id': leader['org_id'],
            'org_name': leader['org_name'],
            'final_score': leader['final_score'],
            'technical': leader['technical'],
            'cognitive': leader['cognitive'],
            'personal': leader['personal'],
            'leader_benchmark': benchmark['leader_value'] if benchmark else None
        }

    def get_cluster_recommendations(self, org_id: int) -> list:
        """Получение рекомендаций на основе анализа похожих организаций"""
        similar = self.find_similar_organizations(org_id, 3)

        recommendations = []

        for sim in similar:
            # Получаем действия, которые выполнила похожая организация
            completed = self.db.query(
                "SELECT action_id FROM completed_actions WHERE org_id = ?",
                (sim['org_id'],)
            )

            for c in completed:
                action = self.db.query_one(
                    "SELECT name, base_growth FROM actions WHERE id = ?",
                    (c['action_id'],)
                )
                if action:
                    recommendations.append({
                        'action_name': action['name'],
                        'base_growth': action['base_growth'],
                        'source_org': sim['org_name'],
                        'source_score': sim['final_score']
                    })

        # Убираем дубликаты
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec['action_name'] not in seen:
                seen.add(rec['action_name'])
                unique_recs.append(rec)

        return unique_recs[:5]