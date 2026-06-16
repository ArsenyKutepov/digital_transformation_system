from database.connection import DatabaseConnection


class SuccessFactorsAnalyzer:
    """Анализ факторов успеха цифровой трансформации"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_most_effective_actions(self, industry_code: str = None, limit: int = 10) -> list:
        """Получение наиболее эффективных действий"""
        query = """
            SELECT a.id, a.name, a.base_growth, a.cost, a.risk,
                   COUNT(ca.id) as times_used,
                   AVG(ca.actual_growth) as avg_actual_growth
            FROM actions a
            LEFT JOIN completed_actions ca ON a.id = ca.action_id
        """

        if industry_code:
            query += " LEFT JOIN organizations o ON ca.org_id = o.id"

        query += " GROUP BY a.id"

        if industry_code:
            query += " HAVING o.industry = '" + industry_code + "'"

        query += " ORDER BY avg_actual_growth DESC LIMIT " + str(limit)

        results = self.db.query(query)

        for r in results:
            if r['base_growth'] > 0:
                efficiency = (r.get('avg_actual_growth', 0) / r['base_growth']) * 100
                r['efficiency'] = round(efficiency, 1)
            else:
                r['efficiency'] = 0

        return results

    def get_successful_patterns(self, min_growth_threshold: float = 10.0) -> list:
        """Выявление успешных паттернов трансформации"""
        query = """
            SELECT o.id, o.name, o.industry,
                   MIN(a.final_score) as initial_score,
                   MAX(a.final_score) as final_score,
                   (MAX(a.final_score) - MIN(a.final_score)) as total_growth,
                   COUNT(DISTINCT a.id) as assessments_count
            FROM organizations o
            JOIN assessments a ON o.id = a.org_id
            GROUP BY o.id
            HAVING total_growth > ?
            ORDER BY total_growth DESC
        """

        successful_orgs = self.db.query(query, (min_growth_threshold,))

        patterns = []
        for org in successful_orgs[:5]:
            query_actions = """
                SELECT ca.action_id, a.name, ca.actual_growth, ca.completed_date, s.number as sprint_number
                FROM completed_actions ca
                JOIN actions a ON ca.action_id = a.id
                LEFT JOIN sprints s ON ca.sprint_id = s.id
                WHERE ca.org_id = ?
                ORDER BY ca.completed_date
            """
            completed = self.db.query(query_actions, (org['id'],))

            patterns.append({
                'org_name': org['name'],
                'industry': org['industry'],
                'initial_score': org['initial_score'],
                'final_score': org['final_score'],
                'total_growth': org['total_growth'],
                'actions_sequence': [
                    {
                        'name': c['name'],
                        'growth': c['actual_growth'],
                        'sprint': c.get('sprint_number', 'N/A')
                    }
                    for c in completed
                ]
            })

        return patterns

    def get_correlation_analysis(self) -> dict:
        """Корреляционный анализ между действиями и ростом ЦЗ"""
        query = """
            SELECT ca.action_id, a.name, a.base_growth, ca.actual_growth,
                   o.industry, a.cost, a.risk
            FROM completed_actions ca
            JOIN actions a ON ca.action_id = a.id
            JOIN organizations o ON ca.org_id = o.id
            WHERE ca.actual_growth IS NOT NULL
        """

        completed = self.db.query(query)

        if not completed:
            return {}

        action_stats = {}
        for c in completed:
            action_id = c['action_id']
            if action_id not in action_stats:
                action_stats[action_id] = {
                    'name': c['name'],
                    'base_growth': c['base_growth'],
                    'actual_growths': [],
                    'costs': [],
                    'risks': [],
                    'industries': {}
                }
            action_stats[action_id]['actual_growths'].append(c['actual_growth'])
            action_stats[action_id]['costs'].append(c['cost'])
            action_stats[action_id]['risks'].append(c['risk'])

            ind = c['industry']
            if ind not in action_stats[action_id]['industries']:
                action_stats[action_id]['industries'][ind] = []
            action_stats[action_id]['industries'][ind].append(c['actual_growth'])

        results = []
        for action_id, stats in action_stats.items():
            if stats['actual_growths']:
                avg_growth = sum(stats['actual_growths']) / len(stats['actual_growths'])
                efficiency = (avg_growth / stats['base_growth']) * 100 if stats['base_growth'] > 0 else 0

                industry_efficiency = {}
                for ind, growths in stats['industries'].items():
                    if growths:
                        industry_efficiency[ind] = round(sum(growths) / len(growths), 1)

                results.append({
                    'action_id': action_id,
                    'action_name': stats['name'],
                    'base_growth': stats['base_growth'],
                    'avg_actual_growth': round(avg_growth, 1),
                    'efficiency': round(efficiency, 1),
                    'times_used': len(stats['actual_growths']),
                    'avg_cost': round(sum(stats['costs']) / len(stats['costs']), 2),
                    'avg_risk': round(sum(stats['risks']) / len(stats['risks']), 2),
                    'industry_efficiency': industry_efficiency
                })

        results.sort(key=lambda x: x['efficiency'], reverse=True)

        return {
            'most_effective': results[:5],
            'least_effective': results[-5:] if len(results) >= 5 else results,
            'total_actions_analyzed': len(results)
        }