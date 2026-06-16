from database.connection import DatabaseConnection


class ActionDependencies:
    """Управление зависимостями между действиями"""

    def __init__(self):
        self.db = DatabaseConnection()

    def add_dependency(self, action_id: int, depends_on_action_id: int,
                       dependency_type: str = 'required') -> bool:
        """Добавление зависимости между действиями"""
        if self._would_create_cycle(action_id, depends_on_action_id):
            return False

        self.db.execute(
            """INSERT INTO action_dependencies (action_id, depends_on_action_id, dependency_type) 
               VALUES (?, ?, ?)""",
            (action_id, depends_on_action_id, dependency_type)
        )
        return True

    def _would_create_cycle(self, action_id: int, depends_on_action_id: int) -> bool:
        """Проверка на циклическую зависимость"""
        visited = set()
        to_check = [depends_on_action_id]

        while to_check:
            current = to_check.pop()
            if current == action_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            deps = self.db.query(
                "SELECT depends_on_action_id FROM action_dependencies WHERE action_id = ?",
                (current,)
            )
            for d in deps:
                to_check.append(d['depends_on_action_id'])

        return False

    def get_dependencies(self, action_id: int) -> list:
        """Получение списка действий, от которых зависит данное"""
        query = """
            SELECT a.id, a.name, ad.dependency_type 
            FROM action_dependencies ad
            JOIN actions a ON ad.depends_on_action_id = a.id
            WHERE ad.action_id = ?
        """
        deps = self.db.query(query, (action_id,))
        return deps

    def get_dependents(self, action_id: int) -> list:
        """Получение списка действий, которые зависят от данного"""
        query = """
            SELECT a.id, a.name, ad.dependency_type 
            FROM action_dependencies ad
            JOIN actions a ON ad.action_id = a.id
            WHERE ad.depends_on_action_id = ?
        """
        deps = self.db.query(query, (action_id,))
        return deps

    def validate_plan_sequence(self, plan_actions: list) -> dict:
        """Проверка последовательности действий на соблюдение зависимостей"""
        completed = set()
        violations = []

        for action in plan_actions:
            action_id = action.get('action_id', action.get('id'))
            deps = self.get_dependencies(action_id)

            for dep in deps:
                if dep['id'] not in completed:
                    violations.append({
                        'action': action.get('name', f'Action_{action_id}'),
                        'depends_on': dep['name'],
                        'type': dep['dependency_type']
                    })

            completed.add(action_id)

        return {
            'is_valid': len(violations) == 0,
            'violations': violations
        }

    def get_optimal_order(self, action_ids: list) -> list:
        """Топологическая сортировка действий с учётом зависимостей"""
        graph = {aid: [] for aid in action_ids}
        in_degree = {aid: 0 for aid in action_ids}

        for aid in action_ids:
            deps = self.get_dependencies(aid)
            for dep in deps:
                if dep['id'] in graph:
                    graph[dep['id']].append(aid)
                    in_degree[aid] += 1

        queue = [aid for aid in action_ids if in_degree[aid] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(action_ids):
            return []

        actions = []
        for aid in result:
            action = self.db.query_one("SELECT name FROM actions WHERE id = ?", (aid,))
            if action:
                actions.append({
                    'id': aid,
                    'name': action['name']
                })

        return actions