import json
from datetime import datetime
from database.connection import DatabaseConnection
from core.sprint_manager import SprintManager
from .handlers import BaseHandler


class SprintListHandler(BaseHandler):
    """Просмотр списка спринтов с детальной информацией и приоритизацией"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        plan_id = params.get('plan_id') if params else None
        if not plan_id:
            return "<h1>ID плана не указан</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()
        plan = db.query_one("SELECT * FROM transformation_plans WHERE id = ?", (plan_id,))
        if not plan:
            return "<h1>План не найден</h1>", 'text/html; charset=utf-8'

        # Получаем данные плана
        plan_data = json.loads(plan['plan_data']) if plan['plan_data'] else []

        sprint_manager = SprintManager()
        sprints = sprint_manager.get_sprint_history(int(plan_id))
        active_sprint = sprint_manager.get_active_sprint(int(plan_id))

        # Получаем название организации
        org = db.query_one("SELECT name FROM organizations WHERE id = ?", (plan['org_id'],))
        org_name = org['name'] if org else 'Организация'

        # Получаем действия для каждого спринта
        for sprint in sprints:
            action_ids = json.loads(sprint['action_ids']) if sprint['action_ids'] else []
            sprint['actions'] = []
            for aid in action_ids:
                action = db.query_one("SELECT id, name, description, base_growth, cost, risk FROM actions WHERE id = ?",
                                      (aid,))
                if action:
                    sprint['actions'].append(action)

        # ПРИОРИТИЗАЦИЯ СПРИНТОВ: активный -> запланированные (по дате) -> завершённые (по дате)
        active_list = []
        planned_list = []
        completed_list = []

        for sprint in sprints:
            if sprint['status'] == 'active':
                active_list.append(sprint)
            elif sprint['status'] == 'planned':
                planned_list.append(sprint)
            elif sprint['status'] == 'completed':
                completed_list.append(sprint)

        # Сортируем запланированные по дате начала (ближайшие первые)
        planned_list.sort(key=lambda x: x['planned_start'])
        # Сортируем завершённые по дате завершения (сначала новые)
        completed_list.sort(key=lambda x: x.get('actual_end', x['planned_end']), reverse=True)

        # Объединяем в правильном порядке
        sorted_sprints = active_list + planned_list + completed_list

        # Статистика
        total_sprints = len(sprints)
        completed_sprints = len(completed_list)
        active_count = len(active_list)
        planned_count = len(planned_list)

        total_planned_growth = sum(s['planned_growth'] for s in sprints)
        total_actual_growth = sum(s.get('actual_growth', 0) for s in sprints if s.get('actual_growth'))

        completion_rate = (completed_sprints / total_sprints * 100) if total_sprints > 0 else 0
        growth_achievement = (total_actual_growth / total_planned_growth * 100) if total_planned_growth > 0 else 0

        # Генерируем HTML
        html = self._build_sprints_html(
            plan_id, org_name, sorted_sprints, active_sprint,
            total_sprints, completed_sprints, active_count, planned_count,
            total_planned_growth, total_actual_growth, completion_rate, growth_achievement
        )

        return html, 'text/html; charset=utf-8'

    def _build_sprints_html(self, plan_id, org_name, sprints, active_sprint,
                            total_sprints, completed_sprints, active_count, planned_count,
                            total_planned_growth, total_actual_growth, completion_rate, growth_achievement):
        """Построение HTML страницы со спринтами"""

        def get_status_badge(status):
            if status == 'planned':
                return '<span style="background: #E2E8F0; color: #475569; padding: 4px 12px; border-radius: 20px; font-size: 12px;">📋 Запланирован</span>'
            elif status == 'active':
                return '<span style="background: #DBEAFE; color: #1E40AF; padding: 4px 12px; border-radius: 20px; font-size: 12px;">▶ Активен</span>'
            elif status == 'completed':
                return '<span style="background: #D1FAE5; color: #065F46; padding: 4px 12px; border-radius: 20px; font-size: 12px;">✅ Завершён</span>'
            else:
                return '<span style="background: #FEE2E2; color: #991B1B; padding: 4px 12px; border-radius: 20px; font-size: 12px;">⚠ Просрочен</span>'

        # Строим HTML для каждого спринта
        sprints_html = ''
        for sprint in sprints:
            status_badge = get_status_badge(sprint['status'])

            # Кнопка действия
            if sprint['status'] == 'planned':
                action_button = f'''
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/sprints/{sprint['id']}/start" style="display: inline-flex; align-items: center; gap: 8px; background: #3B82F6; color: white; padding: 8px 16px; border-radius: 10px; text-decoration: none; font-size: 13px;">
                        <i class="fas fa-play"></i> Начать спринт
                    </a>
                </div>
                '''
            elif sprint['status'] == 'active':
                action_button = f'''
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/sprints/{sprint['id']}/complete" style="display: inline-flex; align-items: center; gap: 8px; background: #10B981; color: white; padding: 8px 16px; border-radius: 10px; text-decoration: none; font-size: 13px;">
                        <i class="fas fa-check"></i> Завершить спринт
                    </a>
                </div>
                '''
            elif sprint['status'] == 'completed':
                action_button = f'''
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/sprints/{sprint['id']}/view" style="display: inline-flex; align-items: center; gap: 8px; background: #64748B; color: white; padding: 8px 16px; border-radius: 10px; text-decoration: none; font-size: 13px;">
                        <i class="fas fa-eye"></i> Детали
                    </a>
                </div>
                '''
            else:
                action_button = ''

            # Прогресс-бар
            progress_percent = 0
            if sprint['status'] == 'completed' and sprint.get('actual_growth') and sprint['planned_growth'] > 0:
                progress_percent = min(100, int((sprint['actual_growth'] / sprint['planned_growth']) * 100))
            elif sprint['status'] == 'active':
                # Для активного спринта прогресс 0% (ещё не завершён)
                progress_percent = 0

            progress_bar = f'''
            <div style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748B; margin-bottom: 4px;">
                    <span>Прогресс выполнения</span>
                    <span>{progress_percent}%</span>
                </div>
                <div style="height: 6px; background: #E2E8F0; border-radius: 3px; overflow: hidden;">
                    <div style="height: 100%; width: {progress_percent}%; background: linear-gradient(90deg, #3B82F6, #8B5CF6); border-radius: 3px;"></div>
                </div>
            </div>
            '''

            # Информация о действиях в спринте
            actions_html = ''
            if sprint.get('actions') and len(sprint['actions']) > 0:
                actions_html = '<div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid #E2E8F0;"><strong style="font-size: 13px;">📋 Действия в спринте:</strong><ul style="margin-top: 8px; list-style: none; padding-left: 0;">'
                for action in sprint['actions']:
                    actions_html += f'<li style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 8px; font-size: 13px;">✅ {action["name"]}<span style="color: #64748B; font-size: 11px; margin-left: 8px;">(+{action["base_growth"] * 100:.0f}%)</span></li>'
                actions_html += '</ul></div>'

            # Фактический рост
            actual_growth_html = ''
            if sprint.get('actual_growth') is not None:
                growth_diff = sprint['actual_growth'] - sprint['planned_growth']
                diff_color = '#10B981' if growth_diff >= 0 else '#EF4444'
                diff_symbol = '+' if growth_diff >= 0 else ''
                actual_growth_html = f'''
                <div style="margin-top: 10px; padding: 8px; background: #F1F5F9; border-radius: 8px;">
                    <span style="font-size: 13px;">✅ Фактический рост: <strong>{sprint['actual_growth']:.1f}%</strong></span>
                    <span style="font-size: 12px; color: {diff_color}; margin-left: 10px;">({diff_symbol}{growth_diff:.1f}% от плана)</span>
                </div>
                '''

            # Отклонение от плана (если есть заметки)
            deviation_html = ''
            if sprint.get('notes'):
                deviation_html = f'''
                <div style="margin-top: 10px; padding: 8px; background: #FEF3C7; border-radius: 8px; font-size: 12px; color: #92400E;">
                    <i class="fas fa-comment"></i> {sprint['notes'][:100]}
                </div>
                '''

            sprints_html += f'''
            <div style="background: #F8FAFC; border-radius: 16px; padding: 20px; margin-bottom: 15px; border-left: 4px solid {'#3B82F6' if sprint['status'] == 'active' else '#64748B'};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap;">
                    <span style="font-size: 18px; font-weight: bold; color: #0F172A;">
                        <i class="fas fa-rocket"></i> Спринт #{sprint["number"]}
                    </span>
                    {status_badge}
                </div>
                <div style="font-size: 13px; color: #64748B; margin-bottom: 10px;">
                    <i class="fas fa-calendar"></i> {sprint["planned_start"]} — {sprint["planned_end"]}
                    {f'<span style="margin-left: 15px;"><i class="fas fa-clock"></i> {sprint["planned_end"]}</span>' if sprint['status'] == 'active' else ''}
                </div>
                <div style="font-size: 14px; font-weight: 500; margin-bottom: 10px;">
                    📈 Плановый рост: <strong>{sprint["planned_growth"]:.1f}%</strong>
                </div>
                {progress_bar}
                {actions_html}
                {actual_growth_html}
                {deviation_html}
                {action_button}
            </div>
            '''

        # Блок с активным спринтом (дополнительный, если есть)
        active_sprint_html = ''
        if active_sprint:
            actions_list = ''
            if active_sprint.get('actions'):
                for action in active_sprint['actions']:
                    actions_list += f'<li style="margin: 5px 0;">✅ {action["name"]}</li>'

            active_sprint_html = f'''
            <div style="background: linear-gradient(135deg, #DBEAFE 0%, #EFF6FF 100%); padding: 20px; border-radius: 16px; margin-bottom: 25px; border: 1px solid #BFDBFE;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                    <i class="fas fa-play-circle" style="font-size: 24px; color: #2563EB;"></i>
                    <h3 style="color: #1E40AF; margin: 0;">Активный спринт #{active_sprint["number"]}</h3>
                </div>
                <p><strong>Период:</strong> {active_sprint["planned_start"]} — {active_sprint["planned_end"]}</p>
                <p><strong>Плановый рост:</strong> {active_sprint["planned_growth"]:.1f}%</p>
                <p><strong>Действия:</strong></p>
                <ul style="margin-left: 20px; margin-bottom: 15px;">
                    {actions_list}
                </ul>
                <a href="/sprints/{active_sprint["id"]}/complete" style="display: inline-flex; align-items: center; gap: 8px; background: #10B981; color: white; padding: 10px 20px; border-radius: 10px; text-decoration: none;">
                    <i class="fas fa-check"></i> Завершить спринт
                </a>
            </div>
            '''

        # Полный HTML
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Спринты - Дорожная карта</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }}
        .container {{ max-width: 900px; margin: -20px auto 0; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; color: #0F172A; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }}
        .stat-card {{ background: white; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #3B82F6; }}
        .stat-label {{ font-size: 12px; color: #64748B; margin-top: 5px; }}
        .back-link {{ display: inline-block; margin-top: 20px; color: #64748B; text-decoration: none; }}
        .back-link:hover {{ color: #3B82F6; }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: #94A3B8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-tasks"></i> Управление спринтами</h1>
        <p>Пошаговая реализация дорожной карты для "{org_name}"</p>
    </div>
    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_sprints}</div>
                <div class="stat-label">Всего спринтов</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{completed_sprints}</div>
                <div class="stat-label">Завершено</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_count}</div>
                <div class="stat-label">Активных</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{planned_count}</div>
                <div class="stat-label">Запланировано</div>
            </div>
        </div>

        <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr);">
            <div class="stat-card">
                <div class="stat-number">{completion_rate:.0f}%</div>
                <div class="stat-label">Выполнение плана</div>
                <div style="height: 4px; background: #E2E8F0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
                    <div style="width: {completion_rate:.0f}%; height: 100%; background: #3B82F6;"></div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{growth_achievement:.0f}%</div>
                <div class="stat-label">Достигнутый рост</div>
                <div style="height: 4px; background: #E2E8F0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
                    <div style="width: {growth_achievement:.0f}%; height: 100%; background: #10B981;"></div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Спринты по плану</h2>

            {active_sprint_html}

            {sprints_html if sprints_html else '<div class="empty-state"><i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i><p>Нет спринтов для этого плана</p></div>'}

            <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
        </div>
    </div>
</body>
</html>'''

        return html


class SprintStartHandler(BaseHandler):
    """Запуск спринта"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role not in ['admin', 'analyst']:
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        sprint_id = params.get('sprint_id') if params else None
        if not sprint_id:
            return "<h1>ID спринта не указан</h1>", 'text/html; charset=utf-8'

        sprint_manager = SprintManager()
        result = sprint_manager.start_sprint(int(sprint_id))

        if result:
            # Получаем plan_id для редиректа
            db = DatabaseConnection()
            sprint = db.query_one("SELECT plan_id FROM sprints WHERE id = ?", (sprint_id,))
            plan_id = sprint['plan_id'] if sprint else None
            return self.render(template_engine, 'redirect.html', {'url': f'/sprints/{plan_id}/list'})
        else:
            return "<h1>Не удалось запустить спринт</h1>", 'text/html; charset=utf-8'


