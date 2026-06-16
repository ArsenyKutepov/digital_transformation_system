#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Интеллектуальная система поддержки принятия решений
по цифровой трансформации организационного объекта

Магистерская диссертация - Кутепов А.А.
Кубанский государственный университет, 2025
"""

import sys
import os
import signal
import threading
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from database.models import Action
from web.server import HTTPServer
from config import HOST, PORT


def init_logging():
    """Инициализация системы логирования"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'app.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


logger = init_logging()


def init_model_file():
    """Создание файла модели DQN при отсутствии"""
    import pickle

    model_dir = 'models'
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)

    model_path = os.path.join(model_dir, 'dqn_model.pkl')
    if not os.path.exists(model_path):
        with open(model_path, 'wb') as f:
            pickle.dump({
                'initialized': True,
                'version': 1,
                'created_at': str(__import__('datetime').datetime.now())
            }, f)
        logger.info("Создан файл модели DQN: %s", model_path)


def init_database():
    """Инициализация базы данных"""
    logger.info("Инициализация базы данных...")
    try:
        db = DatabaseConnection()
        Action.initialize_default_actions()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error("Ошибка инициализации БД: %s", e)
        sys.exit(1)


def start_scheduler():
    """Запуск планировщика периодических задач в фоновом потоке"""
    try:
        from scheduler.task_scheduler import TaskScheduler

        scheduler = TaskScheduler()
        thread = threading.Thread(target=scheduler.run, daemon=True)
        thread.start()
        logger.info("Планировщик задач запущен")
        return scheduler
    except ImportError as e:
        logger.warning("Модуль планировщика не найден: %s", e)
        return None
    except Exception as e:
        logger.error("Ошибка запуска планировщика: %s", e)
        return None


def print_banner():
    """Вывод баннера при запуске"""
    banner = """
    ============================================================

        ИНТЕЛЛЕКТУАЛЬНАЯ СИСТЕМА ПОДДЕРЖКИ ПРИНЯТИЯ РЕШЕНИЙ
         по цифровой трансформации организационного объекта

                         Магистерская диссертация
                              Кутепов А.А.
                    Кубанский государственный университет
                                 2025

    ============================================================
    """
    print(banner)
    logger.info("Система запущена")


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Получен сигнал завершения. Остановка сервера...")
    print("\n[INFO] Получен сигнал завершения. Остановка сервера...")
    sys.exit(0)


def main():
    """Главная функция"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print_banner()
    init_database()
    init_model_file()

    scheduler = start_scheduler()

    print(f"\n[INFO] Запуск веб-сервера на http://{HOST}:{PORT}")
    print("[INFO] Для остановки нажмите Ctrl+C")
    print("[INFO] Демо-доступ: admin / admin123")

    if scheduler:
        print("[INFO] Планировщик задач запущен (ежедневные напоминания, бэкапы)")
    else:
        print("[INFO] Планировщик задач не запущен")

    print()

    try:
        server = HTTPServer(host=HOST, port=PORT)
        server.run()
    except KeyboardInterrupt:
        logger.info("Система остановлена пользователем")
        print("\n[INFO] Система остановлена.")
    except Exception as e:
        logger.error("Критическая ошибка: %s", e)
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()