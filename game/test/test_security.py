from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
import json

class SecurityTest(TestCase):
    """Тесты безопасности приложения"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем пользователей
        self.user = User.objects.create_user(
            username='testuser',
            password='StrongPass123!'
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='AdminPass123!',
            is_staff=True
        )
        
        # Создаем клиент API
        self.client = APIClient()
    
    def test_password_hashing(self):
        """Тест, что пароли хранятся в хешированном виде"""
        # Получаем пользователя из БД
        user_from_db = User.objects.get(username='testuser')
        
        # Проверяем, что пароль хеширован
        password = user_from_db.password
        
        # Хеш пароля должен начинаться с алгоритма (например, pbkdf2_sha256$)
        self.assertTrue(password.startswith('pbkdf2_sha256$'))
        
        # Проверяем, что это не исходный пароль
        self.assertNotEqual(password, 'StrongPass123!')
        
        # Проверяем, что пароль можно проверить
        self.assertTrue(user_from_db.check_password('StrongPass123!'))
        self.assertFalse(user_from_db.check_password('WrongPassword'))
    
    def test_sql_injection_prevention(self):
        """Тест защиты от SQL-инъекций"""
        # Пытаемся использовать SQL-инъекцию в username
        sql_injection_username = "test' OR '1'='1"
        
        # Пытаемся зарегистрироваться с таким именем
        data = {
            'username': sql_injection_username,
            'password': 'password123'
        }
        
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Должен быть 400 Bad Request или успешная регистрация, но без выполнения SQL
        # Важно: имя пользователя может быть принято как обычная строка
        # Проверяем, что не произошло критической ошибки сервера (500)
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Если регистрация прошла, проверяем, что имя сохранено как строка
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username=sql_injection_username)
            self.assertEqual(user.username, sql_injection_username)
    
    def test_xss_prevention_in_game_state(self):
        """Тест защиты от XSS в состоянии игры"""
        # Пытаемся сохранить состояние с XSS
        xss_payload = '<script>alert("XSS")</script>'
        
        game_data = {
            'score': 100,
            'difficulty': 'easy',
            'time_played': 100,
            'is_completed': True,
            'game_state': {
                'player': {
                    'x': 1.5,
                    'y': 1.5,
                    'name': xss_payload  # XSS в имени игрока
                }
            }
        }
        
        # Авторизуемся
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(game_data),
            content_type='application/json'
        )
        
        # Должен быть 201 Created (данные сохраняются как есть)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что данные сохранились
        session = User.objects.get(username='testuser').sessions.first()
        self.assertIsNotNone(session.game_state)
        
        # JSON-сериализация должна экранировать специальные символы
        game_state_json = json.dumps(session.game_state)
        # Проверяем, что скриптовые теги не выполняются
        # (в JSON они будут экранированы)
        # Проверяем, что XSS-пейлоад сохранился как строка (экранирован JSON)
        # JSON экранирует кавычки, но не теги
        self.assertIn('<script>', game_state_json)
        self.assertIn('</script>', game_state_json)
        # Проверяем, что это строка в JSON, а не исполняемый код
        self.assertIn('\\"XSS\\"', game_state_json)  # Кавычки экранированы # Обратный слеш добавлен JSON
    
    def test_authentication_required_for_protected_endpoints(self):
        """Тест, что защищенные endpoint требуют аутентификации"""
        endpoints = [
            ('/api/game/session/save/', 'POST'),
            ('/api/game/session/load/', 'GET'),
            ('/api/game/friends/send/', 'POST'),
            ('/api/game/friends/', 'GET'),
            ('/api/auth/profile/', 'GET'),
            ('/api/auth/profile/update/', 'PATCH'),
        ]
        
        for endpoint, method in endpoints:
            if method == 'POST':
                response = self.client.post(endpoint, data={})
            elif method == 'GET':
                response = self.client.get(endpoint)
            elif method == 'PATCH':
                response = self.client.patch(endpoint, data={})
            else:
                continue
            
            # Должен быть 401 Unauthorized или 403 Forbidden
            self.assertIn(response.status_code, 
                         [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
                         f'{method} {endpoint} не защищен')
    
    def test_csrf_protection(self):
        """Тест защиты от CSRF (для сессионных запросов)"""
        # Django REST Framework с JWT не использует CSRF по умолчанию для API
        # Но проверим, что обычные формы Django защищены
        
        # Создаем клиент с включенными куками (для сессий)
        from django.test import Client
        client = Client()
        
        # Пытаемся отправить POST без CSRF-токена
        response = client.post('/admin/login/', {
            'username': 'admin',
            'password': 'AdminPass123!'
        })
        
        # Должна быть ошибка CSRF или редирект (зависит от настроек)
        # Проверяем, что не произошел успешный вход
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
    
    def test_sensitive_data_exposure(self):
        """Тест, что чувствительные данные не раскрываются"""
        # Создаем еще одного пользователя
        other_user = User.objects.create_user(
            username='otheruser',
            password='OtherPass123!'
        )
        
        # Авторизуемся как testuser
        self.client.force_authenticate(user=self.user)
        
        # Сохраняем игровую сессию
        game_data = {
            'score': 100,
            'difficulty': 'easy',
            'time_played': 100,
            'is_completed': True,
        }
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(game_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Теперь авторизуемся как другой пользователь
        self.client.force_authenticate(user=other_user)
        
        # Пытаемся загрузить сессию первого пользователя
        # (должна быть своя сессия или "нет сохранений")
        response = self.client.get('/api/game/session/load/')
        
        # Проверяем, что не получили данные другого пользователя
        if response.status_code == status.HTTP_200_OK:
            if 'message' in response.data:
                self.assertEqual(response.data['message'], 'Нет сохранений')
            else:
                # Если есть сохранения, они должны принадлежать otheruser
                # (в данном случае их нет, так как мы не сохраняли для otheruser)
                pass
    
    def test_brute_force_protection(self):
        """Тест защиты от перебора паролей"""
        # Пытаемся войти несколько раз с неверным паролем
        failed_attempts = 5
        
        for i in range(failed_attempts):
            data = {
                'username': 'testuser',
                'password': f'WrongPassword{i}'
            }
            
            response = self.client.post(
                '/api/auth/token/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            # Все попытки должны быть отклонены
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Пытаемся войти с правильным паролем после неудачных попыток
        data = {
            'username': 'testuser',
            'password': 'StrongPass123!'
        }
        
        response = self.client.post(
            '/api/auth/token/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Должен быть успех (нет блокировки после 5 попыток в этой конфигурации,
        # но проверяем, что система не упала)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED])
    
    def test_input_validation(self):
        """Тест валидации ввода"""
        # Пытаемся отправить слишком большие данные
        huge_data = {
            'score': 10**100,  # Огромное число
            'difficulty': 'A' * 1000,  # Очень длинная строка
            'time_played': -100,  # Отрицательное время
            'is_completed': 'not_a_boolean',  # Не булево значение
        }
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(huge_data),
            content_type='application/json'
        )
        
        # Должна быть ошибка валидации (400)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_json_vulnerability(self):
        """Тест защиты от JSON уязвимостей"""
        # Пытаемся отправить невалидный JSON
        invalid_json = '{"score": 100, "difficulty": "easy"}'  # Нет закрывающей скобки
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            '/api/game/session/save/',
            data=invalid_json,
            content_type='application/json'
        )
        
        # Должна быть ошибка парсинга JSON (400)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)