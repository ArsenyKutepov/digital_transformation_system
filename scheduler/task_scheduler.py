import time
import threading
import os
import shutil
from datetime import datetime
from database.connection import DatabaseConnection
from core.notification_manager import NotificationManager
from core.sprint_manager import SprintManager
from core.prediction_model import PredictionModel
from export.report_generator import ReportGenerator
from config import DATABASE_PATH, BACKUPS_DIR


class TaskScheduler:
    """Планировщик периодических задач без внешних зависимостей"""

    def __init__(self):
        self.db = DatabaseConnection()
        self.notification_manager = NotificationManager()
        self.sprint_manager = SprintManager()
        self.prediction_model = PredictionModel()
        self.report_generator = ReportGenerator()
        self._running = False
        self._last_run = {}

    def _should_run(self, task_name: str, interval_seconds: int) -> bool:
        """Проверка, нужно ли запускать задачу"""
        now = time.time()
        last_run = self._last_run.get(task_name, 0)
        if now - last_run >= interval_seconds:
            self._last_run[task_name] = now
            return True
        return False

    def check_overdue_sprints(self):
        """Проверка просроченных спринтов"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка просроченных спринтов...")
        try:
            overdue = self.sprint_manager.check_overdue_sprints()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Найдено просроченных спринтов: {len(overdue)}")
        except Exception as e:
            print(f"[ERROR] check_overdue_sprints: {e}")

    def send_sprint_reminders(self):
        """Отправка напоминаний о спринтах"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Отправка напоминаний о спринтах...")
        try:
            self.notification_manager.send_sprint_reminders()
        except Exception as e:
            print(f"[ERROR] send_sprint_reminders: {e}")

    def run_predictions(self):
        """Запуск прогнозирования для всех организаций"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запуск прогнозирования ЦЗ...")
        try:
            orgs = self.db.query("SELECT id FROM organizations")
            for org in orgs:
                self.prediction_model.predict_future_scores(org['id'])
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Прогнозирование завершено для {len(orgs)} организаций")
        except Exception as e:
            print(f"[ERROR] run_predictions: {e}")

    def generate_weekly_reports(self):
        """Еженедельная генерация отчётов"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Генерация еженедельных отчётов...")
        try:
            orgs_with_plans = self.db.query("""
                SELECT DISTINCT o.id, o.name 
                FROM organizations o
                JOIN transformation_plans p ON o.id = p.org_id
                WHERE p.status = 'active'
            """)
            for org in orgs_with_plans:
                filename = f"reports/weekly_{org['id']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                self.report_generator.export_to_excel(org['id'], filename)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Создано отчётов: {len(orgs_with_plans)}")
        except Exception as e:
            print(f"[ERROR] generate_weekly_reports: {e}")

    def update_benchmarks(self):
        """Обновление агрегированных бенчмарков"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Обновление бенчмарков...")
        try:
            industries = self.db.query("SELECT code FROM industries")
            for industry in industries:
                scores = self.db.query("""
                    SELECT a.final_score 
                    FROM assessments a
                    JOIN organizations o ON a.org_id = o.id
                    WHERE o.industry = ?
                """, (industry['code'],))
                if scores:
                    score_list = [s['final_score'] for s in scores]
                    score_list.sort()
                    n = len(score_list)
                    p25 = score_list[int(n * 0.25)] if n > 0 else 0
                    p50 = score_list[int(n * 0.50)] if n > 0 else 0
                    p75 = score_list[int(n * 0.75)] if n > 0 else 0
                    leader = max(score_list) if score_list else 0
                    self.db.execute(
                        "UPDATE benchmarks SET percentile_25 = ?, percentile_50 = ?, percentile_75 = ?, leader_value = ?, updated_at = CURRENT_TIMESTAMP WHERE industry_code = ? AND metric_name = 'final_score'",
                        (p25, p50, p75, leader, industry['code'])
                    )
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Бенчмарки обновлены для {len(industries)} отраслей")
        except Exception as e:
            print(f"[ERROR] update_benchmarks: {e}")

    def cleanup_old_sessions(self):
        """Очистка старых сессий"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Очистка старых сессий...")
        try:
            deleted = self.db.execute("DELETE FROM user_sessions WHERE expires_at < datetime('now')")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Удалено старых сессий: {deleted}")
        except Exception as e:
            print(f"[ERROR] cleanup_old_sessions: {e}")

    def backup_database(self):
        """Резервное копирование базы данных"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Создание резервной копии БД...")
        try:
            if not os.path.exists(BACKUPS_DIR):
                os.makedirs(BACKUPS_DIR, exist_ok=True)
            backup_path = f"{BACKUPS_DIR}/db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DATABASE_PATH, backup_path)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Резервная копия создана: {backup_path}")
        except Exception as e:
            print(f"[ERROR] backup_database: {e}")

    def run(self):
        """Запуск планировщика в отдельном потоке"""
        self._running = True
        print("[Scheduler] Планировщик задач запущен")

        while self._running:
            now = datetime.now()
            if now.hour == 9 and now.minute == 0 and self._should_run('check_overdue_sprints', 3600):
                self.check_overdue_sprints()
            if now.hour == 10 and now.minute == 0 and self._should_run('send_sprint_reminders', 3600):
                self.send_sprint_reminders()
            if now.weekday() == 0 and now.hour == 8 and now.minute == 0 and self._should_run('run_predictions', 86400):
                self.run_predictions()
            if now.weekday() == 4 and now.hour == 17 and now.minute == 0 and self._should_run('generate_weekly_reports',
                                                                                              86400):
                self.generate_weekly_reports()
            if now.hour == 2 and now.minute == 0 and self._should_run('update_benchmarks', 3600):
                self.update_benchmarks()
            if now.hour == 3 and now.minute == 0 and self._should_run('cleanup_old_sessions', 3600):
                self.cleanup_old_sessions()
            if now.weekday() == 6 and now.hour == 1 and now.minute == 0 and self._should_run('backup_database', 86400):
                self.backup_database()
            time.sleep(30)

    def stop(self):
        self._running = False
        print("[Scheduler] Планировщик задач остановлен")


def start_scheduler():
    scheduler = TaskScheduler()
    thread = threading.Thread(target=scheduler.run, daemon=True)
    thread.start()
    return scheduler
