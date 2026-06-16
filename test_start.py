# -*- coding: utf-8 -*-
import sys
import os

print("1. Начало запуска...")
print(f"2. Python версия: {sys.version}")
print(f"3. Платформа: {sys.platform}")

try:
    print("4. Импорт config...")
    from config import HOST, PORT

    print(f"   OK: HOST={HOST}, PORT={PORT}")

    print("5. Импорт DatabaseConnection...")
    from database.connection import DatabaseConnection

    print("   OK")

    print("6. Импорт Action...")
    from database.models import Action

    print("   OK")

    print("7. Импорт HTTPServer...")
    from web.server import HTTPServer

    print("   OK")

    print("\n" + "=" * 50)
    print("ВСЕ МОДУЛИ ЗАГРУЖЕНЫ УСПЕШНО!")
    print("=" * 50)

except Exception as e:
    print(f"\n!!! ОШИБКА: {e}")
    import traceback

    traceback.print_exc()