class SprintCompleteHandler(BaseHandler):
    """Завершение спринта с подробной формой ввода результатов"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role not in ['admin', 'analyst']:
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        sprint_id = params.get('sprint_id') if params else None
        if not sprint_id:
            return "<h1>ID спринта не указан</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()
        sprint = db.query_one("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        if not sprint:
            return "<h1>Спринт не найден</h1>", 'text/html; charset=utf-8'

        # Получаем действия в спринте
        action_ids = json.loads(sprint['action_ids']) if sprint['action_ids'] else []
        actions = []
        for aid in action_ids:
            action = db.query_one("SELECT * FROM actions WHERE id = ?", (aid,))
            if action:
                actions.append(action)

        if request['method'] == 'GET':
            # Форма для ввода результатов с деталями
            actions_html = ''
            for action in actions:
                actions_html += f'''
                <div style="background: #F8FAFC; padding: 12px; border-radius: 10px; margin-bottom: 10px;">
                    <strong>{action['name']}</strong>
                    <div style="display: flex; gap: 15px; margin-top: 5px; font-size: 12px; color: #64748B;">
                        <span>📈 Ожидаемый рост: {action['base_growth'] * 100:.0f}%</span>
                        <span>💰 Затраты: {action['cost'] * 100:.0f}%</span>
                        <span>⚠️ Риск: {action['risk'] * 100:.0f}%</span>
                    </div>
                </div>
                '''

            html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Завершение спринта</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }}
        .container {{ max-width: 600px; margin: -20px auto 0; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; font-weight: 500; margin-bottom: 8px; color: #0F172A; }}
        input, textarea, select {{ width: 100%; padding: 12px; border: 1px solid #E2E8F0; border-radius: 10px; font-size: 14px; }}
        button {{ background: #10B981; color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-weight: 500; width: 100%; }}
        .info {{ background: #DBEAFE; padding: 15px; border-radius: 12px; margin-bottom: 20px; }}
        .action-list {{ margin-top: 15px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Завершение спринта #{sprint["number"]}</h1>
        <p>Введите фактические результаты</p>
    </div>
    <div class="container">
        <div class="card">
            <div class="info">
                <strong><i class="fas fa-info-circle"></i> Информация о спринте</strong><br>
                📅 Период: {sprint["planned_start"]} — {sprint["planned_end"]}<br>
                📈 Плановый рост: <strong>{sprint["planned_growth"]:.1f}%</strong>
            </div>

            <div class="action-list">
                <strong><i class="fas fa-tasks"></i> Действия в спринте:</strong>
                {actions_html}
            </div>

            <form method="POST">
                <div class="form-group">
                    <label>📈 Фактический рост цифровой зрелости (%)</label>
                    <input type="number" step="0.1" name="actual_growth" required placeholder="Например: 12.5" value="{sprint["planned_growth"]:.1f}">
                    <small style="color: #64748B;">Плановое значение: {sprint["planned_growth"]:.1f}%</small>
                </div>

                <div class="form-group">
                    <label>📝 Что было сделано?</label>
                    <textarea name="notes" rows="4" placeholder="Опишите выполненные работы, достигнутые результаты..."></textarea>
                </div>

                <div class="form-group">
                    <label>⚠️ Возникшие сложности</label>
                    <textarea name="challenges" rows="3" placeholder="Какие были проблемы? Что можно улучшить в следующем спринте?"></textarea>
                </div>

                <div class="form-group">
                    <label>💰 Фактические затраты (% от бюджета)</label>
                    <input type="number" step="0.1" name="actual_cost" placeholder="Например: 18.5">
                </div>

                <button type="submit"><i class="fas fa-check"></i> Завершить спринт</button>
            </form>

            <a href="/sprints/{sprint["plan_id"]}/list" style="display: inline-block; margin-top: 15px; color: #64748B; text-decoration: none;">← Вернуться к спринтам</a>
        </div>
    </div>
</body>
</html>'''
            return html, 'text/html; charset=utf-8'

        elif request['method'] == 'POST':
            post_data = request['post_data']
            actual_growth = float(post_data.get('actual_growth', 0))
            notes = post_data.get('notes', '')
            challenges = post_data.get('challenges', '')
            actual_cost = post_data.get('actual_cost')

            full_notes = notes
            if challenges:
                full_notes += f"\n\nСложности: {challenges}"
            if actual_cost:
                full_notes += f"\nФактические затраты: {actual_cost}%"

            sprint_manager = SprintManager()
            result = sprint_manager.complete_sprint(int(sprint_id), actual_growth, full_notes)

            if result:
                return self.render(template_engine, 'redirect.html',
                                   {'url': f'/sprints/{sprint["plan_id"]}/list?message=Спринт успешно завершён'})
            else:
                return "<h1>Не удалось завершить спринт</h1>", 'text/html; charset=utf-8'

class SprintViewHandler(BaseHandler):
    """Просмотр конкретного спринта"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        sprint_id = params.get('sprint_id') if params else None
        if not sprint_id:
            return self.render(template_engine, 'error.html', {'message': 'ID спринта не указан'})

        db = DatabaseConnection()
        sprint = db.query_one("SELECT * FROM sprints WHERE id = ?", (sprint_id,))
        if not sprint:
            return self.render(template_engine, 'error.html', {'message': 'Спринт не найден'})

        action_ids = json.loads(sprint['action_ids']) if sprint['action_ids'] else []
        actions = []
        for aid in action_ids:
            action = db.query_one("SELECT id, name, description, base_growth FROM actions WHERE id = ?", (aid,))
            if action:
                actions.append(action)

        plan = db.query_one("SELECT org_id FROM transformation_plans WHERE id = ?", (sprint['plan_id'],))

        return self.render(template_engine, 'sprint_view.html', {
            'sprint': sprint,
            'actions': actions,
            'org_id': plan['org_id'] if plan else None,
            'user': request['session']
        })


class PlanRescheduleHandler(BaseHandler):
    """Перенос оставшихся спринтов после отклонения"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role not in ['admin', 'analyst']:
            return self.render(template_engine, 'error.html', {'message': 'Недостаточно прав'})

        plan_id = params.get('plan_id') if params else None
        if not plan_id:
            return self.render(template_engine, 'error.html', {'message': 'ID плана не указан'})

        deviation = request.get('query_params', {}).get('deviation', ['0'])[0]

        if request['method'] == 'GET':
            return self.render(template_engine, 'plan_reschedule.html', {
                'plan_id': plan_id,
                'deviation': deviation,
                'user': request['session']
            })

        elif request['method'] == 'POST':
            post_data = request['post_data']
            new_start_date = datetime.strptime(post_data.get('new_start_date'), '%Y-%m-%d')

            sprint_manager = SprintManager()
            result = sprint_manager.reschedule_remaining_sprints(int(plan_id), new_start_date)

            if result:
                return self.render(template_engine, 'redirect.html',
                                   {'url': f'/sprints/{plan_id}/list?message=План скорректирован'})
            else:
                return self.render(template_engine, 'error.html', {'message': 'Не удалось перенести спринты'})