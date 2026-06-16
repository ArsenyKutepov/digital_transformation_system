"""
Миграции базы данных для обновления схемы
"""

import sqlite3
import os
from config import DATABASE_PATH


class Migration:
    """Управление миграциями БД"""

    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_migrations_table()

    def _init_migrations_table(self):
        """Создание таблицы для отслеживания миграций"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def get_current_version(self) -> int:
        """Получение текущей версии БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) as version FROM migrations")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row[0] else 0

    def apply_migration(self, version: int, up_sql: str, down_sql: str = None):
        """Применение миграции"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.executescript(up_sql)
            cursor.execute("INSERT INTO migrations (version) VALUES (?)", (version,))
            conn.commit()
            print(f"Миграция версии {version} применена")
        except Exception as e:
            conn.rollback()
            print(f"Ошибка при применении миграции {version}: {e}")
            raise
        finally:
            conn.close()

    def run_all_migrations(self):
        """Запуск всех необходимых миграций"""
        current = self.get_current_version()

        # Миграция 1: Добавление индексов
        if current < 1:
            self.apply_migration(1, """
                CREATE INDEX IF NOT EXISTS idx_assessments_org_id ON assessments(org_id);
                CREATE INDEX IF NOT EXISTS idx_assessments_date ON assessments(assessment_date);
                CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(resource_type);
            """)

        # Миграция 2: Добавление поля priority в actions
        if current < 2:
            self.apply_migration(2, """
                ALTER TABLE actions ADD COLUMN priority INTEGER DEFAULT 3;
            """)

        # Миграция 3: Добавление таблицы recommendations
        if current < 3:
            self.apply_migration(3, """
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER NOT NULL,
                    assessment_id INTEGER NOT NULL,
                    recommendation_text TEXT NOT NULL,
                    priority INTEGER DEFAULT 3,
                    is_applied INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (org_id) REFERENCES organizations(id),
                    FOREIGN KEY (assessment_id) REFERENCES assessments(id)
                );
            """)


# Запуск миграций при инициализации
def run_migrations():
    mig = Migration()
    mig.run_all_migrations()


if __name__ == "__main__":
    run_migrations()