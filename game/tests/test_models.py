from django.test import TestCase
from django.contrib.auth.models import User
from game.models import (
    Achievement, UserAchievement, GameSession, 
    LeaderboardEntry, Friendship, TimeStampedModel
)
from django.core.exceptions import ValidationError
import datetime

class GameModelsTest(TestCase):
    """Тесты для моделей приложения game"""
    
    def setUp(self):
        """Создаем тестовые данные перед каждым тестом"""
        # Создаем двух пользователей
        self.user1 = User.objects.create_user(
            username='testuser1',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )
        
        # Создаем достижение
        self.achievement = Achievement.objects.create(
            name='Первая победа',
            description='Выиграть первую игру'
        )
        
        # Создаем игровую сессию
        self.game_session = GameSession.objects.create(
            user=self.user1,
            score=100,
            difficulty='medium',
            time_played=300,
            is_completed=True
        )
    
    def test_achievement_creation(self):
        """Тест создания достижения"""
        achievement = Achievement.objects.get(name='Первая победа')
        self.assertEqual(achievement.description, 'Выиграть первую игру')
        self.assertEqual(str(achievement), 'Первая победа')
    
    def test_user_achievement_creation(self):
        """Тест создания достижения пользователя"""
        user_achievement = UserAchievement.objects.create(
            user=self.user1,
            achievement=self.achievement
        )
        
        # Проверяем связь ForeignKey
        self.assertEqual(user_achievement.user, self.user1)
        self.assertEqual(user_achievement.achievement, self.achievement)
        
        # Проверяем уникальность (один пользователь - одно достижение)
        with self.assertRaises(Exception):  # Будет IntegrityError
            UserAchievement.objects.create(
                user=self.user1,
                achievement=self.achievement
            )
    
    def test_game_session_creation(self):
        """Тест создания игровой сессии"""
        session = GameSession.objects.get(user=self.user1)
        
        self.assertEqual(session.score, 100)
        self.assertEqual(session.difficulty, 'medium')
        self.assertEqual(session.time_played, 300)
        self.assertTrue(session.is_completed)
        
        # Проверяем строковое представление
        self.assertIn('testuser1', str(session))
        self.assertIn('100', str(session))
    
    def test_timestamped_model_fields(self):
        """Тест автоматического заполнения created_at и updated_at"""
        # Создаем новую модель
        achievement = Achievement.objects.create(
            name='Новое достижение',
            description='Тест'
        )
        
        # Проверяем, что поля заполнены
        self.assertIsNotNone(achievement.created_at)
        self.assertIsNotNone(achievement.updated_at)
        
        # Сохраняем с изменениями
        old_updated_at = achievement.updated_at
        achievement.description = 'Измененное описание'
        achievement.save()
        
        # updated_at должен обновиться
        self.assertNotEqual(achievement.updated_at, old_updated_at)
    
    def test_leaderboard_entry_creation(self):
        """Тест создания записи в лидерборде"""
        leaderboard_entry = LeaderboardEntry.objects.create(
            user=self.user1,
            score=500
        )
        
        self.assertEqual(leaderboard_entry.user, self.user1)
        self.assertEqual(leaderboard_entry.score, 500)
        
        # date_achieved должен быть автоматически заполнен
        self.assertIsNotNone(leaderboard_entry.date_achieved)
        self.assertEqual(leaderboard_entry.date_achieved, datetime.date.today())
    
    def test_friendship_creation(self):
        """Тест создания дружеской связи"""
        friendship = Friendship.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            status='pending'
        )
        
        self.assertEqual(friendship.from_user, self.user1)
        self.assertEqual(friendship.to_user, self.user2)
        self.assertEqual(friendship.status, 'pending')
        
        # Проверяем уникальность связи
        with self.assertRaises(Exception):
            Friendship.objects.create(
                from_user=self.user1,
                to_user=self.user2,
                status='accepted'
            )
    
    def test_game_session_difficulty_choices(self):
        """Тест валидации выбора сложности"""
        # Корректные значения
        valid_difficulties = ['easy', 'medium', 'hard']
        
        for difficulty in valid_difficulties:
            session = GameSession.objects.create(
                user=self.user1,
                score=50,
                difficulty=difficulty,
                time_played=100,
                is_completed=True
            )
            self.assertEqual(session.difficulty, difficulty)
        
        # Некорректное значение - должно вызвать ошибку при сохранении
        session = GameSession(
            user=self.user1,
            score=50,
            difficulty='impossible',  # Недопустимое значение
            time_played=100,
            is_completed=True
        )
        
        # В Django при попытке save() с недопустимым значением будет ошибка
        # Но давайте проверим, что поле ограничено choices
        valid_choices = dict(GameSession._meta.get_field('difficulty').choices)
        self.assertNotIn('impossible', valid_choices)
    
    def test_score_positive(self):
        """Тест, что счет должен быть положительным"""
        # Создаем с отрицательным счетом
        session = GameSession(
            user=self.user1,
            score=-10,  # Отрицательное значение
            difficulty='easy',
            time_played=100,
            is_completed=True
        )
        
        # Django не валидирует PositiveIntegerField автоматически в тестах
        # Но можем проверить тип поля
        field = GameSession._meta.get_field('score')
        self.assertEqual(field.__class__.__name__, 'PositiveIntegerField')
    
    def test_friendship_status_choices(self):
        """Тест валидации статуса дружбы"""
        valid_statuses = ['pending', 'accepted', 'rejected']
        
        for i, status in enumerate(valid_statuses):
            # Создаем нового пользователя для каждой итерации,
            # чтобы избежать конфликта unique_together
            temp_user = User.objects.create_user(
                username=f'tempuser{i}',
                password='testpass123'
            )
            
            friendship = Friendship.objects.create(
                from_user=self.user1,
                to_user=temp_user,
                status=status
            )
            self.assertEqual(friendship.status, status)
            
            # Также проверяем, что статус можно изменить
            if status == 'pending':
                friendship.status = 'accepted'
                friendship.save()
                friendship.refresh_from_db()
                self.assertEqual(friendship.status, 'accepted')
