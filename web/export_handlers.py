import os
from datetime import datetime
from database.connection import DatabaseConnection
from export.report_generator import ReportGenerator
from .handlers import BaseHandler


class ExportExcelHandler(BaseHandler):
    """Экспорт отчёта в Excel"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return self.render(template_engine, 'error.html', {'message': 'ID организации не указан'})

        # Создаём директорию для отчётов
        reports_dir = 'reports'
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        filename = f"report_org_{org_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(reports_dir, filename)

        report_gen = ReportGenerator()
        result = report_gen.export_to_excel(int(org_id), filepath)

        if result:
            # Логируем экспорт
            db = DatabaseConnection()
            user_id = self._get_user_id(request)
            db.execute(
                "INSERT INTO export_logs (user_id, export_type, format, entity_id, file_path) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'assessment', 'excel', org_id, filepath)
            )

            # Отдаём файл
            with open(filepath, 'rb') as f:
                content = f.read()

            return content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            return self.render(template_engine, 'error.html',
                               {'message': 'Не удалось создать Excel-отчёт. Установите openpyxl.'})


class ExportJsonHandler(BaseHandler):
    """Экспорт отчёта в JSON"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return self.render(template_engine, 'error.html', {'message': 'ID организации не указан'})

        report_gen = ReportGenerator()
        json_data = report_gen.export_to_json(int(org_id))

        # Логируем экспорт
        db = DatabaseConnection()
        user_id = self._get_user_id(request)
        db.execute(
            "INSERT INTO export_logs (user_id, export_type, format, entity_id) VALUES (?, ?, ?, ?)",
            (user_id, 'assessment', 'json', org_id)
        )

        return json_data, 'application/json; charset=utf-8'


class ExportCsvHandler(BaseHandler):
    """Экспорт отчёта в CSV"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return self.render(template_engine, 'error.html', {'message': 'ID организации не указан'})

        reports_dir = 'reports'
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        filename = f"report_org_{org_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(reports_dir, filename)

        report_gen = ReportGenerator()
        result = report_gen.export_to_csv(int(org_id), filepath)

        if result:
            db = DatabaseConnection()
            user_id = self._get_user_id(request)
            db.execute(
                "INSERT INTO export_logs (user_id, export_type, format, entity_id, file_path) VALUES (?, ?, ?, ?, ?)",
                (user_id, 'assessment', 'csv', org_id, filepath)
            )

            with open(filepath, 'rb') as f:
                content = f.read()

            return content, 'text/csv'
        else:
            return self.render(template_engine, 'error.html', {'message': 'Не удалось создать CSV-отчёт'})


class DashboardHtmlHandler(BaseHandler):
    """Генерация HTML-дашборда"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        org_id = params.get('org_id') if params else None
        if not org_id:
            return self.render(template_engine, 'error.html', {'message': 'ID организации не указан'})

        report_gen = ReportGenerator()
        html = report_gen.generate_dashboard_html(int(org_id))

        return html, 'text/html; charset=utf-8'