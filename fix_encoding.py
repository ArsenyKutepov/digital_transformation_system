# -*- coding: utf-8 -*-
"""
Фикс кодировки для Windows консоли
"""

import sys
import os


def fix_console_encoding():
    """Исправление кодировки консоли Windows"""
    if sys.platform == 'win32':
        try:
            # Попытка установить кодировку 65001 (UTF-8)
            os.system('chcp 65001 > nul')
        except:
            pass

        # Перенаправление stdout/stderr
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', errors='replace', buffering=1)
            sys.stderr = open(sys.stderr.fileno(), 'w', encoding='utf-8', errors='replace', buffering=1)


def fix_file_encoding(filepath, from_encoding='cp1251', to_encoding='utf-8'):
    """Конвертация файла из одной кодировки в другую"""
    if not os.path.exists(filepath):
        return

    try:
        with open(filepath, 'r', encoding=from_encoding, errors='ignore') as f:
            content = f.read()

        with open(filepath, 'w', encoding=to_encoding, errors='ignore') as f:
            f.write(content)

        print(f"Конвертирован: {filepath}")
    except Exception as e:
        print(f"Ошибка конвертации {filepath}: {e}")


# Автоматический вызов
fix_console_encoding()