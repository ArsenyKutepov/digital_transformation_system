import socket
import threading
import os
import json
from urllib.parse import urlparse, parse_qs
from typing import Dict

from .router import Router
from .templates import TemplateEngine
from .handlers import (
    IndexHandler, AssessmentHandler, ResultsHandler,
    PlanningHandler, CompareHandler
)
from .auth_handlers import LoginHandler, RegisterHandler, LogoutHandler, ProfileHandler
from .sprint_handlers import (
    SprintListHandler, SprintStartHandler, SprintCompleteHandler,
    SprintViewHandler, PlanRescheduleHandler
)
from .notification_handlers import (
    NotificationListHandler, NotificationReadHandler,
    NotificationReadAllHandler, NotificationDeleteHandler
)
from .analytics_handlers import AnalyticsDashboardHandler, WeakBlocksHandler
from .export_handlers import (
    ExportExcelHandler, ExportJsonHandler, ExportCsvHandler, DashboardHtmlHandler
)
from .admin_handlers import AdminDashboardHandler, AdminActionsHandler, SchedulerAdminHandler
from api.rest_api import RESTAPIHandler
from config import HOST, PORT, STATIC_DIR, TEMPLATE_DIR


class StaticHandler:
    def handle(self, request, template_engine, params=None):
        filename = params.get('file', '') if params else ''
        filepath = os.path.join(STATIC_DIR, filename)

        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            if filename.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif filename.endswith('.js'):
                content_type = 'application/javascript; charset=utf-8'
            else:
                content_type = 'text/plain'
            return content, content_type

        return b'Not Found', 'text/plain'


class TestHandler:
    def handle(self, request, template_engine, params=None):
        html = "<h1>Server is running!</h1>"
        return html, 'text/html; charset=utf-8'


