from database.connection import DatabaseConnection
from core.notification_manager import NotificationManager
from .handlers import BaseHandler


class NotificationListHandler(BaseHandler):
    """Список уведомлений пользователя"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_id = self._get_user_id(request)
        notification_manager = NotificationManager()

        notifications = notification_manager.get_notifications(user_id)
        unread_count = notification_manager.get_unread_count(user_id)

        return self.render(template_engine, 'notifications.html', {
            'notifications': notifications,
            'unread_count': unread_count,
            'user': request['session']
        })


class NotificationReadHandler(BaseHandler):
    """Отметка уведомления как прочитанного"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        notification_id = params.get('id') if params else None
        if not notification_id:
            return self.render(template_engine, 'error.html', {'message': 'ID уведомления не указан'})

        notification_manager = NotificationManager()
        notification_manager.mark_as_read(int(notification_id))

        return self.render(template_engine, 'redirect.html', {'url': '/notifications'})


class NotificationReadAllHandler(BaseHandler):
    """Отметка всех уведомлений как прочитанных"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        user_id = self._get_user_id(request)
        notification_manager = NotificationManager()
        notification_manager.mark_all_as_read(user_id)

        return self.render(template_engine, 'redirect.html', {'url': '/notifications'})


class NotificationDeleteHandler(BaseHandler):
    """Удаление уведомления"""

    def handle(self, request, template_engine, params=None):
        if not self._check_auth(request):
            return self.render(template_engine, 'redirect.html', {'url': '/login'})

        notification_id = params.get('id') if params else None
        if not notification_id:
            return self.render(template_engine, 'error.html', {'message': 'ID уведомления не указан'})

        notification_manager = NotificationManager()
        notification_manager.delete_notification(int(notification_id))

        return self.render(template_engine, 'redirect.html', {'url': '/notifications'})