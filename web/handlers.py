import json
from database.connection import DatabaseConnection
from database.models import Organization, Assessment, Action, TransformationPlan
from core.fuzzy_logic import DigitalMaturityModel
from core.environment import DigitalTransformationEnvironment
from core.dqn_agent import DQNAgent
from config import NUM_EPISODES, MAX_STEPS_PER_EPISODE, LEARNING_RATE, GAMMA_DQN, BUFFER_SIZE, BATCH_SIZE


class BaseHandler:
    def render(self, template_engine, template_name: str, context: dict = None):
        if context is None:
            context = {}
        content = template_engine.render(template_name, context)
        return content, 'text/html; charset=utf-8'

    def _check_auth(self, request) -> bool:
        """Проверка авторизации пользователя"""
        session = request.get('session', {})
        return session.get('valid', False)

    def _get_user_id(self, request) -> int:
        """Получение ID текущего пользователя из сессии"""
        user_id = request.get('session', {}).get('user_id')
        if user_id is None:
            # Если user_id нет в сессии, пробуем получить из cookie
            from database.user_model import UserManager
            session_token = request.get('cookies', {}).get('session_token')
            if session_token:
                um = UserManager()
                valid_session = um.validate_session(session_token)
                if valid_session.get('valid'):
                    user_id = valid_session.get('user_id')
        return user_id

    def _get_user_role(self, request) -> str:
        """Получение роли текущего пользователя"""
        return request.get('session', {}).get('role', 'viewer')


