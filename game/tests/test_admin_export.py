from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import Client
from game.models import GameSession
import json
import io

class AdminExportTest(TestCase):
    """Тесты экспорта данных из админки"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем суперпользователя
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@example.com'
        )
        
        # Создаем обычного пользователя
        self.regular_user = User.objects.create_user(
            username='regular',
            password='regularpass123'
        )
        
        # Создаем клиент
        self.client = Client()
        
        # Создаем тестовые игровые сессии
        self.game_session1 = GameSession.objects.create(
            user=self.regular_user,
            score=100,
            difficulty='easy',
            time_played=300,
            is_completed=True
        )
        
        self.game_session2 = GameSession.objects.create(
            user=self.admin_user,
            score=200,
            difficulty='hard',
            time_played=500,
            is_completed=False
        )
    
    def test_admin_login(self):
        """Тест входа в админку"""
        # Логинимся как админ
        login_success = self.client.login(username='admin', password='adminpass123')
        self.assertTrue(login_success)
        
        # Проверяем доступ к админке
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Django administration', str(response.content))
    
    def test_regular_user_no_admin_access(self):
        """Тест, что обычный пользователь не имеет доступа к админке"""
        # Логинимся как обычный пользователь
        login_success = self.client.login(username='regular', password='regularpass123')
        self.assertTrue(login_success)
        
        # Пытаемся получить доступ к админке
        response = self.client.get('/admin/')
        
        # Должен быть редирект на страницу логина (302) или доступ запрещен (403)
        self.assertIn(response.status_code, [302, 403])
    
    def test_gamesession_export_data_integrity(self):
        """Тест целостности данных при экспорте GameSession"""
        print("\n=== Проверка данных для экспорта ===")
        
        # Получаем все GameSession
        sessions = GameSession.objects.all()
        
        print(f"Всего сессий в БД: {sessions.count()}")
        
        # Проверяем данные, которые должны быть в экспорте
        expected_fields = ['id', 'user', 'score', 'difficulty', 'time_played', 
                          'is_completed', 'created_at']
        
        for session in sessions:
            print(f"\nСессия ID {session.id}:")
            print(f"  Пользователь: {session.user.username}")
            print(f"  Счет: {session.score}")
            print(f"  Сложность: {session.difficulty}")
            print(f"  Время: {session.time_played}с")
            print(f"  Завершена: {session.is_completed}")
            
            # Проверяем, что все поля заполнены
            for field in expected_fields:
                if field == 'user':
                    value = getattr(session, field)
                    self.assertIsNotNone(value, f"Поле {field} не заполнено")
                elif field in ['id', 'score', 'time_played', 'is_completed']:
                    value = getattr(session, field)
                    self.assertIsNotNone(value, f"Поле {field} не заполнено")
        
        print("\n=== Данные готовы для экспорта ===")
    
    def test_gamesession_serialization_for_export(self):
        """Тест сериализации данных GameSession для экспорта"""
        # Собираем данные вручную (без pandas)
        sessions = GameSession.objects.all()
        
        data = []
        for session in sessions:
            data.append({
                'ID': session.id,
                'Пользователь': session.user.username,
                'Счет': session.score,
                'Сложность': session.get_difficulty_display(),
                'Время игры (сек)': session.time_played,
                'Завершена': 'Да' if session.is_completed else 'Нет',
                'Создано': session.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        # Проверяем структуру данных
        print("\n=== Структура экспортируемых данных ===")
        print(f"Колонки: {list(data[0].keys()) if data else 'Нет данных'}")
        print(f"Количество строк: {len(data)}")
        
        # Проверяем ожидаемые колонки
        expected_columns = ['ID', 'Пользователь', 'Счет', 'Сложность', 
                           'Время игры (сек)', 'Завершена', 'Создано']
        
        if data:
            for col in expected_columns:
                self.assertIn(col, data[0], f"Отсутствует колонка {col}")
        
        # Проверяем количество данных
        self.assertEqual(len(data), 2)  # Две сессии
        
        # Проверяем значения
        session1_data = data[0] if data[0]['ID'] == self.game_session1.id else data[1]
        self.assertEqual(session1_data['Пользователь'], 'regular')
        self.assertEqual(session1_data['Счет'], 100)
        self.assertEqual(session1_data['Сложность'], 'Легко')
        
        print("\nДанные сериализованы корректно")
    
    def test_export_filtering(self):
        """Тест фильтрации данных при экспорте"""
        # Создаем дополнительные сессии для теста фильтрации
        GameSession.objects.create(
            user=self.regular_user,
            score=50,
            difficulty='easy',
            time_played=100,
            is_completed=True
        )
        
        GameSession.objects.create(
            user=self.regular_user,
            score=300,
            difficulty='hard',
            time_played=600,
            is_completed=False
        )
        
        print("\n=== Тест фильтрации данных ===")
        
        # Фильтруем завершенные игры
        completed_sessions = GameSession.objects.filter(is_completed=True)
        print(f"Завершенных игр: {completed_sessions.count()}")
        
        # Фильтруем по сложности
        easy_sessions = GameSession.objects.filter(difficulty='easy')
        print(f"Игр на легкой сложности: {easy_sessions.count()}")
        
        # Фильтруем по пользователю
        user_sessions = GameSession.objects.filter(user=self.regular_user)
        print(f"Игр пользователя 'regular': {user_sessions.count()}")
        
        # Фильтруем по счету
        high_score_sessions = GameSession.objects.filter(score__gt=150)
        print(f"Игр со счетом >150: {high_score_sessions.count()}")
        
        # Проверяем фильтрацию
        self.assertEqual(completed_sessions.count(), 2)  # 2 завершенных
        self.assertEqual(easy_sessions.count(), 2)  # 2 легких
        self.assertEqual(user_sessions.count(), 3)  # 3 игры у regular
        self.assertEqual(high_score_sessions.count(), 2)  # 2 игры с score > 150
    
    def test_export_performance(self):
        """Тест производительности экспорта"""
        import time
        
        # Создаем много данных для теста производительности
        print("\n=== Тест производительности ===")
        
        # Измеряем время получения данных
        start_time = time.time()
        
        sessions = GameSession.objects.all()
        session_count = sessions.count()
        
        data_retrieval_time = time.time() - start_time
        print(f"Время получения {session_count} записей: {data_retrieval_time:.3f}с")
        
        # Проверяем, что время приемлемое
        self.assertLess(data_retrieval_time, 1.0, 
                       f"Получение данных заняло слишком долго: {data_retrieval_time:.3f}с")
        
        # Измеряем время сериализации
        start_time = time.time()
        
        data = []
        for session in sessions:
            data.append({
                'user': session.user.username,
                'score': session.score,
                'difficulty': session.difficulty,
            })
        
        serialization_time = time.time() - start_time
        print(f"Время сериализации: {serialization_time:.3f}с")
        
        self.assertLess(serialization_time, 0.5, 
                       f"Сериализация заняла слишком долго: {serialization_time:.3f}с")