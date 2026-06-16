from database.user_model import UserManager
from .handlers import BaseHandler


class LoginHandler(BaseHandler):
    """Обработчик входа в систему"""

    def handle(self, request, template_engine, params=None):
        um = UserManager()

        # Если уже есть сессия, перенаправляем на главную
        session_token = request.get('session', {}).get('token') or request.get('cookies', {}).get('session_token')
        if session_token:
            valid = um.validate_session(session_token)
            if valid['valid']:
                return self.render(template_engine, 'redirect.html', {'url': '/'})

        if request['method'] == 'GET':
            return self.render(template_engine, 'login.html', {'error': None})

        elif request['method'] == 'POST':
            post_data = request['post_data']
            username = post_data.get('username', '').strip()
            password = post_data.get('password', '')

            if not username or not password:
                return self.render(template_engine, 'login.html', {'error': 'Заполните все поля'})

            result = um.authenticate(username, password)

            if result['success']:
                # СОХРАНЯЕМ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ В СЕССИЮ
                # Создаём ответ с установкой cookie
                cookie = f"session_token={result['session_token']}; Path=/; HttpOnly; Max-Age={24 * 60 * 60}"

                # ВАЖНО: сохраняем данные пользователя в сессию (для последующих запросов)
                # Это будет доступно через request['session'] после middleware
                user_data = {
                    'user_id': result['user_id'],
                    'username': result['username'],
                    'role': result['role'],
                    'full_name': result.get('full_name', '')
                }

                html, content_type = self.render(template_engine, 'redirect.html', {'url': '/'})

                response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nSet-Cookie: {cookie}\r\nContent-Length: {len(html)}\r\n\r\n{html}"
                return response.encode()
            else:
                return self.render(template_engine, 'login.html', {'error': result['error']})


class RegisterHandler(BaseHandler):
    """Обработчик регистрации"""

    def handle(self, request, template_engine, params=None):
        um = UserManager()

        if request['method'] == 'GET':
            return self.render(template_engine, 'register.html', {'error': None})

        elif request['method'] == 'POST':
            post_data = request['post_data']
            username = post_data.get('username', '').strip()
            password = post_data.get('password', '')
            confirm_password = post_data.get('confirm_password', '')
            email = post_data.get('email', '')
            full_name = post_data.get('full_name', '')

            if not username or not password:
                return self.render(template_engine, 'register.html', {'error': 'Заполните обязательные поля'})

            if password != confirm_password:
                return self.render(template_engine, 'register.html', {'error': 'Пароли не совпадают'})

            result = um.register(username, password, email, full_name, 'viewer')

            if result['success']:
                return self.render(template_engine, 'register_success.html', {'username': username})
            else:
                return self.render(template_engine, 'register.html', {'error': result['error']})


class LogoutHandler(BaseHandler):
    """Обработчик выхода из системы"""

    def handle(self, request, template_engine, params=None):
        um = UserManager()

        session_token = request.get('cookies', {}).get('session_token')
        if session_token:
            um.logout(session_token)

        # Удаляем cookie
        cookie = "session_token=; Path=/; HttpOnly; Max-Age=0"
        html = "<html><body><script>window.location.href='/login'</script></body></html>"
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nSet-Cookie: {cookie}\r\nContent-Length: {len(html)}\r\n\r\n{html}"
        return response.encode()


class ProfileHandler(BaseHandler):
    """Профиль пользователя"""

    def handle(self, request, template_engine, params=None):
        um = UserManager()

        user_id = request.get('session', {}).get('user_id')
        if not user_id:
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user = um.get_user(user_id)
        if not user:
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        if request['method'] == 'GET':
            return self.render(template_engine, 'profile.html', {
                'user': user,
                'error': None,
                'success': None
            })

        elif request['method'] == 'POST':
            post_data = request['post_data']

            if 'change_password' in post_data:
                old_password = post_data.get('old_password', '')
                new_password = post_data.get('new_password', '')
                confirm_password = post_data.get('confirm_password', '')

                if new_password != confirm_password:
                    return self.render(template_engine, 'profile.html', {
                        'user': user, 'error': 'Новые пароли не совпадают', 'success': None
                    })

                result = um.change_password(user_id, old_password, new_password)
                if result['success']:
                    return self.render(template_engine, 'profile.html', {
                        'user': user, 'error': None, 'success': 'Пароль успешно изменён'
                    })
                else:
                    return self.render(template_engine, 'profile.html', {
                        'user': user, 'error': result['error'], 'success': None
                    })

            return self.render(template_engine, 'profile.html', {'user': user, 'error': None, 'success': None})