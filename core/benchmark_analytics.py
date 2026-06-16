from database.connection import DatabaseConnection


class BenchmarkAnalytics:
    """Аналитика с сравнением с отраслевыми бенчмарками"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_benchmark_comparison(self, org_id: int) -> dict:
        """Сравнение организации с отраслевыми бенчмарками"""
        org = self.db.query_one("SELECT industry FROM organizations WHERE id = ?", (org_id,))
        if not org:
            return {}

        industry = org.get('industry', 'education')

        # Получаем последнюю оценку организации
        assessment = self.db.query_one(
            "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )

        if not assessment:
            return {}

        # Получаем бенчмарки
        benchmarks = self.db.query(
            "SELECT * FROM benchmarks WHERE industry_code = ?",
            (industry,)
        )

        benchmark_dict = {}
        for b in benchmarks:
            benchmark_dict[b['metric_name']] = {
                'p25': b['percentile_25'],
                'p50': b['percentile_50'],
                'p75': b['percentile_75'],
                'leader': b['leader_value']
            }

        # Сравнение по основным метрикам
        comparison = {
            'industry': industry,
            'final_score': {
                'current': assessment['final_score'],
                'p25': benchmark_dict.get('final_score', {}).get('p25', 0),
                'p50': benchmark_dict.get('final_score', {}).get('p50', 0),
                'p75': benchmark_dict.get('final_score', {}).get('p75', 0),
                'leader': benchmark_dict.get('final_score', {}).get('leader', 0),
                'percentile': self._get_percentile(
                    assessment['final_score'],
                    benchmark_dict.get('final_score', {})
                )
            },
            'technical_factor': {
                'current': assessment['technical_factor'],
                'p50': benchmark_dict.get('technical_factor', {}).get('p50', 0),
                'leader': benchmark_dict.get('technical_factor', {}).get('leader', 0)
            },
            'cognitive_factor': {
                'current': assessment['cognitive_factor'],
                'p50': benchmark_dict.get('cognitive_factor', {}).get('p50', 0),
                'leader': benchmark_dict.get('cognitive_factor', {}).get('leader', 0)
            },
            'personal_factor': {
                'current': assessment['personal_factor'],
                'p50': benchmark_dict.get('personal_factor', {}).get('p50', 0),
                'leader': benchmark_dict.get('personal_factor', {}).get('leader', 0)
            }
        }

        # Определяем позицию организации
        current = assessment['final_score']
        p25 = benchmark_dict.get('final_score', {}).get('p25', 0)
        p50 = benchmark_dict.get('final_score', {}).get('p50', 0)
        p75 = benchmark_dict.get('final_score', {}).get('p75', 0)
        leader = benchmark_dict.get('final_score', {}).get('leader', 0)

        if current >= leader:
            position = 'leader'
            position_text = 'Лидер отрасли'
        elif current >= p75:
            position = 'above_average'
            position_text = 'Выше среднего'
        elif current >= p50:
            position = 'average'
            position_text = 'Средний уровень'
        elif current >= p25:
            position = 'below_average'
            position_text = 'Ниже среднего'
        else:
            position = 'lagging'
            position_text = 'Отстающий'

        comparison['position'] = position
        comparison['position_text'] = position_text

        # Гэп до лидера
        gap_to_leader = leader - current
        comparison['gap_to_leader'] = max(0, gap_to_leader)

        return comparison

    def _get_percentile(self, value: float, benchmark: dict) -> str:
        """Определение перцентиля"""
        p25 = benchmark.get('p25', 0)
        p50 = benchmark.get('p50', 0)
        p75 = benchmark.get('p75', 0)

        if value >= p75:
            return '75+'
        elif value >= p50:
            return '50-75'
        elif value >= p25:
            return '25-50'
        else:
            return '<25'

    def get_industry_leader_actions(self, industry_code: str, limit: int = 5) -> list:
        """Получение действий, которые выполнил лидер отрасли"""
        # Находим лидера отрасли
        leader = self.db.query_one(
            """SELECT o.id, o.name, MAX(a.final_score) as max_score
               FROM organizations o
               JOIN assessments a ON o.id = a.org_id
               WHERE o.industry = ?
               GROUP BY o.id
               ORDER BY max_score DESC LIMIT 1""",
            (industry_code,)
        )

        if not leader:
            return []

        # Получаем действия лидера
        completed = self.db.query(
            """SELECT ca.action_id, a.name, a.base_growth, ca.actual_growth, ca.completed_date
               FROM completed_actions ca
               JOIN actions a ON ca.action_id = a.id
               WHERE ca.org_id = ?
               ORDER BY ca.completed_date""",
            (leader['id'],)
        )

        return [
            {
                'action_name': c['name'],
                'base_growth': c['base_growth'],
                'actual_growth': c.get('actual_growth'),
                'date': c.get('completed_date', '')[:10] if c.get('completed_date') else ''
            }
            for c in completed[:limit]
        ]

    def get_benchmark_table(self) -> str:
        """Генерация HTML-таблицы бенчмарков по отраслям"""
        industries = self.db.query("SELECT code, name FROM industries")

        if not industries:
            return '<p style="color: #64748B;">Нет данных об отраслях</p>'

        html = '<table class="benchmark-table"><thead><tr><th>Отрасль</th><th>Средний уровень ЦЗ</th><th>25-й %</th><th>75-й %</th><th>Лидер отрасли</th></tr></thead><tbody>'

        for ind in industries:
            benchmark = self.db.query_one(
                "SELECT percentile_25, percentile_50, percentile_75, leader_value FROM benchmarks WHERE industry_code = ? AND metric_name = 'final_score'",
                (ind['code'],)
            )

            if benchmark:
                html += f'<tr><td>{ind["name"]}</td><td>{benchmark["percentile_50"]:.0f}</td><td>{benchmark["percentile_25"]:.0f}</td><td>{benchmark["percentile_75"]:.0f}</td><td>{benchmark["leader_value"]:.0f}</td></tr>'
            else:
                html += f'<tr><td>{ind["name"]}</td><td colspan="4">Нет данных</td></tr>'

        html += '</tbody></table>'
        return html