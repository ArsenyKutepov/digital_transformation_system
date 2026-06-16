from database.user_model import UserManager


class SessionMiddleware:
    """Middleware для проверки сессии и добавления информации о пользователе в request"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.um = UserManager()

    def __call__(self, request):
        # Извлекаем session_token из cookie
        cookies = self._parse_cookies(request.get('headers', {}).get('Cookie', ''))
        session_token = cookies.get('session_token')

        request['cookies'] = cookies
        request['session'] = {'valid': False, 'user_id': None, 'role': None}

        if session_token:
            valid_session = self.um.validate_session(session_token)
            if valid_session['valid']:
                request['session'] = {
                    'valid': True,
                    'user_id': valid_session['user_id'],
                    'username': valid_session['username'],
                    'role': valid_session['role'],
                    'full_name': valid_session.get('full_name'),
                    'token': session_token
                }

        return self.get_response(request)

    def _parse_cookies(self, cookie_header: str) -> dict:
        """Парсинг Cookie заголовка"""
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key] = value
        return cookies


def require_auth(func):
    """Декоратор для защиты маршрутов, требующих аутентификации"""

    def wrapper(self, request, *args, **kwargs):
        if not request.get('session', {}).get('valid'):
            # Перенаправление на страницу входа
            return b"HTTP/1.1 302 Found\r\nLocation: /login\r\n\r\n"
        return func(self, request, *args, **kwargs)

    return wrapper


def require_role(role):
    """Декоратор для проверки роли пользователя"""

    def decorator(func):
        def wrapper(self, request, *args, **kwargs):
            user_role = request.get('session', {}).get('role')
            if not user_role:
                return b"HTTP/1.1 302 Found\r\nLocation: /login\r\n\r\n"
            if user_role != role and user_role != 'admin':
                # Возвращаем HTML строку вместо bytes с русским текстом
                html = '<h1>Access Denied</h1><p>You do not have permission to view this page.</p>'
                response = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\n\r\n{html}"
                return response.encode('utf-8')
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator