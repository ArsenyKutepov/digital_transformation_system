class AssessmentWizardHandler(BaseHandler):
    """Пошаговый мастер для первой оценки цифровой зрелости"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        session = request.get('session', {})

        if request['method'] == 'GET':
            # Показываем первый шаг мастера
            return self._render_step(template_engine, 1, session)

        elif request['method'] == 'POST':
            post_data = request['post_data']
            step = int(post_data.get('step', 1))
            answers = post_data.get('answers', {})

            # Сохраняем ответы в сессию
            if 'wizard_data' not in session:
                session['wizard_data'] = {}
            session['wizard_data'].update(answers)

            if step < 4:
                return self._render_step(template_engine, step + 1, session)
            else:
                # Завершаем мастер, создаём оценку
                return self._complete_wizard(request, template_engine, session)

    def _render_step(self, template_engine, step: int, session: dict):
        """Рендеринг шага мастера"""
        steps = [
            {
                'title': 'Организация',
                'description': 'Расскажите об организации',
                'fields': [
                    {'name': 'org_name', 'label': 'Название организации', 'type': 'text', 'required': True},
                    {'name': 'org_industry', 'label': 'Отрасль', 'type': 'select',
                     'options': [
                         {'value': 'education', 'label': 'Образование'},
                         {'value': 'it', 'label': 'IT-компания'},
                         {'value': 'manufacturing', 'label': 'Производство'},
                         {'value': 'finance', 'label': 'Финансы'},
                         {'value': 'healthcare', 'label': 'Здравоохранение'},
                         {'value': 'retail', 'label': 'Розничная торговля'},
                         {'value': 'government', 'label': 'Госсектор'}
                     ], 'required': True}
                ]
            },
            {
                'title': 'Технико-технологический блок',
                'description': 'Оцените технологическую инфраструктуру',
                'fields': [
                    {'name': '3.1', 'label': 'Развитость цифровых инструментов управления задачами',
                     'tooltip': '0: бумажные журналы; 1: простые системы; 2: автоматизация; 3: единая среда'},
                    {'name': '3.2', 'label': 'Инициативность исполнителей',
                     'tooltip': '0: не поощряется; 1: допускается; 2: поощряется; 3: культура инноваций'},
                    {'name': '4.3', 'label': 'Степень автоматизации процессов',
                     'tooltip': '0: ручной ввод; 1: частичная; 2: сквозная; 3: роботизация'},
                    {'name': '7.1', 'label': 'Степень систематизации данных',
                     'tooltip': '0: хаотично; 1: структурированы; 2: единое хранилище; 3: Data Lake'},
                    {'name': '8.1', 'label': 'Организация рабочих мест',
                     'tooltip': '0: устаревшее; 1: современное; 2: стандартизировано; 3: BYOD/удалёнка'}
                ]
            },
            {
                'title': 'Когнитивный блок',
                'description': 'Оцените компетенции и навыки персонала',
                'fields': [
                    {'name': '2.1', 'label': 'Уровень развития цифровых компетенций',
                     'tooltip': '0: нет навыков; 1: базовые; 2: уверенное владение; 3: экспертный уровень'},
                    {'name': '2.2', 'label': 'Владение аналитическими инструментами',
                     'tooltip': '0: только Excel; 1: специализированные системы; 2: BI-инструменты; 3: продвинутая аналитика'},
                    {'name': '5.1', 'label': 'Участие в создании цифровых продуктов',
                     'tooltip': '0: не создаются; 1: по запросу; 2: регулярно; 3: инновационная экосистема'},
                    {'name': '6.1', 'label': 'Уровень владения аналитическими методами',
                     'tooltip': '0: не используется; 1: описательная; 2: диагностическая; 3: прогнозная'},
                    {'name': '9.1', 'label': 'Степень цифрового единства',
                     'tooltip': '0: разрозненные; 1: частичная; 2: единое пространство; 3: полная интеграция'}
                ]
            },
            {
                'title': 'Личностный блок',
                'description': 'Оцените цифровую культуру и готовность к изменениям',
                'fields': [
                    {'name': '1.1', 'label': 'Адекватность понимания нравственных аспектов',
                     'tooltip': '0: полное непонимание; 1: базовые знания; 2: системное понимание; 3: проактивная позиция'},
                    {'name': '1.2', 'label': 'Демократичность цифровизации процессов',
                     'tooltip': '0: решения сверху; 1: отдельные консультации; 2: регулярные обсуждения; 3: совместные решения'},
                    {'name': '1.3', 'label': 'Воздействие цифровизации на личностный рост',
                     'tooltip': '0: негативно; 1: нейтрально; 2: положительно; 3: драйвер развития'}
                ]
            }
        ]

        current_step = steps[step - 1]

        # Генерация HTML для полей
        fields_html = ''
        for field in current_step['fields']:
            if field['type'] == 'select':
                options_html = ''
                for opt in field['options']:
                    options_html += f'<option value="{opt["value"]}">{opt["label"]}</option>'
                fields_html += f'''
                <div class="form-group">
                    <label>{field['label']}</label>
                    <select name="{field['name']}" required> {options_html} </select>
                </div>
                '''
            else:
                fields_html += f'''
                <div class="form-group">
                    <label>{field['label']}</label>
                    <input type="number" name="{field['name']}" min="0" max="3" step="1" value="1" required>
                    <small>{field.get('tooltip', '')}</small>
                </div>
                '''

        progress_percent = (step / 4) * 100

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Мастер оценки - Шаг {step} из 4</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .card {{ background: white; border-radius: 24px; padding: 32px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }}
                h1 {{ font-size: 24px; margin-bottom: 8px; color: #0F172A; }}
                .progress {{ height: 8px; background: #E2E8F0; border-radius: 4px; margin: 20px 0; overflow: hidden; }}
                .progress-fill {{ width: {progress_percent}%; height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); }}
                .step-indicator {{ text-align: center; font-size: 14px; color: #64748B; margin-bottom: 20px; }}
                .form-group {{ margin-bottom: 20px; }}
                label {{ display: block; font-weight: 500; margin-bottom: 8px; color: #0F172A; }}
                input, select {{ width: 100%; padding: 12px; border: 1px solid #E2E8F0; border-radius: 12px; font-size: 14px; }}
                small {{ display: block; font-size: 11px; color: #64748B; margin-top: 4px; }}
                .buttons {{ display: flex; justify-content: space-between; margin-top: 30px; }}
                button {{ padding: 12px 24px; border-radius: 40px; font-weight: 500; cursor: pointer; }}
                .btn-next {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; }}
                .btn-prev {{ background: white; border: 1px solid #E2E8F0; color: #64748B; }}
                .scale {{ display: flex; justify-content: space-between; margin-bottom: 20px; padding: 10px; background: #F8FAFC; border-radius: 40px; }}
                .scale-item {{ text-align: center; flex: 1; font-size: 11px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>{current_step['title']}</h1>
                    <p style="color: #64748B;">{current_step['description']}</p>

                    <div class="progress"><div class="progress-fill"></div></div>
                    <div class="step-indicator">Шаг {step} из 4</div>

                    <div class="scale">
                        <div class="scale-item">0<br>Начальный</div>
                        <div class="scale-item">1<br>Автоматизация</div>
                        <div class="scale-item">2<br>Цифровизация</div>
                        <div class="scale-item">3<br>Трансформация</div>
                    </div>

                    <form method="POST">
                        <input type="hidden" name="step" value="{step}">
                        {fields_html}

                        <div class="buttons">
                            {f'<button type="button" class="btn-prev" onclick="history.back()">← Назад</button>' if step > 1 else '<div></div>'}
                            <button type="submit" class="btn-next">{'Завершить' if step == 4 else 'Далее →'}</button>
                        </div>
                    </form>
                </div>
            </div>
        </body>
        </html>
        '''

        return html, 'text/html; charset=utf-8'

    def _complete_wizard(self, request, template_engine, session: dict):
        """Завершение мастера и создание оценки"""
        from core.fuzzy_logic import DigitalMaturityModel
        from database.connection import DatabaseConnection

        wizard_data = session.get('wizard_data', {})

        db = DatabaseConnection()
        org_name = wizard_data.get('org_name', 'Новая организация')
        industry = wizard_data.get('org_industry', 'education')

        org_id = db.execute(
            "INSERT INTO organizations (name, industry, organization_type) VALUES (?, ?, ?)",
            (org_name, industry, 'average')
        )

        scores = {}
        for key, value in wizard_data.items():
            if key not in ['org_name', 'org_industry', 'step']:
                try:
                    scores[key] = int(value)
                except:
                    scores[key] = 1

        all_indicators = [
            '1.1', '1.2', '1.3', '2.1', '2.2', '2.3',
            '3.1', '3.2', '3.3', '4.1', '4.2', '4.3',
            '5.1', '5.2', '5.3', '6.1', '6.2',
            '7.1', '7.2', '7.3', '8.1', '8.2', '8.3',
            '9.1', '9.2'
        ]

        for code in all_indicators:
            if code not in scores:
                scores[code] = 1

        model = DigitalMaturityModel()
        result = model.evaluate(scores)

        # ПОЛУЧАЕМ USER_ID ИЗ СЕССИИ
        user_id = self._get_user_id(request)

        # Если user_id нет, используем значение по умолчанию (admin)
        if user_id is None:
            user_id = 1
            print("[WARNING] user_id not found, using default: 1")

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

        session.pop('wizard_data', None)

        return self.render(template_engine, 'redirect.html', {'url': f'/results/{assessment_id}'})