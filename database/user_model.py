import hashlib
import os
import secrets
from datetime import datetime, timedelta
from .connection import DatabaseConnection


class UserManager:
    """Управление пользователями и аутентификация"""

    def __init__(self):
        self.db = DatabaseConnection()
        self._ensure_admin_user()

    def _ensure_admin_user(self):
        """Создание администратора по умолчанию при первом запуске"""
        admin_exists = self.db.query_one("SELECT id FROM users WHERE role = 'admin'")
        if not admin_exists:
            # Создаём администратора по умолчанию: admin / admin123
            self.register('admin', 'admin123', email='admin@system.local',
                          full_name='Системный администратор', role='admin')
            print("[INFO] Создан администратор по умолчанию: admin / admin123")

    def _hash_password(self, password: str, salt: bytes = None) -> tuple:
        """Хеширование пароля с солью (PBKDF2)"""
        if salt is None:
            salt = os.urandom(32)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt, hash_obj

    def register(self, username: str, password: str, email: str = None,
                 full_name: str = None, role: str = 'viewer') -> dict:
        """Регистрация нового пользователя"""
        # Проверка существования пользователя
        existing = self.db.query_one("SELECT id FROM users WHERE username = ?", (username,))
        if existing:
            return {'success': False, 'error': 'Пользователь с таким логином уже существует'}

        # Проверка длины пароля
        if len(password) < 6:
            return {'success': False, 'error': 'Пароль должен содержать минимум 6 символов'}

        salt, password_hash = self._hash_password(password)

        user_id = self.db.execute(
            '''INSERT INTO users (username, password_hash, salt, role, email, full_name) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (username, password_hash.hex(), salt.hex(), role, email, full_name)
        )

        return {'success': True, 'user_id': user_id, 'username': username}

    def authenticate(self, username: str, password: str, session_expiry_hours: int = 24) -> dict:
        """Аутентификация пользователя и создание сессии"""
        user = self.db.query_one("SELECT * FROM users WHERE username = ?", (username,))
        if not user:
            return {'success': False, 'error': 'Пользователь не найден'}

        salt = bytes.fromhex(user['salt'])
        _, password_hash = self._hash_password(password, salt)

        if password_hash.hex() == user['password_hash']:
            # Генерация сессии
            session_token = secrets.token_urlsafe(32)
            expires_at = (datetime.now() + timedelta(hours=session_expiry_hours)).isoformat()

            # Сохраняем сессию в БД
            self.db.execute(
                '''INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent) 
                   VALUES (?, ?, ?, ?, ?)''',
                (user['id'], session_token, expires_at, '', '')
            )

            return {
                'success': True,
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'session_token': session_token,
                'expires_at': expires_at
            }

        return {'success': False, 'error': 'Неверный пароль'}

    def validate_session(self, session_token: str) -> dict:
        """Проверка валидности сессии"""
        if not session_token:
            return {'valid': False}

        session = self.db.query_one(
            "SELECT * FROM user_sessions WHERE session_token = ? AND expires_at > datetime('now')",
            (session_token,)
        )

        if not session:
            return {'valid': False}

        user = self.get_user(session['user_id'])
        if not user:
            return {'valid': False}

        return {
            'valid': True,
            'user_id': user['id'],
            'username': user['username'],  # Важно: должно быть username
            'role': user['role'],
            'full_name': user.get('full_name')
        }

    def logout(self, session_token: str):
        """Завершение сессии"""
        self.db.execute("DELETE FROM user_sessions WHERE session_token = ?", (session_token,))

    def get_user(self, user_id: int) -> dict:
        """Получение информации о пользователе"""
        return self.db.query_one(
            "SELECT id, username, role, email, full_name, created_at FROM users WHERE id = ?",
            (user_id,)
        )

    def get_all_users(self) -> list:
        """Получение всех пользователей (для администратора)"""
        return self.db.query(
            "SELECT id, username, role, email, full_name, created_at FROM users ORDER BY created_at"
        )

    def update_role(self, user_id: int, new_role: str) -> bool:
        """Обновление роли пользователя (только для администратора)"""
        if new_role not in ['admin', 'analyst', 'viewer']:
            return False
        self.db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
        return True

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя (нельзя удалить последнего администратора)"""
        admin_count = self.db.query_one("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
        user = self.get_user(user_id)

        if user and user['role'] == 'admin' and admin_count['cnt'] <= 1:
            return False

        self.db.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        self.db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        """Смена пароля"""
        user = self.db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return {'success': False, 'error': 'Пользователь не найден'}

        salt = bytes.fromhex(user['salt'])
        _, old_hash = self._hash_password(old_password, salt)

        if old_hash.hex() != user['password_hash']:
            return {'success': False, 'error': 'Неверный текущий пароль'}

        if len(new_password) < 6:
            return {'success': False, 'error': 'Новый пароль должен содержать минимум 6 символов'}

        new_salt, new_hash = self._hash_password(new_password)
        self.db.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (new_hash.hex(), new_salt.hex(), user_id)
        )

        return {'success': True}

    def log_action(self, user_id: int, action: str, entity_type: str = None,
                   entity_id: int = None, details: str = None, ip: str = None):
        """Логирование действий пользователя"""
        self.db.execute(
            '''INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, action, entity_type, entity_id, details, ip)
        )

    def get_user_actions(self, user_id: int, limit: int = 50) -> list:
        """Получение истории действий пользователя"""
        return self.db.query(
            "SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )