import json
from database.connection import DatabaseConnection
from database.models import Organization, Assessment
from .handlers import BaseHandler


class AnalyticsDashboardHandler(BaseHandler):
    """Дашборд с расширенной аналитикой (прямая генерация HTML)"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return "<h1>ID организации не указан</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()

        org = Organization.get_by_id(int(org_id))
        if not org:
            return "<h1>Организация не найдена</h1>", 'text/html; charset=utf-8'

        assessments = Assessment.get_by_org(int(org_id))

        if not assessments:
            html = self._build_empty_html(org)
            return html, 'text/html; charset=utf-8'

        latest = assessments[0]

        details = db.query(
            "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
            (latest['id'],)
        )
        scores = {d['indicator_code']: d['value'] for d in details}

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
            1: 'Личностный', 2: 'Компетенции', 3: 'Организационная культура',
            4: 'Процессы', 5: 'Продукты', 6: 'Модели',
            7: 'Данные', 8: 'Инфраструктура', 9: 'Глобальная среда'
        }

        block_values = {i: [] for i in range(1, 10)}
        for code, value in scores.items():
            block_id = block_map.get(code, 1)
            block_values[block_id].append(value)

        block_scores = {}
        weak_blocks = []
        strong_blocks = []
        for block_id in range(1, 10):
            if block_values[block_id]:
                avg = sum(block_values[block_id]) / len(block_values[block_id])
                block_scores[block_id] = avg
                if avg <= 1.0:
                    weak_blocks.append({'id': block_id, 'name': block_names[block_id], 'score': avg})
                elif avg >= 2.5:
                    strong_blocks.append({'id': block_id, 'name': block_names[block_id], 'score': avg})
            else:
                block_scores[block_id] = 0

        recommendations = []
        recs_map = {
            1: 'Проведите опрос сотрудников о цифровой культуре',
            2: 'Запустите программу повышения цифровой грамотности',
            3: 'Внедрите цифровые инструменты управления задачами',
            4: 'Автоматизируйте ключевые процессы',
            5: 'Создайте продуктовую команду',
            6: 'Развивайте аналитические компетенции',
            7: 'Создайте единое хранилище данных',
            8: 'Модернизируйте IT-инфраструктуру',
            9: 'Развивайте партнёрства с EdTech'
        }
        for wb in weak_blocks:
            recommendations.append(recs_map.get(wb['id'], 'Развивайте этот блок'))

        dates = []
        scores_history = []
        technical_history = []
        cognitive_history = []
        personal_history = []

        for a in reversed(assessments):
            dates.append(a['assessment_date'][:10])
            scores_history.append(a['final_score'])
            technical_history.append(a['technical_factor'])
            cognitive_history.append(a['cognitive_factor'])
            personal_history.append(a['personal_factor'])

        html = self._build_analytics_html(
            org, assessments, latest, block_scores, block_names,
            weak_blocks, strong_blocks, recommendations,
            dates, scores_history, technical_history, cognitive_history, personal_history
        )

        return html, 'text/html; charset=utf-8'

    def _build_empty_html(self, org):
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Аналитика - {org['name']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }}
        .container {{ max-width: 800px; margin: -20px auto 0; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 40px; text-align: center; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #3B82F6; color: white; text-decoration: none; border-radius: 10px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Аналитика организации</h1>
        <p>{org['name']}</p>
    </div>
    <div class="container">
        <div class="card">
            <h2>Нет данных</h2>
            <p>Для этой организации пока нет выполненных оценок цифровой зрелости.</p>
            <a href="/assessment" class="btn">Создать оценку</a>
        </div>
    </div>
</body>
</html>'''

    def _build_analytics_html(self, org, assessments, latest, block_scores, block_names,
                              weak_blocks, strong_blocks, recommendations,
                              dates, scores_history, technical_history, cognitive_history, personal_history):

        current_score = f"{latest['final_score']:.1f}" if latest else "0"
        assessments_count = len(assessments)
        weak_count = len(weak_blocks)
        strong_count = len(strong_blocks)

        blocks_html = ''
        for block_id in range(1, 10):
            score = block_scores.get(block_id, 0)
            percent = (score / 3) * 100
            color = '#EF4444' if score <= 1 else '#F59E0B' if score <= 2 else '#10B981'
            status = 'Требует внимания' if score <= 1 else 'Средний уровень' if score <= 2 else 'Хороший уровень'
            blocks_html += f'''
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{block_names[block_id]}</span>
                    <span>{score:.1f}/3.0</span>
                </div>
                <div style="height: 8px; background: #E2E8F0; border-radius: 4px;">
                    <div style="width: {percent:.0f}%; height: 100%; background: {color}; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 11px; color: #64748B;">{status}</div>
            </div>
            '''

        weak_html = ''
        for w in weak_blocks:
            weak_html += f'<div style="background: #FEE2E2; padding: 10px; border-radius: 8px; margin-bottom: 8px;"><strong>{w["name"]}</strong> (оценка: {w["score"]:.1f}/3.0)</div>'
        if not weak_html:
            weak_html = '<div style="color: #10B981;">✅ Слабых блоков не обнаружено</div>'

        strong_html = ''
        for s in strong_blocks:
            strong_html += f'<div style="background: #D1FAE5; padding: 10px; border-radius: 8px; margin-bottom: 8px;"><strong>{s["name"]}</strong> (оценка: {s["score"]:.1f}/3.0)</div>'
        if not strong_html:
            strong_html = '<div style="color: #64748B;">Пока нет блоков с высокими оценками</div>'

        rec_html = ''
        for r in recommendations[:5]:
            rec_html += f'<div style="background: #EFF6FF; padding: 10px; border-radius: 8px; margin-bottom: 8px;">💡 {r}</div>'

        history_rows = ''
        for a in assessments:
            date_str = str(a['assessment_date'])[:19] if a['assessment_date'] else ''
            history_rows += f'''
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px;">{date_str}</td>
                <td style="padding: 8px;"><strong>{a['final_score']:.1f}</strong></td>
                <td style="padding: 8px;">{a['technical_factor']:.1f}</td>
                <td style="padding: 8px;">{a['cognitive_factor']:.1f}</td>
                <td style="padding: 8px;">{a['personal_factor']:.1f}</td>
            <tr>
            '''

        dates_json = json.dumps(dates)
        scores_json = json.dumps(scores_history)
        technical_json = json.dumps(technical_history)
        cognitive_json = json.dumps(cognitive_history)
        personal_json = json.dumps(personal_history)

        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Аналитика - {org['name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); color: white; padding: 30px; text-align: center; }}
        .container {{ max-width: 1200px; margin: -20px auto 0; padding: 20px; }}
        .card {{ background: white; border-radius: 20px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        h2 {{ margin-bottom: 20px; border-left: 4px solid #3B82F6; padding-left: 15px; color: #0F172A; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; border-radius: 12px; padding: 15px; text-align: center; border: 1px solid #E2E8F0; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #3B82F6; }}
        .stat-label {{ font-size: 12px; color: #64748B; margin-top: 5px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .btn-back {{ display: inline-block; margin-top: 20px; color: #64748B; text-decoration: none; }}
        .chart-container {{ height: 300px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Аналитика организации</h1>
        <p>{org['name']} | Тип: {org.get('organization_type', 'average')}</p>
    </div>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{current_score}</div><div class="stat-label">Текущий уровень ЦЗ</div></div>
            <div class="stat-card"><div class="stat-number">{assessments_count}</div><div class="stat-label">Выполнено оценок</div></div>
            <div class="stat-card"><div class="stat-number">{weak_count}</div><div class="stat-label">Слабых блоков</div></div>
            <div class="stat-card"><div class="stat-number">{strong_count}</div><div class="stat-label">Сильных блоков</div></div>
        </div>

        <div class="card">
            <h2>📈 Динамика цифровой зрелости</h2>
            <div class="chart-container"><canvas id="trendChart"></canvas></div>
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>🎯 Факторы ЦЗ</h2>
                <div class="chart-container"><canvas id="factorsChart"></canvas></div>
            </div>
            <div class="card">
                <h2>📊 Динамика факторов</h2>
                <div class="chart-container"><canvas id="factorsTrendChart"></canvas></div>
            </div>
        </div>

        <div class="card">
            <h2>📋 Оценка по блокам</h2>
            {blocks_html}
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>⚠️ Сильные и слабые стороны</h2>
                <h3>🔴 Требуют внимания</h3>
                {weak_html}
                <h3 style="margin-top: 15px;">🟢 Сильные стороны</h3>
                {strong_html}
            </div>
            <div class="card">
                <h2>💡 Рекомендации</h2>
                {rec_html}
            </div>
        </div>

        <div class="card">
            <h2>📜 История оценок</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #F1F5F9;">
                        <th style="padding: 10px;">Дата</th><th>Итоговый балл</th><th>Технический</th><th>Когнитивный</th><th>Личностный</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
        </div>

        <a href="/" class="btn-back">← На главную</a>
    </div>

    <script>
        const dates = {dates_json};
        const scores = {scores_json};
        const technical = {technical_json};
        const cognitive = {cognitive_json};
        const personal = {personal_json};

        if (dates.length > 0) {{
            new Chart(document.getElementById('trendChart'), {{
                type: 'line',
                data: {{ labels: dates, datasets: [{{ label: 'Цифровая зрелость (баллы)', data: scores, borderColor: '#3B82F6', fill: true }}] }}
            }});

            if (technical.length > 0) {{
                const last = technical.length - 1;
                new Chart(document.getElementById('factorsChart'), {{
                    type: 'bar',
                    data: {{ labels: ['Технический', 'Когнитивный', 'Личностный'], datasets: [{{ data: [technical[last], cognitive[last], personal[last]], backgroundColor: ['#3B82F6', '#F59E0B', '#10B981'] }}] }}
                }});
            }}

            new Chart(document.getElementById('factorsTrendChart'), {{
                type: 'line',
                data: {{ labels: dates, datasets: [
                    {{ label: 'Технический', data: technical, borderColor: '#3B82F6' }},
                    {{ label: 'Когнитивный', data: cognitive, borderColor: '#F59E0B' }},
                    {{ label: 'Личностный', data: personal, borderColor: '#10B981' }}
                ] }}
            }});
        }}
    </script>
</body>
</html>'''

        return html


class WeakBlocksHandler(BaseHandler):
    """Анализ слабых блоков организации"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return "<h1>ID организации не указан</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()

        org = Organization.get_by_id(int(org_id))
        if not org:
            return "<h1>Организация не найдена</h1>", 'text/html; charset=utf-8'

        assessment = db.query_one(
            "SELECT * FROM assessments WHERE org_id = ? ORDER BY assessment_date DESC LIMIT 1",
            (org_id,)
        )

        if not assessment:
            return self.render(template_engine, 'error.html', {'message': 'Нет оценок для организации'})

        details = db.query(
            "SELECT indicator_code, value FROM assessment_details WHERE assessment_id = ?",
            (assessment['id'],)
        )

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

        block_values = {i: [] for i in range(1, 10)}
        for d in details:
            block_id = block_map.get(d['indicator_code'], 1)
            block_values[block_id].append(d['value'])

        block_analysis = []
        weak_blocks = []
        for block_id in range(1, 10):
            if block_values[block_id]:
                avg = sum(block_values[block_id]) / len(block_values[block_id])
                is_weak = avg <= 1.0
                if is_weak:
                    weak_blocks.append(block_id)
                block_analysis.append({
                    'id': block_id,
                    'name': block_names[block_id],
                    'avg': avg,
                    'is_weak': is_weak,
                    'scores': block_values[block_id]
                })
            else:
                block_analysis.append({
                    'id': block_id,
                    'name': block_names[block_id],
                    'avg': 0,
                    'is_weak': True,
                    'scores': []
                })

        return self.render(template_engine, 'weak_blocks.html', {
            'org': org,
            'org_id': org_id,
            'block_analysis': block_analysis,
            'weak_blocks': weak_blocks,
            'user': request['session']
        })