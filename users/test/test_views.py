from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import UserProfile
import json

class UsersViewsTest(TestCase):
    """Тесты для представлений приложения users"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Создаем профиль
        self.profile = UserProfile.objects.create(
            user=self.user,
            bio='Тестовая биография',
            date_of_birth='1990-01-01'
        )
        
        # Создаем клиент API
        self.client = APIClient()
        
        # Создаем токен для пользователя
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
    
    def test_register_view_success(self):
        """Тест успешной регистрации"""
        data = {
            'username': 'newuser',
            'password': 'NewPass123',
            'email': 'new@example.com'
        }
        
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        
        # Проверяем, что пользователь создан
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Проверяем, что профиль создан
        new_user = User.objects.get(username='newuser')
        self.assertTrue(UserProfile.objects.filter(user=new_user).exists())
    
    def test_register_view_missing_fields(self):
        """Тест регистрации с отсутствующими полями"""
        # Без username
        data = {
            'password': 'NewPass123'
        }
        
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_view_existing_username(self):
        """Тест регистрации с существующим именем пользователя"""
        data = {
            'username': 'testuser',  # Уже существует
            'password': 'NewPass123'
        }
        
        response = self.client.post(
            '/api/auth/register/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('уже существует', response.data['error'])
    
    def test_login_view_success(self):
        """Тест успешного входа"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/api/auth/token/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_view_wrong_password(self):
        """Тест входа с неверным паролем"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(
            '/api/auth/token/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # SimpleJWT возвращает 401 при неверных учетных данных
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_view_nonexistent_user(self):
        """Тест входа с несуществующим пользователем"""
        data = {
            'username': 'nonexistent',
            'password': 'somepassword'
        }
        
        response = self.client.post(
            '/api/auth/token/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_view_authenticated(self):
        """Тест получения профиля (авторизованный пользователь)"""
        # Авторизуем пользователя через токен
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'testuser')
        self.assertEqual(response.data['bio'], 'Тестовая биография')
        self.assertEqual(response.data['date_of_birth'], '1990-01-01')
    
    def test_profile_view_unauthenticated(self):
        """Тест получения профиля (неавторизованный пользователь)"""
        # НЕ авторизуем пользователя
        
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_profile_update_view_authenticated(self):
        """Тест обновления профиля (авторизованный пользователь)"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Создаем тестовый файл для аватара
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Просто обновляем текстовые поля (без файла)
        data = {
            'bio': 'Обновленная биография',
            'date_of_birth': '1995-05-15'
        }
        
        response = self.client.patch(
            '/api/auth/profile/update/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем обновление в БД
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'Обновленная биография')
        self.assertEqual(str(self.profile.date_of_birth), '1995-05-15')
    
    def test_profile_update_view_unauthenticated(self):
        """Тест обновления профиля (неавторизованный пользователь)"""
        # НЕ авторизуем пользователя
        
        data = {
            'bio': 'Попытка обновить без авторизации'
        }
        
        response = self.client.patch(
            '/api/auth/profile/update/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh_view(self):
        """Тест обновления токена"""
        # Сначала получаем refresh токен через логин
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        login_response = self.client.post(
            '/api/auth/token/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        refresh_token = login_response.data['refresh']
        
        # Обновляем токен
        data = {
            'refresh': refresh_token
        }
        
        response = self.client.post(
            '/api/auth/token/refresh/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_protected_view_access_with_token(self):
        """Тест доступа к защищенному представлению с токеном"""
        # Используем токен для доступа к профилю
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_protected_view_access_without_token(self):
        """Тест доступа к защищенному представлению без токена"""
        # НЕ устанавливаем токен
        
        response = self.client.get('/api/auth/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)