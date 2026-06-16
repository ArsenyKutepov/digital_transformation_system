from datetime import datetime, timedelta
from database.connection import DatabaseConnection


class SystemMetrics:
    """Сбор и отображение системных метрик для администратора"""

    def __init__(self):
        self.db = DatabaseConnection()

    def get_dashboard_metrics(self) -> dict:
        """Получение всех метрик для дашборда администратора"""
        return {
            'users': self._get_user_metrics(),
            'organizations': self._get_organization_metrics(),
            'assessments': self._get_assessment_metrics(),
            'plans': self._get_plan_metrics(),
            'sprints': self._get_sprint_metrics(),
            'performance': self._get_performance_metrics(),
            'growth': self._get_growth_metrics()
        }

    def _get_user_metrics(self) -> dict:
        """Метрики по пользователям"""
        total_users = self.db.query_one("SELECT COUNT(*) as cnt FROM users")
        active_users_7d = self.db.query_one("""
            SELECT COUNT(DISTINCT user_id) as cnt 
            FROM audit_log 
            WHERE timestamp > datetime('now', '-7 days')
        """)

        return {
            'total': total_users['cnt'] if total_users else 0,
            'active_7d': active_users_7d['cnt'] if active_users_7d else 0,
            'by_role': self.db.query("""
                SELECT role, COUNT(*) as cnt 
                FROM users 
                GROUP BY role
            """)
        }

    def _get_organization_metrics(self) -> dict:
        """Метрики по организациям"""
        total_orgs = self.db.query_one("SELECT COUNT(*) as cnt FROM organizations")

        return {
            'total': total_orgs['cnt'] if total_orgs else 0,
            'by_industry': self.db.query("""
                SELECT industry, COUNT(*) as cnt 
                FROM organizations 
                GROUP BY industry
            """),
            'by_type': self.db.query("""
                SELECT organization_type, COUNT(*) as cnt 
                FROM organizations 
                GROUP BY organization_type
            """)
        }

    def _get_assessment_metrics(self) -> dict:
        """Метрики по оценкам"""
        total_assessments = self.db.query_one("SELECT COUNT(*) as cnt FROM assessments")
        avg_score = self.db.query_one("SELECT AVG(final_score) as avg FROM assessments")

        # Оценки по дням за последние 30 дней
        daily_scores = self.db.query("""
            SELECT DATE(assessment_date) as date, 
                   COUNT(*) as count,
                   AVG(final_score) as avg_score
            FROM assessments 
            WHERE assessment_date > datetime('now', '-30 days')
            GROUP BY DATE(assessment_date)
            ORDER BY date
        """)

        return {
            'total': total_assessments['cnt'] if total_assessments else 0,
            'avg_score': round(avg_score['avg'], 1) if avg_score and avg_score['avg'] else 0,
            'daily_stats': daily_scores
        }

    def _get_plan_metrics(self) -> dict:
        """Метрики по планам трансформации"""
        total_plans = self.db.query_one("SELECT COUNT(*) as cnt FROM transformation_plans")
        active_plans = self.db.query_one("SELECT COUNT(*) as cnt FROM transformation_plans WHERE status = 'active'")
        success_rate = self.db.query_one("""
            SELECT AVG(CASE WHEN success = 1 THEN 100 ELSE 0 END) as rate 
            FROM transformation_plans 
            WHERE success IS NOT NULL
        """)

        return {
            'total': total_plans['cnt'] if total_plans else 0,
            'active': active_plans['cnt'] if active_plans else 0,
            'success_rate': round(success_rate['rate'], 1) if success_rate and success_rate['rate'] else 0
        }

    def _get_sprint_metrics(self) -> dict:
        """Метрики по спринтам"""
        total_sprints = self.db.query_one("SELECT COUNT(*) as cnt FROM sprints")
        completed_sprints = self.db.query_one("SELECT COUNT(*) as cnt FROM sprints WHERE status = 'completed'")

        # Средняя точность прогноза
        accuracy = self.db.query_one("""
            SELECT AVG(actual_growth / planned_growth * 100) as accuracy 
            FROM sprints 
            WHERE status = 'completed' AND planned_growth > 0 AND actual_growth IS NOT NULL
        """)

        return {
            'total': total_sprints['cnt'] if total_sprints else 0,
            'completed': completed_sprints['cnt'] if completed_sprints else 0,
            'completion_rate': round((completed_sprints['cnt'] / total_sprints['cnt']) * 100, 1) if total_sprints[
                'cnt'] else 0,
            'forecast_accuracy': round(accuracy['accuracy'], 1) if accuracy and accuracy['accuracy'] else 0
        }

    def _get_performance_metrics(self) -> dict:
        """Метрики производительности системы"""
        # API latency (примерно, можно заменить на реальные замеры)
        avg_response_time = 0.250  # секунд

        return {
            'avg_response_time': avg_response_time,
            'db_size': self._get_db_size(),
            'active_sessions':
                self.db.query_one("SELECT COUNT(*) as cnt FROM user_sessions WHERE expires_at > datetime('now')")['cnt']
        }

    def _get_growth_metrics(self) -> dict:
        """Метрики роста за период"""
        # Рост числа пользователей за месяц
        users_growth = self.db.query_one("""
            SELECT 
                COUNT(CASE WHEN created_at > datetime('now', '-30 days') THEN 1 END) as new,
                COUNT(CASE WHEN created_at <= datetime('now', '-30 days') THEN 1 END) as old
            FROM users
        """)

        # Рост числа оценок за месяц
        assessments_growth = self.db.query_one("""
            SELECT 
                COUNT(CASE WHEN assessment_date > datetime('now', '-30 days') THEN 1 END) as new,
                COUNT(CASE WHEN assessment_date <= datetime('now', '-30 days') THEN 1 END) as old
            FROM assessments
        """)

        return {
            'users': {
                'new': users_growth['new'] if users_growth else 0,
                'total_growth': round((users_growth['new'] / users_growth['old']) * 100, 1) if users_growth and
                                                                                               users_growth[
                                                                                                   'old'] > 0 else 0
            },
            'assessments': {
                'new': assessments_growth['new'] if assessments_growth else 0,
                'total_growth': round((assessments_growth['new'] / assessments_growth['old']) * 100,
                                      1) if assessments_growth and assessments_growth['old'] > 0 else 0
            }
        }

    def _get_db_size(self) -> str:
        """Получение размера базы данных"""
        import os
        from config import DATABASE_PATH

        if os.path.exists(DATABASE_PATH):
            size_bytes = os.path.getsize(DATABASE_PATH)
            if size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        return "0 KB"

    def record_metric(self, metric_name: str, metric_value: str):
        """Запись метрики в БД"""
        self.db.execute(
            "INSERT INTO system_metrics (metric_name, metric_value) VALUES (?, ?)",
            (metric_name, metric_value)
        )

    def get_admin_dashboard_html(self) -> str:
        """Генерация HTML дашборда администратора"""
        metrics = self.get_dashboard_metrics()

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Системная аналитика</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Segoe UI', sans-serif; background: #F8FAFC; padding: 20px; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                h1 {{ margin-bottom: 20px; color: #0F172A; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                .stat-number {{ font-size: 32px; font-weight: bold; color: #3B82F6; }}
                .stat-label {{ font-size: 14px; color: #64748B; margin-top: 8px; }}
                .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
                h2 {{ margin-bottom: 20px; font-size: 18px; border-left: 4px solid #3B82F6; padding-left: 12px; }}
                .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
                th {{ background: #F1F5F9; }}
                .chart-container {{ height: 300px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Системная аналитика</h1>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{metrics['users']['total']}</div>
                        <div class="stat-label">Пользователей</div>
                        <div style="font-size: 12px; color: #10B981;">+{metrics['growth']['users']['total_growth']}% за месяц</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{metrics['organizations']['total']}</div>
                        <div class="stat-label">Организаций</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{metrics['assessments']['total']}</div>
                        <div class="stat-label">Оценок ЦЗ</div>
                        <div style="font-size: 12px;">Средний балл: {metrics['assessments']['avg_score']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{metrics['plans']['success_rate']}%</div>
                        <div class="stat-label">Успешность планов</div>
                    </div>
                </div>

                <div class="grid-2">
                    <div class="card">
                        <h2>Пользователи по ролям</h2>
                        <table>
                            <thead><tr><th>Роль</th><th>Количество</th></tr></thead>
                            <tbody>
                                {''.join([f'<tr><td>{r["role"]}</td><td>{r["cnt"]}</td></tr>' for r in metrics['users']['by_role']])}
                            </tbody>
                        </table>
                    </div>

                    <div class="card">
                        <h2>Организации по отраслям</h2>
                        <table>
                            <thead><tr><th>Отрасль</th><th>Количество</th></tr></thead>
                            <tbody>
                                {''.join([f'<tr><td>{r["industry"]}</td><td>{r["cnt"]}</td></tr>' for r in metrics['organizations']['by_industry']])}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="card">
                    <h2>Динамика оценок (последние 30 дней)</h2>
                    <div class="chart-container">
                        <canvas id="assessmentsChart"></canvas>
                    </div>
                </div>

                <div class="grid-2">
                    <div class="card">
                        <h2>Статистика спринтов</h2>
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; font-weight: bold; color: #3B82F6;">{metrics['sprints']['completion_rate']}%</div>
                            <div>Выполнение спринтов</div>
                            <div style="margin-top: 10px;">Всего: {metrics['sprints']['total']} | Завершено: {metrics['sprints']['completed']}</div>
                            <div style="margin-top: 5px; font-size: 12px;">Точность прогноза: {metrics['sprints']['forecast_accuracy']}%</div>
                        </div>
                    </div>

                    <div class="card">
                        <h2>Производительность системы</h2>
                        <div style="padding: 20px;">
                            <div>⏱ Среднее время ответа: {metrics['performance']['avg_response_time']} с</div>
                            <div>💾 Размер БД: {metrics['performance']['db_size']}</div>
                            <div>🟢 Активных сессий: {metrics['performance']['active_sessions']}</div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                const dailyData = {str([{
            'dates': [d['date'] for d in metrics['assessments']['daily_stats']],
            'counts': [d['count'] for d in metrics['assessments']['daily_stats']],
            'scores': [d['avg_score'] for d in metrics['assessments']['daily_stats']]
        }])};

                new Chart(document.getElementById('assessmentsChart'), {{
                    type: 'line',
                    data: {{
                        labels: dailyData.dates,
                        datasets: [
                            {{ label: 'Количество оценок', data: dailyData.counts, borderColor: '#3B82F6', fill: false, yAxisID: 'y' }},
                            {{ label: 'Средний балл', data: dailyData.scores, borderColor: '#10B981', fill: false, yAxisID: 'y1' }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {{
                            y: {{ title: {{ display: true, text: 'Количество оценок' }} }},
                            y1: {{ position: 'right', title: {{ display: true, text: 'Средний балл' }}, min: 0, max: 100 }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        '''

        return html