class IndexHandler(BaseHandler):
    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user = request['session']
        user_role = user.get('role', 'viewer')
        user_id = user.get('user_id')

        db = DatabaseConnection()

        # Получаем организации, к которым имеет доступ пользователь
        if user_role == 'admin':
            organizations = Organization.get_all()
        else:
            # Обычный пользователь видит только свои организации
            user_orgs = db.query(
                "SELECT DISTINCT org_id FROM assessments WHERE user_id = ?",
                (user_id,)
            )
            org_ids = [o['org_id'] for o in user_orgs]
            organizations = []
            for org_id in org_ids:
                org = Organization.get_by_id(org_id)
                if org:
                    organizations.append(org)

        # Генерируем HTML напрямую
        html = self._build_index_html(user, user_role, organizations)

        return html, 'text/html; charset=utf-8'

    def _build_index_html(self, user, user_role, organizations):
        """Построение HTML главной страницы"""

        # Роль на русском
        if user_role == 'admin':
            role_text = 'Администратор'
            show_dqn = True
        elif user_role == 'analyst':
            role_text = 'Аналитик'
            show_dqn = True
        else:
            role_text = 'Просмотр'
            show_dqn = False

        # Таблица организаций
        if organizations:
            table_rows = ''
            for org in organizations:
                created_date = org['created_at'][:10] if org['created_at'] else '-'
                table_rows += f'''
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 12px;">{org['id']}</td>
                    <td style="padding: 12px;"><strong>{org['name']}</strong></td>
                    <td style="padding: 12px;"><span style="background: #E2E8F0; padding: 4px 12px; border-radius: 20px; font-size: 12px;">{org['organization_type']}</span></td>
                    <td style="padding: 12px;">{created_date}</td>
                    <td style="padding: 12px;"><a href="/compare/{org['id']}" style="color: #3B82F6; text-decoration: none;">Анализ →</a></td>
                </tr>
                '''
        else:
            table_rows = '<tr><td colspan="5" style="padding: 40px; text-align: center;">Нет организаций. Создайте первую оценку.</td></tr>'

        # Кнопка DQN (только для админа и аналитика)
        dqn_button = ''
        if show_dqn:
            dqn_button = '<a href="/dynamic_planning" style="display: inline-block; padding: 10px 20px; background: #10B981; color: white; text-decoration: none; border-radius: 10px; margin: 5px;">🎯 DQN планирование</a>'

        # Панель администратора (только для админа)
        admin_panel = ''
        if user_role == 'admin':
            admin_panel = '''
            <div style="margin-top: 20px; padding: 20px; background: #F1F5F9; border-radius: 12px;">
                <h3 style="margin-bottom: 15px;">⚙️ Панель администратора</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <a href="/admin" style="display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px;">Управление системой</a>
                    <a href="/admin/actions" style="display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px;">Управление действиями</a>
                    <a href="/admin/scheduler" style="display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px;">Планировщик задач</a>
                </div>
            </div>
            '''

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Цифровая трансформация</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }}
        .user-info {{ display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }}
        .user-role {{ background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
        .logout-btn {{ color: #F87171; text-decoration: none; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; color: #0F172A; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin: 5px; }}
        .btn-secondary {{ background: #10B981; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
        th {{ background: #F1F5F9; font-weight: 600; }}
        .empty-state {{ text-align: center; padding: 60px 20px; color: #64748B; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Цифровая трансформация</h1>
        <div class="user-info">
            <span>{user.get('username', 'Гость')}</span>
            <span class="user-role">{role_text}</span>
            <a href="/logout" class="logout-btn">Выйти</a>
        </div>
    </div>

    <div class="container">
        <div class="card">
            <h2>Организации</h2>
            <div style="margin-bottom: 15px;">
                <a href="/assessment" class="btn">📊 Новая оценка</a>
                {dqn_button}
            </div>

            <table>
                <thead>
                    <tr>
                        <th>ID</th><th>Название</th><th>Тип</th><th>Дата создания</th><th></th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        {admin_panel}
    </div>
</body>
</html>'''

        return html


class AssessmentHandler(BaseHandler):
    def handle(self, request, template_engine, params=None):
        from core.fuzzy_logic import DigitalMaturityModel
        from database.connection import DatabaseConnection

        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        if request['method'] == 'GET':
            orgs = Organization.get_all()
            return self.render(template_engine, 'assessment.html', {
                'organizations': orgs,
                'user': request['session']
            })

        elif request['method'] == 'POST':
            # ОТЛАДКА
            print("[DEBUG] AssessmentHandler POST started")
            print(f"[DEBUG] Session content: {request['session']}")
            user_id = request['session'].get('user_id')
            print(f"[DEBUG] user_id from session: {user_id}")

            post_data = request['post_data']
            org_name = post_data.get('org_name', 'Новая организация')
            org_type = post_data.get('org_type', 'average')

            db = DatabaseConnection()

            existing = db.query_one("SELECT id FROM organizations WHERE name = ?", (org_name,))
            if existing:
                org_id = existing['id']
            else:
                org_id = db.execute(
                    "INSERT INTO organizations (name, organization_type) VALUES (?, ?)",
                    (org_name, org_type)
                )

            indicator_codes = [
                '1.1', '1.2', '1.3', '2.1', '2.2', '2.3',
                '3.1', '3.2', '3.3', '4.1', '4.2', '4.3',
                '5.1', '5.2', '5.3', '6.1', '6.2',
                '7.1', '7.2', '7.3', '8.1', '8.2', '8.3',
                '9.1', '9.2'
            ]

            scores = {}
            for code in indicator_codes:
                val = post_data.get(code, '1')
                try:
                    scores[code] = int(val)
                except:
                    scores[code] = 1

            model = DigitalMaturityModel()
            result = model.evaluate(scores)

            # Если user_id не найден, используем 1 (admin)
            if user_id is None:
                user_id = 1
                print("[DEBUG] user_id not found, using default: 1")

            assessment_id = db.execute(
                '''INSERT INTO assessments (org_id, user_id, final_score, technical_factor, 
                   cognitive_factor, personal_factor) VALUES (?, ?, ?, ?, ?, ?)''',
                (org_id, user_id, result['final_score'], result['technical_factor'],
                 result['cognitive_factor'], result['personal_factor'])
            )

            for code, value in scores.items():
                db.execute(
                    "INSERT INTO assessment_details (assessment_id, indicator_code, value) VALUES (?, ?, ?)",
                    (assessment_id, code, value)
                )

            return self.render(template_engine, 'redirect.html', {'url': f'/results/{assessment_id}'})


class ResultsHandler(BaseHandler):
    def handle(self, request, template_engine, params=None):
        # Проверка авторизации
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        assessment_id = params.get('id')

        if not assessment_id:
            return "<h1>ID оценки не указан</h1>", 'text/html; charset=utf-8'

        # Получаем user_id и user_role из сессии
        user_id = request['session'].get('user_id')
        user_role = request['session'].get('role', 'viewer')

        # Получаем оценку
        assessment = Assessment.get_by_id(int(assessment_id))

        # Проверка доступа: пользователь может видеть только свои оценки, кроме admin
        if assessment and assessment.get('user_id') != user_id and user_role != 'admin':
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        if not assessment:
            return "<h1>Оценка не найдена</h1>", 'text/html; charset=utf-8'

        final_score = assessment['final_score']
        technical = assessment['technical_factor']
        cognitive = assessment['cognitive_factor']
        personal = assessment['personal_factor']

        # Генерируем HTML напрямую
        html = self._generate_results_html(assessment, final_score, technical, cognitive, personal)

        return html, 'text/html; charset=utf-8'

    def _generate_results_html(self, assessment, final_score, technical, cognitive, personal):
        """Генерация HTML страницы результатов"""

        final_score_rounded = round(final_score, 1)
        technical_rounded = round(technical, 1)
        cognitive_rounded = round(cognitive, 1)
        personal_rounded = round(personal, 1)

        # Рекомендация
        if final_score < 40:
            recommendation = "🔴 Критический уровень. Необходима срочная цифровая трансформация."
        elif final_score < 60:
            recommendation = "🟡 Базовый уровень. Требуется системная работа по автоматизации."
        elif final_score < 80:
            recommendation = "🟢 Продвинутый уровень. Фокусируйтесь на интеграции систем."
        else:
            recommendation = "🏆 Высокий уровень. Поддерживайте лидерство."

        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Результаты оценки цифровой зрелости</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}

        .header {{
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            padding: 30px 24px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; color: white; }}

        .container {{ max-width: 800px; margin: -20px auto 0; padding: 0 20px 40px; }}

        .card {{
            background: white;
            border-radius: 24px;
            padding: 28px;
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }}

        .score-circle {{
            width: 180px;
            height: 180px;
            border-radius: 50%;
            margin: 0 auto;
            background: conic-gradient(#3B82F6 0deg {final_score * 3.6}deg, #E2E8F0 {final_score * 3.6}deg);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .score-inner {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .score-number {{ font-size: 42px; font-weight: bold; color: #3B82F6; }}

        .factors {{
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .factor {{
            text-align: center;
            flex: 1;
            padding: 15px;
            background: #F8FAFC;
            border-radius: 16px;
        }}
        .factor-value {{ font-size: 28px; font-weight: bold; }}
        .factor-technical {{ color: #3B82F6; }}
        .factor-cognitive {{ color: #F59E0B; }}
        .factor-personal {{ color: #10B981; }}

        .btn {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #3B82F6, #8B5CF6);
            color: white;
            text-decoration: none;
            border-radius: 40px;
            margin: 5px;
        }}
        .recommendation {{
            background: #EFF6FF;
            padding: 15px;
            border-radius: 16px;
            margin-top: 20px;
            border-left: 4px solid #3B82F6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Результаты оценки цифровой зрелости</h1>
    </div>

    <div class="container">
        <div class="card">
            <div class="score-circle">
                <div class="score-inner">
                    <div class="score-number">{final_score_rounded}</div>
                    <div style="font-size: 12px; color: #64748B;">из 100</div>
                </div>
            </div>

            <div class="factors">
                <div class="factor">
                    <h4>Технико-технологический</h4>
                    <div class="factor-value factor-technical">{technical_rounded}</div>
                </div>
                <div class="factor">
                    <h4>Когнитивный</h4>
                    <div class="factor-value factor-cognitive">{cognitive_rounded}</div>
                </div>
                <div class="factor">
                    <h4>Личностный</h4>
                    <div class="factor-value factor-personal">{personal_rounded}</div>
                </div>
            </div>

            <div class="recommendation">
                <strong>💡 Рекомендация</strong><br>
                {recommendation}
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="/" class="btn">На главную</a>
                <a href="/dynamic_planning" class="btn" style="background: #10B981;">Построить план</a>
            </div>
        </div>
    </div>
</body>
</html>'''

        return html


class PlanningHandler(BaseHandler):
    def handle(self, request, template_engine, params=None):
        import json
        from core.sprint_manager import SprintManager
        from database.connection import DatabaseConnection
        from core.fuzzy_logic import DigitalMaturityModel
        from core.environment import DigitalTransformationEnvironment
        from core.dqn_agent import DQNAgent
        from database.models import Action, TransformationPlan
        from config import MAX_STEPS_PER_EPISODE

        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        if request['method'] == 'GET':
            orgs = Organization.get_all()
            return self.render(template_engine, 'dynamic_planning.html', {
                'organizations': orgs,
                'user': request['session']
            })

        elif request['method'] == 'POST':
            post_data = request['post_data']
            org_id = int(post_data.get('org_id', 1))
            org_type = post_data.get('org_type', 'average')

            # Получение текущей оценки организации
            assessment = Assessment.get_latest(org_id)

            db = DatabaseConnection()

            if assessment:
                current_score = assessment['final_score']
                # ПРАВИЛЬНОЕ ПОЛУЧЕНИЕ DETAILS ИЗ БД
                details = db.query(
                    "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
                    (assessment['id'],)
                )
                initial_scores = {d['indicator_code']: d['value'] for d in details}
                assessment_id = assessment['id']
            else:
                current_score = 30.0
                assessment_id = None
                model = DigitalMaturityModel()
                indicator_codes = list(model.indicator_keys.keys())
                initial_scores = {code: 1 for code in indicator_codes}

            # Целевой уровень
            target_score = min(100, current_score + 25)
            needed_growth = target_score - current_score

            # Получение действий
            actions = Action.get_all()
            if not actions:
                Action.initialize_default_actions()
                actions = Action.get_all()

            # Анализ слабых блоков (если есть оценка)
            weak_blocks = []
            if assessment:
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
                block_values = {i: [] for i in range(1, 10)}
                for code, value in initial_scores.items():
                    block_id = block_map.get(code, 1)
                    block_values[block_id].append(value)

                for block_id in range(1, 10):
                    if block_values[block_id]:
                        avg = sum(block_values[block_id]) / len(block_values[block_id])
                        if avg <= 1.0:
                            weak_blocks.append(block_id)

            # Генерация плана
            plan = []
            used_actions = set()
            cumulative_growth = 0
            step_score = current_score

            block_keywords = {
                1: ['личн', 'персон', 'человек', 'культур'],
                2: ['компетенц', 'обучен', 'навык', 'курс'],
                3: ['организац', 'культур', 'управлен', 'менеджмент'],
                4: ['процесс', 'автоматизац', 'оптимизац'],
                5: ['продукт', 'сервис', 'разработк'],
                6: ['модел', 'аналитик', 'метод'],
                7: ['данн', 'аналитик', 'хранилище'],
                8: ['инфраструктур', 'инструмент', 'платформ', 'безопасн'],
                9: ['глобальн', 'среда', 'единство', 'интеграц']
            }

            # Сначала действия для слабых блоков
            for block_id in weak_blocks:
                keywords = block_keywords.get(block_id, [])
                for action in actions:
                    action_id = action.get('id')
                    if action_id in used_actions:
                        continue
                    action_name = action.get('name', '').lower()
                    match = any(kw in action_name for kw in keywords)
                    if match or not keywords:
                        used_actions.add(action_id)
                        growth_pct = action.get('base_growth', 0.08) * 100
                        cost_pct = action.get('cost', 0.1) * 100
                        risk_pct = action.get('risk', 0.1) * 100
                        cumulative_growth += growth_pct
                        step_score = min(100, current_score + cumulative_growth)
                        step_progress = (step_score / target_score) * 100 if target_score > 0 else 0
                        plan.append({
                            'step': len(plan) + 1,
                            'action_id': action_id,
                            'action_name': action.get('name', f'Действие {len(plan) + 1}'),
                            'description': action.get('description', ''),
                            'timeframe': action.get('timeframe', '1-2 месяца'),
                            'base_growth': f"{growth_pct:.1f}",
                            'base_growth_raw': growth_pct,
                            'cost': f"{cost_pct:.1f}",
                            'cost_raw': cost_pct,
                            'risk': f"{risk_pct:.1f}",
                            'risk_raw': risk_pct,
                            'expected_maturity': f"{step_score:.1f}",
                            'progress': f"{step_progress:.1f}",
                            'target_block': f"Блок {block_id}"
                        })
                        break

            # Затем лучшие оставшиеся действия
            remaining_actions = [a for a in actions if a['id'] not in used_actions]
            remaining_actions.sort(key=lambda x: x.get('base_growth', 0), reverse=True)

            for action in remaining_actions[:8 - len(plan)]:
                growth_pct = action.get('base_growth', 0.08) * 100
                cost_pct = action.get('cost', 0.1) * 100
                risk_pct = action.get('risk', 0.1) * 100
                cumulative_growth += growth_pct
                step_score = min(100, current_score + cumulative_growth)
                step_progress = (step_score / target_score) * 100 if target_score > 0 else 0
                plan.append({
                    'step': len(plan) + 1,
                    'action_id': action['id'],
                    'action_name': action.get('name', f'Действие {len(plan) + 1}'),
                    'description': action.get('description', ''),
                    'timeframe': action.get('timeframe', '1-2 месяца'),
                    'base_growth': f"{growth_pct:.1f}",
                    'base_growth_raw': growth_pct,
                    'cost': f"{cost_pct:.1f}",
                    'cost_raw': cost_pct,
                    'risk': f"{risk_pct:.1f}",
                    'risk_raw': risk_pct,
                    'expected_maturity': f"{step_score:.1f}",
                    'progress': f"{step_progress:.1f}",
                    'target_block': 'Общее развитие'
                })

            # Сохранение плана
            user_id = request['session'].get('user_id', 1)
            plan_id = db.execute(
                '''INSERT INTO transformation_plans 
                   (org_id, user_id, final_maturity, plan_data, status) 
                   VALUES (?, ?, ?, ?, ?)''',
                (org_id, user_id, current_score, json.dumps(plan, ensure_ascii=False), 'active')
            )

            # Создание спринтов
            sprint_manager = SprintManager()
            sprints_created = sprint_manager.create_sprints_from_plan(plan_id, plan)

            # Данные для графика
            plan_chart_steps = [f"Шаг {p['step']}" for p in plan]
            plan_chart_growth = [float(p['base_growth']) for p in plan]
            plan_chart_costs = [float(p['cost']) for p in plan]
            total_progress = (current_score / target_score) * 100 if target_score > 0 else 0
            message = f'Построен план из {len(plan)} шагов. Ожидаемый рост: +{cumulative_growth:.1f} баллов. Создано {len(sprints_created)} спринтов.'

            # HTML результат
            html = self._build_plan_html(
                plan, current_score, target_score, needed_growth,
                total_progress, plan_chart_steps, plan_chart_growth, plan_chart_costs,
                assessment_id, org_id, plan_id, message
            )

            return html, 'text/html; charset=utf-8'

    def _build_plan_html(self, plan, current_score, target_score, needed_growth,
                         total_progress, plan_chart_steps, plan_chart_growth, plan_chart_costs,
                         assessment_id, org_id, plan_id, message):
        import json
        import random

        # Генерация уникального ID для графика
        chart_id = f"chart_{random.randint(1000, 9999)}"

        rationale_html = ''
        for step in plan:
            rationale_html += f'''
            <div class="rationale-item" data-step="{step['step']}">
                <span class="rationale-step">{step['step']}</span>
                <span class="rationale-text">{step['action_name']}</span>
                <span class="rationale-growth">+{step['base_growth']}%</span>
            </div>
            '''

        plan_html = ''
        for step in plan:
            growth_class = 'high-growth' if float(step['base_growth']) > 15 else 'medium-growth' if float(
                step['base_growth']) > 8 else 'low-growth'
            risk_class = 'high-risk' if float(step['risk']) > 20 else 'medium-risk' if float(
                step['risk']) > 12 else 'low-risk'

            plan_html += f'''
            <div class="roadmap-node" data-step="{step['step']}">
                <div class="node-marker">
                    <div class="node-number">{step['step']}</div>
                    <div class="node-line"></div>
                </div>
                <div class="node-card">
                    <div class="card-header">
                        <h3 class="card-title">{step['action_name']}</h3>
                        <div class="card-badge {growth_class}">+{step['base_growth']}%</div>
                    </div>
                    <div class="card-stats">
                        <div class="stat">
                            <span class="stat-icon">💰</span>
                            <span class="stat-value">{step['cost']}%</span>
                            <span class="stat-label">ресурсов</span>
                        </div>
                        <div class="stat">
                            <span class="stat-icon">⚠️</span>
                            <span class="stat-value">{step['risk']}%</span>
                            <span class="stat-label {risk_class}">риск</span>
                        </div>
                        <div class="stat">
                            <span class="stat-icon">🎯</span>
                            <span class="stat-value">{step['expected_maturity']}</span>
                            <span class="stat-label">баллов</span>
                        </div>
                    </div>
                    <div class="card-progress">
                        <div class="progress-track">
                            <div class="progress-fill" style="width: {step['progress']}%;"></div>
                        </div>
                    </div>
                </div>
            </div>
            '''

        html = f'''<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Стратегическая карта развития</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Inter', sans-serif; 
                background: #0A0C10;
                color: #E8EDF2;
                line-height: 1.5;
            }}

            /* Анимированный градиентный фон */
            .animated-bg {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(circle at 20% 30%, #1a1a2e, #0A0C10);
                z-index: -2;
            }}

            .animated-bg::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle at 30% 40%, rgba(100, 80, 200, 0.08), transparent);
                animation: pulse 8s ease-in-out infinite;
            }}

            @keyframes pulse {{
                0%, 100% {{ transform: translate(0, 0) scale(1); opacity: 0.5; }}
                50% {{ transform: translate(5%, 5%) scale(1.2); opacity: 0.8; }}
            }}

            /* Хедер */
            .hero {{
                position: relative;
                padding: 60px 24px 40px;
                text-align: center;
                overflow: hidden;
            }}

            .hero::after {{
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, #667eea, #a855f7, #667eea, transparent);
            }}

            .hero-badge {{
                display: inline-block;
                background: rgba(102, 126, 234, 0.15);
                backdrop-filter: blur(4px);
                padding: 6px 16px;
                border-radius: 40px;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.5px;
                color: #a855f7;
                border: 1px solid rgba(168, 85, 247, 0.3);
                margin-bottom: 20px;
            }}

            .hero h1 {{
                font-size: 48px;
                font-weight: 700;
                background: linear-gradient(135deg, #fff, #a855f7, #667eea);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                margin-bottom: 12px;
                letter-spacing: -0.02em;
            }}

            .hero p {{
                font-size: 16px;
                color: #8E9AAF;
                max-width: 500px;
                margin: 0 auto;
            }}

            /* Контейнер */
            .container {{
                max-width: 1000px;
                margin: -20px auto 0;
                padding: 0 24px 48px;
                position: relative;
                z-index: 2;
            }}

            /* Карточки метрик */
            .metrics-panel {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-bottom: 32px;
            }}

            .metric-card {{
                background: rgba(18, 20, 28, 0.8);
                backdrop-filter: blur(10px);
                border-radius: 24px;
                padding: 20px;
                border: 1px solid rgba(255,255,255,0.05);
                transition: all 0.3s ease;
            }}

            .metric-card:hover {{
                transform: translateY(-4px);
                border-color: rgba(102, 126, 234, 0.3);
                box-shadow: 0 20px 30px -15px rgba(0,0,0,0.3);
            }}

            .metric-label {{
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #8E9AAF;
                margin-bottom: 8px;
            }}

            .metric-value {{
                font-size: 28px;
                font-weight: 700;
                color: #fff;
            }}

            .metric-trend {{
                font-size: 13px;
                margin-top: 8px;
                color: #10B981;
            }}

            /* График */
            .chart-panel {{
                background: rgba(18, 20, 28, 0.6);
                backdrop-filter: blur(8px);
                border-radius: 28px;
                padding: 24px;
                margin-bottom: 32px;
                border: 1px solid rgba(255,255,255,0.05);
            }}

            .chart-panel h3 {{
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 20px;
                color: #a855f7;
                letter-spacing: 0.5px;
            }}

            .chart-container {{
                height: 280px;
                position: relative;
            }}

            /* Дорожная карта */
            .roadmap {{
                position: relative;
                padding-left: 30px;
            }}

            .roadmap::before {{
                content: '';
                position: absolute;
                left: 45px;
                top: 0;
                bottom: 0;
                width: 2px;
                background: linear-gradient(180deg, #667eea, #a855f7, #667eea);
                opacity: 0.3;
            }}

            .roadmap-node {{
                display: flex;
                margin-bottom: 32px;
                position: relative;
            }}

            .node-marker {{
                position: relative;
                width: 60px;
                flex-shrink: 0;
            }}

            .node-number {{
                width: 36px;
                height: 36px;
                background: linear-gradient(135deg, #667eea, #a855f7);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 14px;
                color: white;
                box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
                transition: all 0.2s;
            }}

            .roadmap-node:hover .node-number {{
                transform: scale(1.1);
                box-shadow: 0 0 0 6px rgba(102, 126, 234, 0.3);
            }}

            .node-card {{
                flex: 1;
                background: rgba(25, 28, 38, 0.9);
                backdrop-filter: blur(8px);
                border-radius: 20px;
                padding: 20px;
                border: 1px solid rgba(255,255,255,0.08);
                transition: all 0.3s ease;
                cursor: pointer;
            }}

            .node-card:hover {{
                transform: translateX(8px);
                border-color: rgba(102, 126, 234, 0.4);
                background: rgba(30, 33, 45, 0.95);
            }}

            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                flex-wrap: wrap;
                gap: 10px;
            }}

            .card-title {{
                font-size: 17px;
                font-weight: 600;
                color: #fff;
            }}

            .card-badge {{
                padding: 4px 12px;
                border-radius: 30px;
                font-size: 12px;
                font-weight: 600;
            }}

            .high-growth {{ background: linear-gradient(135deg, #10B981, #059669); color: white; }}
            .medium-growth {{ background: linear-gradient(135deg, #F59E0B, #D97706); color: white; }}
            .low-growth {{ background: linear-gradient(135deg, #3B82F6, #2563EB); color: white; }}

            .high-risk {{ color: #EF4444; }}
            .medium-risk {{ color: #F59E0B; }}
            .low-risk {{ color: #10B981; }}

            .card-stats {{
                display: flex;
                gap: 24px;
                margin-bottom: 16px;
                flex-wrap: wrap;
            }}

            .stat {{
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 13px;
            }}

            .stat-icon {{
                font-size: 16px;
            }}

            .stat-value {{
                font-weight: 600;
                color: #fff;
            }}

            .stat-label {{
                color: #8E9AAF;
            }}

            .progress-track {{
                height: 4px;
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                overflow: hidden;
            }}

            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #667eea, #a855f7);
                border-radius: 4px;
                transition: width 0.5s ease;
            }}

            /* Рациональное обоснование */
            .rationale-panel {{
                background: rgba(18, 20, 28, 0.6);
                backdrop-filter: blur(8px);
                border-radius: 24px;
                padding: 24px;
                margin: 32px 0;
                border: 1px solid rgba(255,255,255,0.05);
            }}

            .rationale-panel h3 {{
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 20px;
                color: #a855f7;
            }}

            .rationale-grid {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}

            .rationale-item {{
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 12px;
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                transition: all 0.2s;
            }}

            .rationale-item:hover {{
                background: rgba(102, 126, 234, 0.1);
                transform: translateX(4px);
            }}

            .rationale-step {{
                width: 28px;
                height: 28px;
                background: rgba(102, 126, 234, 0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: 600;
                color: #a855f7;
            }}

            .rationale-text {{
                flex: 1;
                font-size: 13px;
                color: #CBD5E1;
            }}

            .rationale-growth {{
                font-size: 13px;
                font-weight: 600;
                color: #10B981;
            }}

            /* Кнопки */
            .action-buttons {{
                display: flex;
                justify-content: center;
                gap: 16px;
                margin-top: 32px;
                flex-wrap: wrap;
            }}

            .btn {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 24px;
                border-radius: 40px;
                font-weight: 500;
                font-size: 14px;
                text-decoration: none;
                transition: all 0.2s;
                cursor: pointer;
                border: none;
            }}

            .btn-primary {{
                background: linear-gradient(135deg, #667eea, #a855f7);
                color: white;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }}

            .btn-primary:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }}

            .btn-secondary {{
                background: rgba(255,255,255,0.08);
                color: #CBD5E1;
                border: 1px solid rgba(255,255,255,0.1);
            }}

            .btn-secondary:hover {{
                background: rgba(255,255,255,0.12);
                transform: translateY(-2px);
            }}

            .btn-outline {{
                background: transparent;
                border: 1px solid rgba(102, 126, 234, 0.5);
                color: #667eea;
            }}

            .btn-outline:hover {{
                background: rgba(102, 126, 234, 0.1);
                transform: translateY(-2px);
            }}

            @media (max-width: 768px) {{
                .hero h1 {{ font-size: 32px; }}
                .metrics-panel {{ grid-template-columns: 1fr; }}
                .roadmap {{ padding-left: 15px; }}
                .roadmap::before {{ left: 25px; }}
                .card-stats {{ gap: 12px; }}
            }}

            @media print {{
                .animated-bg, .action-buttons {{ display: none; }}
                body {{ background: white; color: black; }}
                .metric-card, .chart-panel, .node-card, .rationale-panel {{
                    background: white;
                    border: 1px solid #ddd;
                    color: black;
                }}
                .card-title, .stat-value {{ color: black; }}
            }}
        </style>
    </head>
    <body>
        <div class="animated-bg"></div>

        <div class="hero">
            <div class="hero-badge">
                <span>⚡ DQN OPTIMIZED</span>
            </div>
            <h1>Стратегическая карта<br>цифровой трансформации</h1>
            <p>Адаптивный план на основе глубокого обучения с подкреплением</p>
        </div>

        <div class="container">
            <div class="metrics-panel">
                <div class="metric-card">
                    <div class="metric-label">📊 ТЕКУЩАЯ ЗРЕЛОСТЬ</div>
                    <div class="metric-value">{current_score:.1f} <span style="font-size: 14px;">баллов</span></div>
                    <div class="metric-trend">↑ Необходимо +{needed_growth:.1f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">🎯 ЦЕЛЕВОЙ УРОВЕНЬ</div>
                    <div class="metric-value">{target_score:.1f} <span style="font-size: 14px;">баллов</span></div>
                    <div class="metric-trend">🏆 Лидерский уровень</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">📈 ПРОГРЕСС</div>
                    <div class="metric-value">{total_progress:.1f}%</div>
                    <div class="progress-track" style="margin-top: 12px;">
                        <div class="progress-fill" style="width: {total_progress:.1f}%;"></div>
                    </div>
                </div>
            </div>

            <div class="chart-panel">
                <h3>📈 ТРАЕКТОРИЯ РАЗВИТИЯ</h3>
                <div class="chart-container">
                    <canvas id="{chart_id}"></canvas>
                </div>
            </div>

            <div class="roadmap">
                {plan_html}
            </div>

            <div class="rationale-panel">
                <h3>🧠 ЛОГИЧЕСКОЕ ОБОСНОВАНИЕ</h3>
                <div class="rationale-grid">
                    {rationale_html}
                </div>
            </div>

            <div class="action-buttons">
                <a href="/" class="btn btn-secondary">← На главную</a>
                <a href="/sprints/{plan_id}/list" class="btn btn-primary">🚀 Управление спринтами</a>
                {f'<a href="/results/{assessment_id}" class="btn btn-outline">📊 К оценке ЦЗ</a>' if assessment_id else ''}
                <button onclick="window.print()" class="btn btn-secondary">🖨️ Сохранить PDF</button>
            </div>
        </div>

        <script>
            const steps = {json.dumps(plan_chart_steps)};
            const growth = {json.dumps(plan_chart_growth)};
            const costs = {json.dumps(plan_chart_costs)};

            new Chart(document.getElementById('{chart_id}'), {{
                type: 'line',
                data: {{
                    labels: steps,
                    datasets: [
                        {{
                            label: 'Ожидаемый рост (%)',
                            data: growth,
                            borderColor: '#a855f7',
                            backgroundColor: 'rgba(168, 85, 247, 0.05)',
                            fill: true,
                            tension: 0.3,
                            pointBackgroundColor: '#a855f7',
                            pointBorderColor: '#fff',
                            pointRadius: 5,
                            pointHoverRadius: 7
                        }},
                        {{
                            label: 'Затраты ресурсов (%)',
                            data: costs,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.05)',
                            fill: true,
                            tension: 0.3,
                            pointBackgroundColor: '#667eea',
                            pointBorderColor: '#fff',
                            pointRadius: 5,
                            pointHoverRadius: 7
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            labels: {{ color: '#CBD5E1', usePointStyle: true, boxWidth: 8 }}
                        }},
                        tooltip: {{
                            backgroundColor: '#1E293B',
                            titleColor: '#F1F5F9',
                            bodyColor: '#94A3B8',
                            borderColor: '#a855f7',
                            borderWidth: 1
                        }}
                    }},
                    scales: {{
                        y: {{
                            grid: {{ color: 'rgba(255,255,255,0.05)' }},
                            title: {{ display: true, text: 'Проценты (%)', color: '#8E9AAF' }}
                        }},
                        x: {{
                            grid: {{ display: false }},
                            title: {{ display: true, text: 'Шаги трансформации', color: '#8E9AAF' }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>'''

        return html


class CompareHandler(BaseHandler):
    """Страница сравнения оценок с детальной аналитикой"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id')
        if not org_id:
            return self.render(template_engine, 'error.html', {'message': 'Организация не найдена'})

        db = DatabaseConnection()

        # Получаем организацию
        org = Organization.get_by_id(int(org_id))
        if not org:
            return self.render(template_engine, 'error.html', {'message': 'Организация не найдена'})

        # Получаем все оценки организации
        assessments = Assessment.get_by_org(int(org_id))

        # Получаем последнюю оценку для детального анализа
        latest_assessment = assessments[0] if assessments else None

        if not latest_assessment:
            return self.render(template_engine, 'compare.html', {
                'org': org,
                'assessments': [],
                'has_data': False,
                'user': request['session']
            })

        # Получаем детали последней оценки
        details = db.query(
            "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
            (latest_assessment['id'],)
        )
        scores = {d['indicator_code']: d['value'] for d in details}

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

        block_names = {
            1: 'Личностный фактор', 2: 'Компетенции', 3: 'Организационная культура',
            4: 'Процессы', 5: 'Продукты', 6: 'Модели',
            7: 'Данные', 8: 'Инфраструктура', 9: 'Глобальная среда'
        }

        # Вычисляем средние по блокам
        block_values = {i: [] for i in range(1, 10)}
        for code, value in scores.items():
            block_id = block_map.get(code, 1)
            block_values[block_id].append(value)

        block_scores = {}
        for block_id in range(1, 10):
            if block_values[block_id]:
                avg = sum(block_values[block_id]) / len(block_values[block_id])
                block_scores[block_id] = avg
            else:
                block_scores[block_id] = 0

        # Определяем слабые и сильные блоки
        weak_blocks = []
        strong_blocks = []
        for block_id, score in block_scores.items():
            if score <= 1.0:
                weak_blocks.append({'id': block_id, 'name': block_names[block_id], 'score': score})
            elif score >= 2.5:
                strong_blocks.append({'id': block_id, 'name': block_names[block_id], 'score': score})

        # Рекомендации по слабым блокам
        recommendations = []
        for wb in weak_blocks:
            if wb['id'] == 1:
                recommendations.append(
                    "Проведите опрос сотрудников о цифровой культуре, организуйте обучение цифровой этике")
            elif wb['id'] == 2:
                recommendations.append(
                    "Запустите программу повышения цифровой грамотности, организуйте курсы по работе с аналитикой")
            elif wb['id'] == 3:
                recommendations.append(
                    "Внедрите цифровые инструменты управления задачами, поощряйте инициативы сотрудников")
            elif wb['id'] == 4:
                recommendations.append("Проведите реинжиниринг ключевых процессов, автоматизируйте рутинные операции")
            elif wb['id'] == 5:
                recommendations.append("Создайте продуктовую команду, запустите пилотный цифровой продукт")
            elif wb['id'] == 6:
                recommendations.append(
                    "Внедрите системы поддержки принятия решений, развивайте аналитические компетенции")
            elif wb['id'] == 7:
                recommendations.append("Создайте единое хранилище данных, внедрите систему управления качеством данных")
            elif wb['id'] == 8:
                recommendations.append("Модернизируйте IT-инфраструктуру, внедрите облачные сервисы")
            elif wb['id'] == 9:
                recommendations.append("Развивайте партнёрства с EdTech-компаниями, участвуйте в цифровых сообществах")

        # Данные для графика динамики
        dates = []
        scores_history = []
        technical_history = []
        cognitive_history = []
        personal_history = []

        for a in reversed(assessments):  # в хронологическом порядке
            dates.append(a['assessment_date'][:10])
            scores_history.append(a['final_score'])
            technical_history.append(a['technical_factor'])
            cognitive_history.append(a['cognitive_factor'])
            personal_history.append(a['personal_factor'])

        import json
        dates_json = json.dumps(dates)
        scores_json = json.dumps(scores_history)
        technical_json = json.dumps(technical_history)
        cognitive_json = json.dumps(cognitive_history)
        personal_json = json.dumps(personal_history)

        # Прогресс
        if len(scores_history) > 1:
            first_score = scores_history[0]
            last_score = scores_history[-1]
            growth = last_score - first_score
            growth_percent = (growth / first_score * 100) if first_score > 0 else 0
        else:
            growth = 0
            growth_percent = 0

        # Генерируем HTML через обычную конкатенацию строк (без f-строк)
        html = self._build_compare_html(
            org, assessments, latest_assessment, block_scores, block_names,
            weak_blocks, strong_blocks, recommendations,
            dates_json, scores_json, technical_json, cognitive_json, personal_json,
            growth, growth_percent
        )

        return html, 'text/html; charset=utf-8'

    def _build_compare_html(self, org, assessments, latest_assessment, block_scores, block_names,
                            weak_blocks, strong_blocks, recommendations,
                            dates_json, scores_json, technical_json, cognitive_json, personal_json,
                            growth, growth_percent):
        """Построение HTML страницы сравнения с детальной аналитикой (без f-строк)"""

        # Блоки для отображения
        blocks_html = ''
        for block_id in range(1, 10):
            score = block_scores.get(block_id, 0)
            score_percent = (score / 3) * 100

            # Цвет в зависимости от оценки
            if score <= 1:
                bar_color = '#EF4444'
                status_text = 'Требует внимания'
            elif score <= 2:
                bar_color = '#F59E0B'
                status_text = 'Средний уровень'
            else:
                bar_color = '#10B981'
                status_text = 'Хороший уровень'

            blocks_html += '''
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 500;">''' + block_names[block_id] + '''</span>
                    <span style="font-size: 14px; color: ''' + bar_color + ''';">''' + f"{score:.1f}" + ''' / 3.0 (''' + f"{score_percent:.0f}" + '''%)</span>
                </div>
                <div style="height: 8px; background: #E2E8F0; border-radius: 4px; overflow: hidden;">
                    <div style="width: ''' + f"{score_percent:.0f}" + '''%; height: 100%; background: ''' + bar_color + '''; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 11px; color: #64748B; margin-top: 3px;">''' + status_text + '''</div>
            </div>
            '''

        # Слабые блоки
        weak_html = ''
        for wb in weak_blocks:
            weak_html += '<li style="margin: 8px 0; padding: 8px; background: #FEE2E2; border-radius: 8px;"><strong>' + \
                         wb["name"] + '</strong> (оценка: ' + f"{wb['score']:.1f}" + '/3.0)</li>'

        if not weak_html:
            weak_html = '<li style="color: #10B981;">✅ Слабых блоков не обнаружено. Отличный результат!</li>'

        # Сильные блоки
        strong_html = ''
        for sb in strong_blocks:
            strong_html += '<li style="margin: 8px 0; padding: 8px; background: #D1FAE5; border-radius: 8px;"><strong>' + \
                           sb["name"] + '</strong> (оценка: ' + f"{sb['score']:.1f}" + '/3.0)</li>'

        if not strong_html:
            strong_html = '<li style="color: #64748B;">Пока нет блоков с высокими оценками. Продолжайте развитие!</li>'

        # Рекомендации
        rec_html = ''
        for rec in recommendations[:5]:
            rec_html += '<li style="margin: 10px 0; padding: 10px; background: #EFF6FF; border-radius: 8px;"><i class="fas fa-lightbulb" style="color: #F59E0B; margin-right: 10px;"></i>' + rec + '</li>'

        if not rec_html:
            rec_html = '<li style="color: #10B981;">✅ Все блоки на хорошем уровне. Поддерживайте достигнутый результат!</li>'

        # Таблица истории оценок
        history_rows = ''
        for a in assessments:
            date_str = str(a['assessment_date'])[:19] if a['assessment_date'] else ''
            history_rows += '''
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 10px;">''' + date_str + '''</td>
                <td style="padding: 10px;"><strong>''' + f"{a['final_score']:.1f}" + '''</strong></td>
                <td style="padding: 10px;">''' + f"{a['technical_factor']:.1f}" + '''</td>
                <td style="padding: 10px;">''' + f"{a['cognitive_factor']:.1f}" + '''</td>
                <td style="padding: 10px;">''' + f"{a['personal_factor']:.1f}" + '''</td>
            </tr>
            '''

        assessments_count = len(assessments)
        growth_class = 'growth-positive' if growth >= 0 else 'growth-negative'

        # Полный HTML
        html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Аналитика - ''' + org['name'] + '''</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #F8FAFC; }
        .header { background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }
        .container { max-width: 1200px; margin: -20px auto 0; padding: 20px; }
        .card { background: white; border-radius: 20px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h2 { margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; color: #0F172A; }
        h3 { margin-bottom: 15px; color: #1E293B; font-size: 18px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; border-radius: 12px; padding: 15px; text-align: center; border: 1px solid #E2E8F0; }
        .stat-number { font-size: 28px; font-weight: bold; color: #3B82F6; }
        .stat-label { font-size: 12px; color: #64748B; margin-top: 5px; }
        .btn { display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin: 5px; }
        .btn-secondary { background: #10B981; }
        .back-link { display: inline-block; margin-top: 20px; color: #64748B; text-decoration: none; }
        .chart-container { height: 300px; margin: 20px 0; }
        .info-box { background: #F1F5F9; padding: 15px; border-radius: 12px; margin: 15px 0; }
        .growth-positive { color: #10B981; }
        .growth-negative { color: #EF4444; }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-chart-line"></i> Аналитика организации</h1>
        <p>''' + org['name'] + ''' | Тип: ''' + org.get('organization_type', 'average') + '''</p>
    </div>

    <div class="container">
        <!-- Статистика -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">''' + f"{latest_assessment['final_score']:.1f}" + '''</div>
                <div class="stat-label">Текущий уровень ЦЗ</div>
            </div>
            <div class="stat-card">
                <div class="stat-number ''' + growth_class + '''">''' + f"{growth:+.1f}" + '''</div>
                <div class="stat-label">Рост за период</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">''' + str(assessments_count) + '''</div>
                <div class="stat-label">Выполнено оценок</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">''' + str(len(weak_blocks)) + '''</div>
                <div class="stat-label">Слабых блоков</div>
            </div>
        </div>

        <!-- Динамика ЦЗ -->
        <div class="card">
            <h2>📈 Динамика цифровой зрелости</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
            <div class="info-box">
                <strong>Текущий уровень:</strong> ''' + f"{latest_assessment['final_score']:.1f}" + ''' баллов
                <br><strong>Рост:</strong> <span class="''' + growth_class + '''">''' + f"{growth:+.1f}" + ''' баллов (''' + f"{growth_percent:+.1f}" + '''%)</span>
            </div>
        </div>

        <div class="grid-2">
            <!-- Факторы ЦЗ -->
            <div class="card">
                <h2>🎯 Факторы цифровой зрелости</h2>
                <div class="chart-container" style="height: 250px;">
                    <canvas id="factorsChart"></canvas>
                </div>
                <div class="info-box">
                    <div><span style="display: inline-block; width: 12px; height: 12px; background: #3B82F6; border-radius: 2px; margin-right: 8px;"></span> Технико-технологический: ''' + f"{latest_assessment['technical_factor']:.1f}" + ''' баллов</div>
                    <div style="margin-top: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background: #F59E0B; border-radius: 2px; margin-right: 8px;"></span> Когнитивный: ''' + f"{latest_assessment['cognitive_factor']:.1f}" + ''' баллов</div>
                    <div style="margin-top: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background: #10B981; border-radius: 2px; margin-right: 8px;"></span> Личностный: ''' + f"{latest_assessment['personal_factor']:.1f}" + ''' баллов</div>
                </div>
            </div>

            <!-- Динамика факторов -->
            <div class="card">
                <h2>📊 Динамика факторов</h2>
                <div class="chart-container" style="height: 250px;">
                    <canvas id="factorsTrendChart"></canvas>
                </div>
            </div>
        </div>

        <div class="grid-2">
            <!-- Оценка по блокам -->
            <div class="card">
                <h2>📋 Оценка по блокам</h2>
                ''' + blocks_html + '''
            </div>

            <!-- Сильные и слабые стороны -->
            <div class="card">
                <h2>⚠️ Сильные и слабые стороны</h2>

                <h3 style="margin-top: 0;">🔴 Требуют внимания (слабые блоки)</h3>
                <ul style="margin-left: 20px; margin-bottom: 20px;">
                    ''' + weak_html + '''
                </ul>

                <h3>🟢 Сильные стороны</h3>
                <ul style="margin-left: 20px;">
                    ''' + strong_html + '''
                </ul>
            </div>
        </div>

        <!-- Рекомендации -->
        <div class="card">
            <h2>💡 Рекомендации по развитию</h2>
            <ul style="margin-left: 20px;">
                ''' + rec_html + '''
            </ul>
            <div style="margin-top: 20px; padding: 15px; background: #F1F5F9; border-radius: 12px;">
                <strong><i class="fas fa-rocket"></i> Следующий шаг:</strong>
                <a href="/dynamic_planning" style="color: #3B82F6; text-decoration: none;">Перейти к DQN-планированию →</a>
            </div>
        </div>

        <!-- История оценок -->
        <div class="card">
            <h2>📜 История оценок</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #F1F5F9;">
                        <th style="padding: 12px; text-align: left;">Дата</th>
                        <th style="padding: 12px; text-align: left;">Итоговый балл</th>
                        <th style="padding: 12px; text-align: left;">Технический</th>
                        <th style="padding: 12px; text-align: left;">Когнитивный</th>
                        <th style="padding: 12px; text-align: left;">Личностный</th>
                    </tr>
                </thead>
                <tbody>
                    ''' + history_rows + '''
                </tbody>
            </table>

            <div style="margin-top: 20px; text-align: center;">
                <a href="/assessment" class="btn"><i class="fas fa-plus"></i> Новая оценка</a>
                <a href="/dynamic_planning" class="btn btn-secondary"><i class="fas fa-route"></i> Построить план</a>
            </div>
        </div>

        <div style="text-align: center;">
            <a href="/" class="back-link"><i class="fas fa-arrow-left"></i> На главную</a>
        </div>
    </div>

    <script>
        // График динамики ЦЗ
        const dates = ''' + dates_json + ''';
        const scores = ''' + scores_json + ''';

        new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Цифровая зрелость (баллы)',
                    data: scores,
                    borderColor: '#3B82F6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#3B82F6',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'Баллы' } },
                           x: { title: { display: true, text: 'Дата' } } }
            }
        });

        // График факторов
        new Chart(document.getElementById('factorsChart'), {
            type: 'bar',
            data: {
                labels: ['Технико-технологический', 'Когнитивный', 'Личностный'],
                datasets: [{
                    data: [''' + f"{latest_assessment['technical_factor']:.1f}" + ''', ''' + f"{latest_assessment['cognitive_factor']:.1f}" + ''', ''' + f"{latest_assessment['personal_factor']:.1f}" + '''],
                    backgroundColor: ['#3B82F6', '#F59E0B', '#10B981'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'Баллы' } } }
            }
        });

        // Динамика факторов
        const technical = ''' + technical_json + ''';
        const cognitive = ''' + cognitive_json + ''';
        const personal = ''' + personal_json + ''';

        new Chart(document.getElementById('factorsTrendChart'), {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    { label: 'Технический фактор', data: technical, borderColor: '#3B82F6', fill: false, tension: 0.3, pointRadius: 3 },
                    { label: 'Когнитивный фактор', data: cognitive, borderColor: '#F59E0B', fill: false, tension: 0.3, pointRadius: 3 },
                    { label: 'Личностный фактор', data: personal, borderColor: '#10B981', fill: false, tension: 0.3, pointRadius: 3 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'Баллы' } } }
            }
        });
    </script>
</body>
</html>'''

        return html