print("1. Importing config...")
import config
print("OK")

print("2. Importing database.connection...")
from database.connection import DatabaseConnection
print("OK")

print("3. Importing database.models...")
from database.models import Organization, Assessment, Action
print("OK")

print("4. Importing core.fuzzy_logic...")
from core.fuzzy_logic import DigitalMaturityModel
print("OK")

print("5. Importing core.dqn_agent...")
from core.dqn_agent import DQNAgent
print("OK")

print("6. Importing core.environment...")
from core.environment import DigitalTransformationEnvironment
print("OK")

print("7. Importing core.sprint_manager...")
from core.sprint_manager import SprintManager
print("OK")

print("8. Importing core.notification_manager...")
from core.notification_manager import NotificationManager
print("OK")

print("9. Importing web.router...")
from web.router import Router
print("OK")

print("10. Importing web.templates...")
from web.templates import TemplateEngine
print("OK")

print("11. Importing web.handlers...")
from web.handlers import IndexHandler, AssessmentHandler, ResultsHandler, PlanningHandler, CompareHandler
print("OK")

print("12. Importing web.auth_handlers...")
from web.auth_handlers import LoginHandler, RegisterHandler, LogoutHandler, ProfileHandler
print("OK")

print("13. Importing web.sprint_handlers...")
from web.sprint_handlers import SprintListHandler, SprintStartHandler, SprintCompleteHandler, SprintViewHandler, PlanRescheduleHandler
print("OK")

print("14. Importing web.notification_handlers...")
from web.notification_handlers import NotificationListHandler, NotificationReadHandler, NotificationReadAllHandler, NotificationDeleteHandler
print("OK")

print("15. Importing web.analytics_handlers...")
from web.analytics_handlers import AnalyticsDashboardHandler, WeakBlocksHandler
print("OK")

print("16. Importing web.export_handlers...")
from web.export_handlers import ExportExcelHandler, ExportJsonHandler, ExportCsvHandler, DashboardHtmlHandler
print("OK")

print("17. Importing web.admin_handlers...")
from web.admin_handlers import AdminDashboardHandler, AdminActionsHandler, SchedulerAdminHandler
print("OK")

print("18. Importing api.rest_api...")
from api.rest_api import RESTAPIHandler
print("OK")

print("19. Importing scheduler.task_scheduler...")
from scheduler.task_scheduler import TaskScheduler
print("OK")

print("ALL IMPORTS SUCCESSFUL!")