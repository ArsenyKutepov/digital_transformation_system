import re


class Router:
    """Маршрутизатор"""

    def __init__(self):
        self.routes = []

    def add_route(self, method: str, path: str, handler_class):
        """
        Добавление маршрута - сохраняем класс обработчика
        """
        pattern = path
        param_names = []

        for match in re.finditer(r'{([^}]+)}', path):
            param_names.append(match.group(1))
            pattern = pattern.replace(match.group(0), r'([^/]+)')

        pattern = '^' + pattern + '$'

        self.routes.append({
            'method': method,
            'pattern': re.compile(pattern),
            'param_names': param_names,
            'handler_class': handler_class
        })

    def match(self, method: str, path: str):
        """Поиск маршрута - возвращаем класс и параметры"""
        for route in self.routes:
            if route['method'] != method:
                continue

            match = route['pattern'].match(path)
            if match:
                params = {}
                for i, name in enumerate(route['param_names']):
                    params[name] = match.group(i + 1)
                return route['handler_class'], params

        return None, None