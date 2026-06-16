import json
from database.connection import DatabaseConnection
from .handlers import BaseHandler


class ActionListAdminHandler(BaseHandler):
    """Управление действиями (администратор)"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_role = self._get_user_role(request)
        if user_role != 'admin':
            return "<h1>Доступ запрещён</h1>", 'text/html; charset=utf-8'

        db = DatabaseConnection()

        if request['method'] == 'GET':
            actions = db.query("SELECT * FROM actions ORDER BY id")

            # Получаем расширенную информацию
            for action in actions:
                extended = db.query_one(
                    "SELECT * FROM actions_extended WHERE action_id = ?",
                    (action['id'],)
                )
                if extended:
                    action['description'] = extended.get('description', '')
                    action['timeframe'] = extended.get('timeframe', '')
                    action['prerequisites'] = json.loads(extended.get('prerequisites', '[]'))
                    action['success_criteria'] = json.loads(extended.get('success_criteria', '[]'))

            html = self._build_actions_html(actions)
            return html, 'text/html; charset=utf-8'

        elif request['method'] == 'POST':
            post_data = request['post_data']
            action = post_data.get('action')

            if action == 'create':
                return self._create_action(post_data, db)
            elif action == 'update':
                return self._update_action(post_data, db)
            elif action == 'delete':
                return self._delete_action(post_data, db)

            return self.render(template_engine, 'redirect.html', {'url': '/admin/actions'})

    def _create_action(self, post_data: dict, db):
        """Создание нового действия"""
        name = post_data.get('name')
        base_growth = float(post_data.get('base_growth', 0.1))
        cost = float(post_data.get('cost', 0.1))
        risk = float(post_data.get('risk', 0.1))
        inertia_shock = float(post_data.get('inertia_shock', 0.15))
        cognitive_load = float(post_data.get('cognitive_load', 0.15))
        description = post_data.get('description', '')
        timeframe = post_data.get('timeframe', '1-2 месяца')
        prerequisites = post_data.get('prerequisites', '').split('\n')
        success_criteria = post_data.get('success_criteria', '').split('\n')

        action_id = db.execute(
            """INSERT INTO actions (name, base_growth, cost, risk, inertia_shock, cognitive_load) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, base_growth, cost, risk, inertia_shock, cognitive_load)
        )

        db.execute(
            """INSERT INTO actions_extended (action_id, description, timeframe, prerequisites, success_criteria) 
               VALUES (?, ?, ?, ?, ?)""",
            (action_id, description, timeframe, json.dumps(prerequisites), json.dumps(success_criteria))
        )

        return self.render(None, 'redirect.html', {'url': '/admin/actions'})

    def _update_action(self, post_data: dict, db):
        """Обновление действия"""
        action_id = int(post_data.get('action_id'))
        name = post_data.get('name')
        base_growth = float(post_data.get('base_growth', 0.1))
        cost = float(post_data.get('cost', 0.1))
        risk = float(post_data.get('risk', 0.1))
        inertia_shock = float(post_data.get('inertia_shock', 0.15))
        cognitive_load = float(post_data.get('cognitive_load', 0.15))

        db.execute(
            """UPDATE actions SET name = ?, base_growth = ?, cost = ?, risk = ?, 
               inertia_shock = ?, cognitive_load = ? WHERE id = ?""",
            (name, base_growth, cost, risk, inertia_shock, cognitive_load, action_id)
        )

        return self.render(None, 'redirect.html', {'url': '/admin/actions'})

    def _delete_action(self, post_data: dict, db):
        """Удаление действия"""
        action_id = int(post_data.get('action_id'))

        db.execute("DELETE FROM actions_extended WHERE action_id = ?", (action_id,))
        db.execute("DELETE FROM actions WHERE id = ?", (action_id,))

        return self.render(None, 'redirect.html', {'url': '/admin/actions'})

    def _build_actions_html(self, actions):
        """Построение HTML страницы управления действиями"""
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
                    <button onclick="editAction({a['id']})" class="btn-edit">✏️</button>
                    <button onclick="deleteAction({a['id']})" class="btn-delete">🗑️</button>
                </td>
            </tr>
            '''

        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Управление действиями</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Segoe UI', sans-serif; background: #F8FAFC; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .card {{ background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; }}
                h1 {{ margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
                th {{ background: #F1F5F9; }}
                .btn {{ padding: 8px 16px; border-radius: 8px; cursor: pointer; margin: 5px; }}
                .btn-create {{ background: #10B981; color: white; border: none; }}
                .btn-edit {{ background: #3B82F6; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; }}
                .btn-delete {{ background: #EF4444; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; }}
                .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }}
                .modal-content {{ background: white; border-radius: 16px; padding: 24px; max-width: 500px; width: 100%; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; font-weight: 500; }}
                input, textarea {{ width: 100%; padding: 8px; border: 1px solid #E2E8F0; border-radius: 8px; }}
                .modal-buttons {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>Управление действиями</h1>
                    <button class="btn btn-create" onclick="openCreateModal()">+ Создать действие</button>

                    <table>
                        <thead>
                            <tr><th>ID</th><th>Название</th><th>Рост</th><th>Затраты</th><th>Риск</th><th>Действия</th></tr>
                        </thead>
                        <tbody>
                            {actions_table}
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="modal" class="modal">
                <div class="modal-content">
                    <h2 id="modalTitle">Создание действия</h2>
                    <form id="actionForm" method="POST">
                        <input type="hidden" name="action" id="formAction">
                        <input type="hidden" name="action_id" id="actionId">

                        <div class="form-group">
                            <label>Название</label>
                            <input type="text" name="name" id="actionName" required>
                        </div>
                        <div class="form-group">
                            <label>Базовый рост (%)</label>
                            <input type="number" step="0.01" name="base_growth" id="actionBaseGrowth" value="0.1">
                        </div>
                        <div class="form-group">
                            <label>Затраты (%)</label>
                            <input type="number" step="0.01" name="cost" id="actionCost" value="0.1">
                        </div>
                        <div class="form-group">
                            <label>Риск (%)</label>
                            <input type="number" step="0.01" name="risk" id="actionRisk" value="0.1">
                        </div>
                        <div class="form-group">
                            <label>Инерционный шок</label>
                            <input type="number" step="0.01" name="inertia_shock" id="actionInertia" value="0.15">
                        </div>
                        <div class="form-group">
                            <label>Когнитивная нагрузка</label>
                            <input type="number" step="0.01" name="cognitive_load" id="actionCognitive" value="0.15">
                        </div>
                        <div class="form-group">
                            <label>Описание</label>
                            <textarea name="description" id="actionDescription" rows="3"></textarea>
                        </div>
                        <div class="form-group">
                            <label>Срок реализации</label>
                            <input type="text" name="timeframe" id="actionTimeframe" value="1-2 месяца">
                        </div>

                        <div class="modal-buttons">
                            <button type="button" onclick="closeModal()">Отмена</button>
                            <button type="submit" class="btn-create">Сохранить</button>
                        </div>
                    </form>
                </div>
            </div>

            <script>
                function openCreateModal() {{
                    document.getElementById('modalTitle').innerText = 'Создание действия';
                    document.getElementById('formAction').value = 'create';
                    document.getElementById('actionId').value = '';
                    document.getElementById('actionName').value = '';
                    document.getElementById('actionBaseGrowth').value = '0.1';
                    document.getElementById('actionCost').value = '0.1';
                    document.getElementById('actionRisk').value = '0.1';
                    document.getElementById('actionInertia').value = '0.15';
                    document.getElementById('actionCognitive').value = '0.15';
                    document.getElementById('actionDescription').value = '';
                    document.getElementById('actionTimeframe').value = '1-2 месяца';
                    document.getElementById('modal').style.display = 'flex';
                }}

                function editAction(id) {{
                    fetch(`/api/v1/actions?action_id=${{id}}`)
                        .then(res => res.json())
                        .then(data => {{
                            document.getElementById('modalTitle').innerText = 'Редактирование действия';
                            document.getElementById('formAction').value = 'update';
                            document.getElementById('actionId').value = data.id;
                            document.getElementById('actionName').value = data.name;
                            document.getElementById('actionBaseGrowth').value = data.base_growth;
                            document.getElementById('actionCost').value = data.cost;
                            document.getElementById('actionRisk').value = data.risk;
                            document.getElementById('actionInertia').value = data.inertia_shock;
                            document.getElementById('actionCognitive').value = data.cognitive_load;
                            document.getElementById('actionDescription').value = data.description || '';
                            document.getElementById('actionTimeframe').value = data.timeframe || '1-2 месяца';
                            document.getElementById('modal').style.display = 'flex';
                        }});
                }}

                function deleteAction(id) {{
                    if (confirm('Удалить действие?')) {{
                        const form = document.createElement('form');
                        form.method = 'POST';
                        form.innerHTML = `<input type="hidden" name="action" value="delete"><input type="hidden" name="action_id" value="${{id}}">`;
                        document.body.appendChild(form);
                        form.submit();
                    }}
                }}

                function closeModal() {{
                    document.getElementById('modal').style.display = 'none';
                }}
            </script>
        </body>
        </html>
        '''

        return html