class HTTPServer:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.router = Router()
        self.template_engine = TemplateEngine(TEMPLATE_DIR)
        self._setup_routes()

    def _setup_routes(self):
        # Публичные
        self.router.add_route('GET', '/login', LoginHandler)
        self.router.add_route('POST', '/login', LoginHandler)
        self.router.add_route('GET', '/register', RegisterHandler)
        self.router.add_route('POST', '/register', RegisterHandler)
        self.router.add_route('GET', '/logout', LogoutHandler)
        self.router.add_route('GET', '/test', TestHandler)
        self.router.add_route('GET', '/static/{file}', StaticHandler)

        # Защищённые
        self.router.add_route('GET', '/', IndexHandler)
        self.router.add_route('GET', '/assessment', AssessmentHandler)
        self.router.add_route('POST', '/assessment/submit', AssessmentHandler)
        self.router.add_route('GET', '/results/{id}', ResultsHandler)
        self.router.add_route('GET', '/dynamic_planning', PlanningHandler)
        self.router.add_route('POST', '/dynamic_planning/run', PlanningHandler)
        self.router.add_route('GET', '/compare/{org_id}', CompareHandler)
        self.router.add_route('GET', '/profile', ProfileHandler)
        self.router.add_route('POST', '/profile', ProfileHandler)

        # Спринты
        self.router.add_route('GET', '/sprints/{plan_id}/list', SprintListHandler)
        self.router.add_route('GET', '/sprints/{sprint_id}/start', SprintStartHandler)
        self.router.add_route('GET', '/sprints/{sprint_id}/complete', SprintCompleteHandler)
        self.router.add_route('POST', '/sprints/{sprint_id}/complete', SprintCompleteHandler)
        self.router.add_route('GET', '/sprints/{sprint_id}/view', SprintViewHandler)
        self.router.add_route('GET', '/plan/reschedule/{plan_id}', PlanRescheduleHandler)
        self.router.add_route('POST', '/plan/reschedule/{plan_id}', PlanRescheduleHandler)

        # Уведомления
        self.router.add_route('GET', '/notifications', NotificationListHandler)
        self.router.add_route('GET', '/notifications/{id}/read', NotificationReadHandler)
        self.router.add_route('GET', '/notifications/read-all', NotificationReadAllHandler)
        self.router.add_route('GET', '/notifications/{id}/delete', NotificationDeleteHandler)

        # Аналитика
        self.router.add_route('GET', '/analytics/{org_id}', AnalyticsDashboardHandler)
        self.router.add_route('GET', '/analytics/{org_id}/weak-blocks', WeakBlocksHandler)

        # Экспорт
        self.router.add_route('GET', '/export/excel/{org_id}', ExportExcelHandler)
        self.router.add_route('GET', '/export/json/{org_id}', ExportJsonHandler)
        self.router.add_route('GET', '/export/csv/{org_id}', ExportCsvHandler)
        self.router.add_route('GET', '/dashboard/{org_id}', DashboardHtmlHandler)

        # Администрирование
        self.router.add_route('GET', '/admin', AdminDashboardHandler)
        self.router.add_route('GET', '/admin/actions', AdminActionsHandler)
        self.router.add_route('POST', '/admin/actions', AdminActionsHandler)
        self.router.add_route('GET', '/admin/scheduler', SchedulerAdminHandler)
        self.router.add_route('POST', '/admin/scheduler', SchedulerAdminHandler)

        # API
        self.router.add_route('GET', '/api/v1/maturity', RESTAPIHandler)
        self.router.add_route('POST', '/api/v1/assessments', RESTAPIHandler)
        self.router.add_route('GET', '/api/v1/plan/{org_id}', RESTAPIHandler)
        self.router.add_route('POST', '/api/v1/sprints/{sprint_id}', RESTAPIHandler)
        self.router.add_route('GET', '/api/v1/organizations', RESTAPIHandler)
        self.router.add_route('GET', '/api/v1/analytics/{org_id}', RESTAPIHandler)
        self.router.add_route('GET', '/api/v1/actions', RESTAPIHandler)

    def _parse_request(self, data: bytes) -> Dict:
        try:
            request_line = data.split(b'\r\n')[0].decode('utf-8', errors='replace')
        except:
            request_line = ''
        parts = request_line.split(' ')
        if len(parts) < 2:
            return None
        method = parts[0]
        path = parts[1]
        parsed_url = urlparse(path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        headers = {}
        body = ''
        header_end = data.find(b'\r\n\r\n')
        if header_end != -1:
            header_data = data[:header_end].decode('utf-8', errors='replace')
            body = data[header_end + 4:].decode('utf-8', errors='replace')
            lines = header_data.split('\r\n')
            for line in lines[1:]:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key] = value
        post_data = {}
        if method == 'POST' and body:
            content_type = headers.get('Content-Type', '')
            if 'application/x-www-form-urlencoded' in content_type:
                post_data = parse_qs(body)
                post_data = {k: v[0] if len(v) == 1 else v for k, v in post_data.items()}
            elif 'application/json' in content_type:
                try:
                    post_data = json.loads(body)
                except:
                    post_data = {}
        return {'method': method, 'path': path, 'query_params': query_params, 'post_data': post_data,
                'headers': headers}

    def _parse_cookies(self, cookie_header: str) -> dict:
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key] = value
        return cookies

    def _add_session_to_request(self, request: dict):
        """Добавление информации о сессии в request"""
        cookies = self._parse_cookies(request.get('headers', {}).get('Cookie', ''))
        session_token = cookies.get('session_token')

        request['cookies'] = cookies
        request['session'] = {'valid': False, 'user_id': None, 'role': None, 'username': None}

        if session_token:
            from database.user_model import UserManager
            um = UserManager()
            valid_session = um.validate_session(session_token)
            if valid_session['valid']:
                request['session'] = {
                    'valid': True,
                    'user_id': valid_session['user_id'],
                    'username': valid_session['username'],
                    'role': valid_session['role'],
                    'full_name': valid_session.get('full_name'),
                    'token': session_token
                }

    def _is_protected_route(self, path: str) -> bool:
        public_routes = ['/login', '/register', '/test', '/static', '/logout']
        for route in public_routes:
            if path.startswith(route):
                return False
        if path.startswith('/api/'):
            return False
        return True

    def _http_response(self, status_code: int, content_type: str, content: bytes) -> bytes:
        status_codes = {200: 'OK', 302: 'Found', 404: 'Not Found', 500: 'Internal Server Error', 403: 'Forbidden',
                        401: 'Unauthorized'}
        response_line = f"HTTP/1.1 {status_code} {status_codes.get(status_code, 'Unknown')}\r\n"
        headers = f"Content-Type: {content_type}\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n"
        return response_line.encode() + headers.encode() + content

    def _redirect(self, location: str) -> bytes:
        return f"HTTP/1.1 302 Found\r\nLocation: {location}\r\nContent-Length: 0\r\n\r\n".encode()

    def _safe_send(self, client_socket: socket.socket, data: bytes):
        try:
            client_socket.send(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            pass

    def _handle_api_request(self, request: dict) -> bytes:
        api_handler = RESTAPIHandler()
        api_request = {
            'method': request['method'],
            'path': request['path'],
            'headers': request['headers'],
            'body': request['post_data'] if request['method'] == 'POST' else request['query_params']
        }
        result = api_handler.handle_request(api_request)
        if isinstance(result, dict):
            response_json = json.dumps(result, ensure_ascii=False)
            return self._http_response(result.get('status', 200), 'application/json; charset=utf-8',
                                       response_json.encode())
        elif isinstance(result, tuple) and len(result) == 2:
            content, content_type = result
            if isinstance(content, str):
                content = content.encode('utf-8')
            return self._http_response(200, content_type, content)
        error_json = json.dumps({'error': 'Internal Server Error', 'status': 500})
        return self._http_response(500, 'application/json; charset=utf-8', error_json.encode())

    def _handle_client(self, client_socket: socket.socket):
        try:
            client_socket.settimeout(30)
            data = client_socket.recv(8192)
            if not data:
                client_socket.close()
                return
            request = self._parse_request(data)
            if not request:
                client_socket.close()
                return
            self._add_session_to_request(request)
            path = request['path']
            if path.startswith('/api/'):
                response = self._handle_api_request(request)
                self._safe_send(client_socket, response)
                client_socket.close()
                return
            if self._is_protected_route(path) and not request['session']['valid']:
                self._safe_send(client_socket, self._redirect('/login'))
                client_socket.close()
                return
            handler_class, params = self.router.match(request['method'], path)
            if handler_class:
                handler_instance = handler_class()
                response = handler_instance.handle(request, self.template_engine, params)
                if isinstance(response, tuple):
                    content, content_type = response
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    self._safe_send(client_socket, self._http_response(200, content_type, content))
                elif isinstance(response, bytes):
                    self._safe_send(client_socket, response)
                else:
                    self._safe_send(client_socket, self._http_response(200, 'text/html', str(response).encode()))
            else:
                self._safe_send(client_socket, self._http_response(404, 'text/plain', b'Not Found'))

        except Exception as e:
            print(f"Error: {e}")
            try:
                self._safe_send(client_socket, self._http_response(500, 'text/plain', str(e).encode()))
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass

    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"[OK] Server started at http://{self.host}:{self.port}")
        print("[INFO] Press Ctrl+C to stop")
        print("[INFO] Demo access: admin / admin123\n")
        try:
            while True:
                client_socket, addr = server_socket.accept()
                thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\n[INFO] Server stopped")
        finally:
            server_socket.close()