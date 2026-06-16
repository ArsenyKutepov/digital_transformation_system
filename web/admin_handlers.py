from database.connection import DatabaseConnection
from database.user_model import UserManager
from core.system_metrics import SystemMetrics
from core.benchmark_analytics import BenchmarkAnalytics
from .handlers import BaseHandler


class AdminDashboardHandler(BaseHandler):
    """Панель администратора - прямая генерация HTML"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role != 'admin':
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        metrics = SystemMetrics()
        dashboard_metrics = metrics.get_dashboard_metrics()

        # Получаем бенчмарки в виде HTML
        benchmark = BenchmarkAnalytics()
        benchmark_table = benchmark.get_benchmark_table()

        # Генерируем HTML напрямую
        html = self._build_admin_html(dashboard_metrics, benchmark_table)

        return html, 'text/html; charset=utf-8'

    def _build_admin_html(self, metrics, benchmark_table):
        """Построение HTML страницы администратора"""

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Панель администратора</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }}
        .container {{ max-width: 1200px; margin: -20px auto 0; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: white; border-radius: 16px; padding: 20px; text-align: center; border: 1px solid #E2E8F0; }}
        .stat-number {{ font-size: 32px; font-weight: bold; color: #3B82F6; }}
        .stat-label {{ font-size: 14px; color: #64748B; margin-top: 8px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin: 5px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .admin-links {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px; }}
        .admin-link {{ background: #F1F5F9; padding: 12px 20px; border-radius: 12px; text-decoration: none; color: #0F172A; font-weight: 500; display: inline-flex; align-items: center; gap: 10px; }}
        .admin-link:hover {{ background: #E2E8F0; }}
        .benchmark-table {{ width: 100%; border-collapse: collapse; }}
        .benchmark-table th, .benchmark-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
        .benchmark-table th {{ background: #F1F5F9; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚙️ Панель администратора</h1>
        <p>Управление системой, действиями и планировщиком</p>
    </div>
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{metrics['users']['total']}</div><div class="stat-label">Пользователей</div></div>
            <div class="stat-card"><div class="stat-number">{metrics['organizations']['total']}</div><div class="stat-label">Организаций</div></div>
            <div class="stat-card"><div class="stat-number">{metrics['assessments']['total']}</div><div class="stat-label">Оценок ЦЗ</div></div>
            <div class="stat-card"><div class="stat-number">{metrics['plans']['success_rate']}%</div><div class="stat-label">Успешность планов</div></div>
        </div>

        <div class="admin-links">
            <a href="/admin/actions" class="admin-link">📋 Управление действиями</a>
            <a href="/admin/scheduler" class="admin-link">⏰ Планировщик задач</a>
            <a href="/admin/users" class="admin-link">👥 Управление пользователями</a>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>📊 Отраслевые бенчмарки</h2>
                {benchmark_table}
            </div>
            <div class="card">
                <h2>📈 Системные метрики</h2>
                <p><strong>Средний ответ API:</strong> {metrics['performance']['avg_response_time']} с</p>
                <p><strong>Размер БД:</strong> {metrics['performance']['db_size']}</p>
                <p><strong>Активных сессий:</strong> {metrics['performance']['active_sessions']}</p>
                <p><strong>Завершено спринтов:</strong> {metrics['sprints']['completed']}</p>
                <p><strong>Точность прогноза:</strong> {metrics['sprints']['forecast_accuracy']}%</p>
            </div>
        </div>

        <div style="text-align: center; margin-top: 20px;">
            <a href="/" class="btn">← На главную</a>
        </div>
    </div>
</body>
</html>'''

        return html


class AdminActionsHandler(BaseHandler):
    """Управление действиями (CRUD)"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role != 'admin':
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()

        if request['method'] == 'GET':
            actions = db.query("SELECT * FROM actions ORDER BY id")

            # Генерируем HTML напрямую
            html = self._build_actions_html(actions)
            return html, 'text/html; charset=utf-8'

        elif request['method'] == 'POST':
            post_data = request['post_data']
            action_type = post_data.get('action')

            if action_type == 'create':
                name = post_data.get('name')
                base_growth = float(post_data.get('base_growth', 0.1))
                cost = float(post_data.get('cost', 0.1))
                risk = float(post_data.get('risk', 0.1))
                inertia_shock = float(post_data.get('inertia_shock', 0.15))
                cognitive_load = float(post_data.get('cognitive_load', 0.15))

                db.execute(
                    "INSERT INTO actions (name, base_growth, cost, risk, inertia_shock, cognitive_load) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, base_growth, cost, risk, inertia_shock, cognitive_load)
                )

            elif action_type == 'update':
                action_id = int(post_data.get('action_id'))
                db.execute(
                    "UPDATE actions SET name = ?, base_growth = ?, cost = ?, risk = ?, inertia_shock = ?, cognitive_load = ? WHERE id = ?",
                    (post_data.get('name'), float(post_data.get('base_growth', 0.1)), float(post_data.get('cost', 0.1)),
                     float(post_data.get('risk', 0.1)), float(post_data.get('inertia_shock', 0.15)),
                     float(post_data.get('cognitive_load', 0.15)), action_id)
                )

            elif action_type == 'delete':
                action_id = int(post_data.get('action_id'))
                db.execute("DELETE FROM actions WHERE id = ?", (action_id,))

            return self.render(template_engine, 'redirect.html', {'url': '/admin/actions'})

    def _build_actions_html(self, actions):
        actions_table = ''
        for a in actions:
            actions_table += f'''
            <tr>
                <td>{a['id']}</td>
                <td>{a['name']}</td>
                <td>{a['base_growth'] * 100:.0f}%</td>
                <td>{a['cost'] * 100:.0f}%</td>
                <td>{a['risk'] * 100:.0f}%</td>
                <td>
                    <form method="POST" style="display: inline;">
                        <input type="hidden" name="action" value="delete">
                        <input type="hidden" name="action_id" value="{a['id']}">
                        <button type="submit" style="background: #EF4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">🗑️</button>
                    </form>
                </td>
            </tr>
            '''

        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Управление действиями</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 20px; padding: 24px; margin-bottom: 20px; }}
        h1 {{ margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
        th {{ background: #F1F5F9; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin: 5px; }}
        .btn-create {{ background: #10B981; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Управление действиями</h1>
            <button onclick="showCreateForm()" class="btn btn-create">+ Создать действие</button>

            <div id="createForm" style="display: none; margin-top: 20px; padding: 20px; background: #F8FAFC; border-radius: 12px;">
                <h3>Новое действие</h3>
                <form method="POST">
                    <input type="hidden" name="action" value="create">
                    <div style="margin-bottom: 10px;"><input type="text" name="name" placeholder="Название" required style="width: 100%; padding: 8px;"></div>
                    <div style="margin-bottom: 10px;"><input type="number" step="0.01" name="base_growth" placeholder="Базовый рост" value="0.1" style="width: 100%; padding: 8px;"></div>
                    <div style="margin-bottom: 10px;"><input type="number" step="0.01" name="cost" placeholder="Затраты" value="0.1" style="width: 100%; padding: 8px;"></div>
                    <div style="margin-bottom: 10px;"><input type="number" step="0.01" name="risk" placeholder="Риск" value="0.1" style="width: 100%; padding: 8px;"></div>
                    <button type="submit" class="btn">Сохранить</button>
                    <button type="button" onclick="hideCreateForm()" class="btn">Отмена</button>
                </form>
            </div>

            <table>
                <thead><tr><th>ID</th><th>Название</th><th>Рост</th><th>Затраты</th><th>Риск</th><th></th></tr></thead>
                <tbody>
                    {actions_table}
                </tbody>
            </table>
            <a href="/admin" class="btn">← Назад</a>
        </div>
    </div>
    <script>
        function showCreateForm() {{ document.getElementById('createForm').style.display = 'block'; }}
        function hideCreateForm() {{ document.getElementById('createForm').style.display = 'none'; }}
    </script>
</body>
</html>'''


class SchedulerAdminHandler(BaseHandler):
    """Администрирование планировщика задач"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role != 'admin':
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        tasks = [
            {'name': 'check_overdue_sprints', 'label': 'Проверка просроченных спринтов',
             'schedule': 'Ежедневно в 09:00'},
            {'name': 'send_sprint_reminders', 'label': 'Напоминания о спринтах', 'schedule': 'Ежедневно в 10:00'},
            {'name': 'run_predictions', 'label': 'Прогнозирование ЦЗ', 'schedule': 'Понедельник в 08:00'},
            {'name': 'generate_weekly_reports', 'label': 'Генерация отчётов', 'schedule': 'Пятница в 17:00'},
            {'name': 'update_benchmarks', 'label': 'Обновление бенчмарков', 'schedule': 'Ежедневно в 02:00'},
            {'name': 'cleanup_old_sessions', 'label': 'Очистка сессий', 'schedule': 'Ежедневно в 03:00'},
            {'name': 'backup_database', 'label': 'Резервное копирование', 'schedule': 'Воскресенье в 01:00'}
        ]

        tasks_html = ''
        for t in tasks:
            tasks_html += f'''
            <tr>
                <td><strong>{t['label']}</strong></td>
                <td>{t['schedule']}</td>
                <td>
                    <form method="POST" style="display: inline;">
                        <input type="hidden" name="task" value="{t['name']}">
                        <button type="submit" style="background: #3B82F6; color: white; border: none; padding: 6px 16px; border-radius: 8px; cursor: pointer;">▶ Запустить</button>
                    </form>
                </td>
            </tr>
            '''

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Планировщик задач</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 20px; padding: 24px; }}
        h1 {{ margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
        th {{ background: #F1F5F9; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>⏰ Планировщик задач</h1>
            <p>Статус: <span style="background: #D1FAE5; padding: 4px 12px; border-radius: 20px;">Активен</span></p>

            <table>
                <thead><tr><th>Задача</th><th>Расписание</th><th>Действие</th></tr></thead>
                <tbody>{tasks_html}</tbody>
            </table>

            <a href="/admin" class="btn">← Назад</a>
        </div>
    </div>
</body>
</html>'''

        if request['method'] == 'GET':
            return html, 'text/html; charset=utf-8'

        elif request['method'] == 'POST':
            from scheduler.task_scheduler import TaskScheduler
            post_data = request['post_data']
            task_name = post_data.get('task')

            scheduler = TaskScheduler()
            tasks_map = {
                'check_overdue_sprints': scheduler.check_overdue_sprints,
                'send_sprint_reminders': scheduler.send_sprint_reminders,
                'run_predictions': scheduler.run_predictions,
                'generate_weekly_reports': scheduler.generate_weekly_reports,
                'update_benchmarks': scheduler.update_benchmarks,
                'cleanup_old_sessions': scheduler.cleanup_old_sessions,
                'backup_database': scheduler.backup_database
            }

            if task_name in tasks_map:
                tasks_map[task_name]()

            return self.render(template_engine, 'redirect.html', {'url': '/admin/scheduler'})