import re
import os
from typing import Dict, Any


class TemplateEngine:
    """Шаблонизатор с поддержкой переменных, циклов и условий"""

    def __init__(self, template_dir: str):
        self.template_dir = template_dir

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Рендеринг шаблона"""
        filepath = os.path.join(self.template_dir, template_name)

        if not os.path.exists(filepath):
            return f"<h1>Template {template_name} not found</h1>"

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Обрабатываем циклы (самое важное!)
        content = self._process_loops(content, context)

        # Обрабатываем условия
        content = self._process_conditions(content, context)

        # Обрабатываем переменные
        content = self._process_variables(content, context)

        return content

    def _process_variables(self, content: str, context: Dict[str, Any]) -> str:
        """Замена переменных {{ variable }}"""

        def replace_var(match):
            var_path = match.group(1).strip()

            # Получаем значение
            parts = var_path.split('.')
            value = context

            for part in parts:
                if value is None:
                    value = ''
                    break
                elif isinstance(value, dict):
                    value = value.get(part, '')
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    value = ''
                    break

            if value is None:
                return ''

            # Форматирование чисел
            if isinstance(value, float):
                return f"{value:.1f}"
            return str(value)

        # Шаблон для поиска {{ переменная }}
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}'
        content = re.sub(pattern, replace_var, content)

        return content

    def _process_loops(self, content: str, context: Dict[str, Any]) -> str:
        """Обработка циклов {% for item in list %} ... {% endfor %}"""

        # Находим все циклы
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'

        def replace_loop(match):
            item_name = match.group(1)  # например, 'org'
            list_name = match.group(2)  # например, 'organizations'
            inner_html = match.group(3)  # HTML внутри цикла

            # Получаем список из контекста
            items = context.get(list_name, [])

            if not isinstance(items, list):
                items = []

            # Рендерим каждый элемент
            result = []
            for item in items:
                # Создаём временный контекст для этого элемента
                temp_context = context.copy()

                if isinstance(item, dict):
                    # Добавляем все поля словаря
                    for key, val in item.items():
                        temp_context[key] = val
                    # Также добавляем по имени переменной
                    temp_context[item_name] = item
                else:
                    temp_context[item_name] = item

                # Обрабатываем внутренность цикла
                rendered = inner_html
                # Сначала переменные
                rendered = self._process_variables(rendered, temp_context)
                # Потом вложенные циклы
                rendered = self._process_loops(rendered, temp_context)
                # Потом условия
                rendered = self._process_conditions(rendered, temp_context)

                result.append(rendered)

            return ''.join(result)

        # Применяем замену несколько раз для вложенных циклов
        prev_content = None
        while prev_content != content:
            prev_content = content
            content = re.sub(pattern, replace_loop, content, flags=re.DOTALL)

        return content

    def _process_conditions(self, content: str, context: Dict[str, Any]) -> str:
        """Обработка условий {% if variable %} ... {% else %} ... {% endif %}"""

        # Условия с else
        pattern_else = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}'

        def replace_else(match):
            var_name = match.group(1)
            true_block = match.group(2)
            false_block = match.group(3)

            value = context.get(var_name)

            if value:
                # Обрабатываем true блок
                result = true_block
                result = self._process_variables(result, context)
                result = self._process_loops(result, context)
                return result
            else:
                # Обрабатываем false блок
                result = false_block
                result = self._process_variables(result, context)
                result = self._process_loops(result, context)
                return result

        content = re.sub(pattern_else, replace_else, content, flags=re.DOTALL)

        # Условия без else
        pattern_no_else = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'

        def replace_no_else(match):
            var_name = match.group(1)
            block = match.group(2)

            value = context.get(var_name)

            if value:
                result = block
                result = self._process_variables(result, context)
                result = self._process_loops(result, context)
                return result
            return ''

        content = re.sub(pattern_no_else, replace_no_else, content, flags=re.DOTALL)

        return content


# Тестирование
if __name__ == "__main__":
    engine = TemplateEngine('templates')

    test_context = {
        'organizations': [
            {'id': 1, 'name': 'Тестовая организация 1', 'organization_type': 'Гибкая', 'created_at': '2025-01-01'},
            {'id': 2, 'name': 'Тестовая организация 2', 'organization_type': 'Средняя', 'created_at': '2025-01-02'},
        ]
    }

    test_template = """
    <table>
        <tr><th>ID</th><th>Название</th><th>Тип</th></tr>
        {% for org in organizations %}
        <tr>
            <td>{{ org.id }}</td>
            <td>{{ org.name }}</td>
            <td>{{ org.organization_type }}</td>
        </tr>
        {% endfor %}
    </table>
    """

    result = engine._process_loops(test_template, test_context)
    result = engine._process_variables(result, test_context)
    print("Результат теста:")
    print(result)