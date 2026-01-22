from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from game.models import GameSession, LeaderboardEntry
import json

class GameFunctionalityTest(TestCase):
    """Тесты основного функционала игры"""
    
    def setUp(self):
        """Создаем тестовые данные"""
        # Создаем пользователей
        self.user1 = User.objects.create_user(
            username='player1',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='player2',
            password='pass123'
        )
        
        # Создаем клиент API
        self.client = APIClient()
        
        # Авторизуем пользователя
        self.client.force_authenticate(user=self.user1)
    
    def test_complete_game_cycle(self):
        """Тест полного цикла игры: сохранение -> лидерборд"""
        print("\n=== Тест полного цикла игры ===")
        
        # Шаг 1: Играем игру (сохраняем незавершенную сессию)
        game_data1 = {
            'score': 50,
            'difficulty': 'easy',
            'time_played': 100,
            'is_completed': False,  # Еще не завершена
            'game_state': {'player': {'x': 5, 'y': 5}}
        }
        
        response1 = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(game_data1),
            content_type='application/json'
        )
        print(f"1. Сохранена незавершенная игра: {response1.status_code}")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что сессия сохранена
        sessions_count = GameSession.objects.filter(user=self.user1).count()
        print(f"   Сессий в БД: {sessions_count}")
        self.assertEqual(sessions_count, 1)
        
        # Шаг 2: Завершаем игру (победа)
        game_data2 = {
            'score': 150,  # Больше очков
            'difficulty': 'easy',
            'time_played': 300,
            'is_completed': True,  # Завершена
            'game_state': {}
        }
        
        response2 = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(game_data2),
            content_type='application/json'
        )
        print(f"2. Сохранена завершенная игра: {response2.status_code}")
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что теперь 2 сессии
        sessions_count = GameSession.objects.filter(user=self.user1).count()
        print(f"   Сессий в БД: {sessions_count}")
        self.assertEqual(sessions_count, 2)
        
        # Шаг 3: Проверяем лидерборд
        # Сначала получаем как авторизованный пользователь
        self.client.force_authenticate(user=self.user1)
        response3 = self.client.get('/api/game/leaderboard/')
        print(f"3. Получен лидерборд: {response3.status_code}")
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        
        # Проверяем структуру данных
        self.assertIsInstance(response3.data, list)
        print(f"   Записей в лидерборде: {len(response3.data)}")
        
        # Ищем нашего пользователя в лидерборде
        user_in_leaderboard = False
        for entry in response3.data:
            if entry['username'] == 'player1':
                user_in_leaderboard = True
                print(f"   Найден player1 в лидерборде: {entry['score']} очков")
                # Проверяем, что записан максимальный счет (150, а не 50)
                self.assertEqual(entry['score'], 150)
                break
        
        self.assertTrue(user_in_leaderboard, "Игрок должен быть в лидерборде")
        
        # Шаг 4: Проверяем загрузку последней сессии
        response4 = self.client.get('/api/game/session/load/')
        print(f"4. Загружена последняя сессия: {response4.status_code}")
        self.assertEqual(response4.status_code, status.HTTP_200_OK)
        
        # Должна быть последняя сессия (завершенная, 150 очков)
        self.assertEqual(response4.data['score'], 150)
        self.assertEqual(response4.data['is_completed'], True)
        
        print("=== Цикл игры завершен успешно ===")
    
    def test_multiple_games_leaderboard_update(self):
        """Тест обновления лидерборда после нескольких игр"""
        print("\n=== Тест нескольких игр и лидерборда ===")
        
        # Играем несколько раз с разными счетами
        scores = [50, 200, 100, 300, 150]  # Максимальный должен быть 300
        
        for i, score in enumerate(scores):
            game_data = {
                'score': score,
                'difficulty': 'medium',
                'time_played': (i + 1) * 100,
                'is_completed': True,
            }
            
            response = self.client.post(
                '/api/game/session/save/',
                data=json.dumps(game_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            print(f"  Игра {i+1}: {score} очков")
        
        print(f"  Всего сыграно игр: {len(scores)}")
        
        # Проверяем количество сессий в БД
        sessions_count = GameSession.objects.filter(user=self.user1).count()
        self.assertEqual(sessions_count, len(scores))
        
        # Проверяем лидерборд
        response = self.client.get('/api/game/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Ищем максимальный счет
        max_score = max(scores)
        user_entry = None
        for entry in response.data:
            if entry['username'] == 'player1':
                user_entry = entry
                break
        
        self.assertIsNotNone(user_entry, "Игрок должен быть в лидерборде")
        print(f"  Максимальный счет в лидерборде: {user_entry['score']} (ожидается: {max_score})")
        self.assertEqual(user_entry['score'], max_score)
        
        # Проверяем, что в лидерборде только ОДНА запись на пользователя
        user_entries = [e for e in response.data if e['username'] == 'player1']
        self.assertEqual(len(user_entries), 1, "Должна быть только одна запись на пользователя")
        
        print("=== Тест нескольких игр завершен ===")
    
    def test_game_state_persistence(self):
        """Тест сохранения и загрузки состояния игры"""
        print("\n=== Тест сохранения состояния игры ===")
        
        # Создаем сложное состояние игры
        complex_game_state = {
            'maze': [
                [1, 0, 1, 0, 1],
                [0, 0, 1, 0, 0],
                [1, 0, 0, 0, 1],
                [0, 0, 1, 0, 0],
                [1, 0, 1, 0, 1]
            ],
            'player': {
                'x': 1.5,
                'y': 1.5,
                'color': '#FF0000'
            },
            'goal': {
                'x': 3.5,
                'y': 3.5
            },
            'easter_egg': {
                'x': 2.5,
                'y': 1.5,
                'found': False
            },
            'timer': 45.5,
            'score': 75
        }
        
        # Сохраняем с состоянием
        save_data = {
            'score': 75,
            'difficulty': 'hard',
            'time_played': 45,
            'is_completed': False,
            'game_state': complex_game_state
        }
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(save_data),
            content_type='application/json'
        )
        print(f"1. Сохранено состояние игры: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('game_state', response.data)
        
        # Проверяем, что состояние сохранено в БД
        session = GameSession.objects.filter(user=self.user1).first()
        self.assertIsNotNone(session.game_state)
        
        # Проверяем загрузку
        response = self.client.get('/api/game/session/load/')
        print(f"2. Загружено состояние игры: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем ключевые элементы состояния
        loaded_state = response.data.get('game_state', {})
        self.assertIn('maze', loaded_state)
        self.assertIn('player', loaded_state)
        self.assertEqual(len(loaded_state['maze']), 5)  # 5x5 лабиринт
        self.assertEqual(loaded_state['player']['color'], '#FF0000')
        
        print("=== Состояние игры сохранено и загружено успешно ===")
    
    def test_leaderboard_ranking(self):
        """Тест правильности ранжирования в лидерборде"""
        print("\n=== Тест ранжирования в лидерборде ===")
        
        # Создаем несколько пользователей с разными счетами
        users_scores = [
            ('rankuser1', 100),
            ('rankuser2', 300),
            ('rankuser3', 200),
            ('rankuser4', 400),
            ('rankuser5', 150),
        ]
        
        for username, score in users_scores:
            user = User.objects.create_user(username=username, password='pass123')
            
            # Сохраняем игру с максимальным счетом
            client = APIClient()
            client.force_authenticate(user=user)
            
            game_data = {
                'score': score,
                'difficulty': 'medium',
                'time_played': 100,
                'is_completed': True,
            }
            
            response = client.post(
                '/api/game/session/save/',
                data=json.dumps(game_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            print(f"  Создан {username}: {score} очков")
        
        # Получаем лидерборд (без авторизации - он публичный)
        self.client.force_authenticate(user=None)  # Снимаем авторизацию
        response = self.client.get('/api/game/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем порядок ранжирования (по убыванию счета)
        print("  Ранжирование:")
        prev_score = float('inf')  # Бесконечность
        for i, entry in enumerate(response.data):
            current_score = entry['score']
            print(f"    {i+1}. {entry['username']}: {current_score} очков")
            
            # Проверяем, что ранги идут по порядку
            self.assertEqual(entry['rank'], i + 1)
            
            # Проверяем, что счет не увеличивается (должен убывать или быть равен)
            self.assertLessEqual(current_score, prev_score)
            prev_score = current_score
        
        # Проверяем, что лучший игрок на первом месте
        self.assertEqual(response.data[0]['username'], 'rankuser4')  # 400 очков
        self.assertEqual(response.data[0]['score'], 400)
        
        print("=== Ранжирование работает корректно ===")
    
    def test_friends_comparison(self):
        """Тест сравнения результатов с друзьями"""
        print("\n=== Тест сравнения с друзьями ===")
        
        # Создаем друзей с разными счетами
        friends = [
            ('friend1', 250),
            ('friend2', 100),
            ('friend3', 350),
        ]
        
        # Сначала создаем основного пользователя с хорошим счетом
        main_user_score = 300
        game_data = {
            'score': main_user_score,
            'difficulty': 'hard',
            'time_played': 500,
            'is_completed': True,
        }
        
        response = self.client.post(
            '/api/game/session/save/',
            data=json.dumps(game_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        print(f"  Основной игрок: {main_user_score} очков")
        
        # Создаем друзей
        for friend_name, friend_score in friends:
            friend_user = User.objects.create_user(
                username=friend_name,
                password='pass123'
            )
            
            client = APIClient()
            client.force_authenticate(user=friend_user)
            
            game_data = {
                'score': friend_score,
                'difficulty': 'medium',
                'time_played': 300,
                'is_completed': True,
            }
            
            response = client.post(
                '/api/game/session/save/',
                data=json.dumps(game_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            print(f"  Друг {friend_name}: {friend_score} очков")
        
        # Получаем лидерборд
        response = self.client.get('/api/game/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Анализируем позиции
        positions = {}
        for entry in response.data:
            positions[entry['username']] = entry['rank']
        
        print("  Позиции в лидерборде:")
        for username, rank in sorted(positions.items(), key=lambda x: x[1]):
            print(f"    {rank}. {username}")
        
        # Основной игрок должен быть выше друзей с меньшим счетом
        self.assertLess(positions.get('player1', 100), positions.get('friend2', 0))
        
        # И ниже друзей с большим счетом
        self.assertGreater(positions.get('player1', 0), positions.get('friend3', 100))
        
        print("=== Сравнение с друзьями работает корректно ===")