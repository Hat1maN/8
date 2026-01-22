#!/usr/bin/env python
"""
Скрипт для запуска всех тестов проекта
"""

import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем настройки напрямую
import backend.test_settings_simple as test_settings

# Устанавливаем переменные окружения
for key in dir(test_settings):
    if key.isupper():
        os.environ[key] = str(getattr(test_settings, key))

# Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.test_settings_simple')

try:
    django.setup()
except Exception as e:
    print(f"Ошибка при настройке Django: {e}")
    sys.exit(1)

from django.test.utils import get_runner
from django.conf import settings

def run_tests():
    """Запуск всех тестов"""
    print("=" * 60)
    print("ЗАПУСК ВСЕХ ТЕСТОВ ПРОЕКТА")
    print("=" * 60)
    
    # Создаем тестовый раннер
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)
    
    # Находим все тестовые модули
    test_modules = [
        'game.test.test_models',
        'game.test.test_views', 
        'game.test.test_game_functionality',
        'game.test.test_security',
        'game.test.test_admin_export',
        'users.test.test_models',
        'users.test.test_forms',
        'users.test.test_views',
    ]
    
    # Запускаем тесты
    failures = test_runner.run_tests(test_modules)
    
    print("=" * 60)
    print(f"ИТОГ: {'ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if failures == 0 else 'ЕСТЬ ОШИБКИ'}")
    print("=" * 60)
    
    return failures

if __name__ == '__main__':
    # Сначала проверим существование тестовых файлов
    test_files = [
        'game/test/test_models.py',
        'game/test/test_views.py',
        'game/test/test_game_functionality.py',
        'game/test/test_security.py',
        'game/test/test_admin_export.py',
        'users/test/test_models.py',
        'users/test/test_forms.py',
        'users/test/test_views.py',
    ]
    
    missing_files = []
    for file in test_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("ОШИБКА: Отсутствуют тестовые файлы:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nСоздайте папки 'test' в game и users и скопируйте туда тесты")
        sys.exit(1)
    
    # Запускаем тесты
    result = run_tests()
    sys.exit(0 if result == 0 else 1)