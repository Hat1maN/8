from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from game.models import GameSession, LeaderboardEntry, Friendship
import json

class GameViewsTest(TestCase):
    """Тесты для представлений приложения game"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем пользователей
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )
        
        # Создаем клиент API
        self.client = APIClient()
        
        # Создаем тестовые игровые сессии
        self.game_session1 = GameSession.objects.create(
            user=self.user1,
            score=100,
            difficulty='medium',
            time_played=300,
            is_completed=True
        )
        self.game_session2 = GameSession.objects.create(
            user=self.user1,
            score=200,
            difficulty='hard',
            time_played=500,
            is_completed=False
        )
        
        # Создаем запись в лидерборде
        self.leaderboard_entry = LeaderboardEntry.objects.create(
            user=self.user1,
            score=200,
            rank=1
        )
    
    def test_save_game_session_authenticated(self):
        """Тест сохранения игровой сессии (авторизованный пользователь)"""
        # Авторизуем пользователя
        self.client.force_authenticate(user=self.user1)
        
        # Данные для сохранения
        data = {
            'score': 150,
            'difficulty': 'easy',
            'time_played': 200,
            'is_completed': True,
            'game_state': {'maze': [[0, 1], [1, 0]], 'player': {'x': 1, 'y': 1}}
        }
        
        # Отправляем POST запрос
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем ответ
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['score'], 150)
        self.assertEqual(response.data['difficulty'], 'easy')
        
        # Проверяем, что сессия сохранена в БД
        self.assertEqual(GameSession.objects.filter(user=self.user1).count(), 3)
    
    def test_save_game_session_unauthenticated(self):
        """Тест сохранения игровой сессии (неавторизованный пользователь)"""
        # НЕ авторизуем пользователя
        
        data = {
            'score': 150,
            'difficulty': 'easy',
            'time_played': 200,
            'is_completed': True,
        }
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Должен быть 401 Unauthorized (или 403 Forbidden)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_load_last_session_authenticated(self):
        """Тест загрузки последней сессии (авторизованный пользователь)"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/game/session/load/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 200)  # Последняя сессия с score=200
        self.assertEqual(response.data['difficulty'], 'hard')
    
    def test_load_last_session_unauthenticated(self):
        """Тест загрузки последней сессии (неавторизованный пользователь)"""
        # НЕ авторизуем пользователя
        
        response = self.client.get('/api/game/session/load/')
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_load_last_session_no_sessions(self):
        """Тест загрузки последней сессии (нет сохранений)"""
        # Создаем нового пользователя без сессий
        new_user = User.objects.create_user(
            username='newuser',
            password='newpass'
        )
        self.client.force_authenticate(user=new_user)
        
        response = self.client.get('/api/game/session/load/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Нет сохранений')
    
    def test_leaderboard_view(self):
        """Тест получения лидерборда"""
        # Лидерборд доступен всем (даже неавторизованным)
        response = self.client.get('/api/game/leaderboard/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # Проверяем данные
        if len(response.data) > 0:
            entry = response.data[0]
            self.assertIn('username', entry)
            self.assertIn('score', entry)
            self.assertIn('rank', entry)
    
    def test_send_friend_request_authenticated(self):
        """Тест отправки запроса в друзья"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'username': 'testuser2'
        }
        
        response = self.client.post(
            '/api/game/friends/send/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Проверяем, что запрос создан в БД
        friendship = Friendship.objects.get(from_user=self.user1, to_user=self.user2)
        self.assertEqual(friendship.status, 'pending')
    
    def test_send_friend_request_to_self(self):
        """Тест отправки запроса в друзья самому себе"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'username': 'testuser1'  # Себе
        }
        
        response = self.client.post(
            '/api/game/friends/send/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Нельзя добавить себя', response.data['error'])
    
    def test_send_friend_request_to_nonexistent_user(self):
        """Тест отправки запроса несуществующему пользователю"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'username': 'nonexistentuser'
        }
        
        response = self.client.post(
            '/api/game/friends/send/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertIn('не найден', response.data['error'])
    
    def test_send_friend_request_unauthenticated(self):
        """Тест отправки запроса в друзья (неавторизованный)"""
        # НЕ авторизуем пользователя
        
        data = {
            'username': 'testuser2'
        }
        
        response = self.client.post(
            '/api/game/friends/send/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_friends_list_view_authenticated(self):
        """Тест получения списка друзей (авторизованный)"""
        # Создаем запрос в друзья
        Friendship.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/game/friends/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('incoming_requests', response.data)
        self.assertIn('friends', response.data)
        
        # Проверяем входящие запросы
        self.assertIn('testuser2', response.data['incoming_requests'])
    
    def test_friends_list_view_unauthenticated(self):
        """Тест получения списка друзей (неавторизованный)"""
        response = self.client.get('/api/game/friends/')
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_accept_friend_request(self):
        """Тест принятия запроса в друзья"""
        # Создаем запрос в друзья
        Friendship.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'username': 'testuser2'
        }
        
        response = self.client.post(
            '/api/game/friends/accept/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что статус изменился
        friendship = Friendship.objects.get(from_user=self.user2, to_user=self.user1)
        self.assertEqual(friendship.status, 'accepted')
    
    def test_reject_friend_request(self):
        """Тест отклонения запроса в друзья"""
        # Создаем запрос в друзья
        Friendship.objects.create(
            from_user=self.user2,
            to_user=self.user1,
            status='pending'
        )
        
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'username': 'testuser2'
        }
        
        response = self.client.post(
            '/api/game/friends/reject/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что запрос удален
        with self.assertRaises(Friendship.DoesNotExist):
            Friendship.objects.get(from_user=self.user2, to_user=self.user1, status='pending')