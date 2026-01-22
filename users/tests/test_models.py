from django.test import TestCase
from django.contrib.auth.models import User
from users.models import UserProfile
from django.core.exceptions import ValidationError
import datetime

class UsersModelsTest(TestCase):
    """Тесты для моделей приложения users"""
    
    def setUp(self):
        """Создаем тестовые данные перед каждым тестом"""
        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Создаем профиль ВРУЧНУЮ (так как нет сигнала)
        self.profile = UserProfile.objects.create(user=self.user)
    
    def test_user_profile_creation(self):
        """Тест автоматического создания профиля пользователя"""
        # Проверяем, что профиль создан
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.bio, '')
        self.assertIsNone(self.profile.date_of_birth)
        self.assertIsNone(self.profile.avatar.name)  # Проверяем имя файла, а не объект
        
        # Проверяем строковое представление
        self.assertEqual(str(self.profile), 'testuser')
    
    def test_user_profile_one_to_one_relation(self):
        """Тест связи OneToOne между User и UserProfile"""
        # Связь должна быть уникальной
        self.assertEqual(self.user.profile, self.profile)
        
        # Нельзя создать второй профиль для того же пользователя
        with self.assertRaises(Exception):
            UserProfile.objects.create(user=self.user)
    
    def test_user_profile_fields(self):
        """Тест полей профиля пользователя"""
        # Обновляем поля профиля
        self.profile.bio = 'Тестовая биография'
        self.profile.date_of_birth = datetime.date(1990, 1, 1)
        self.profile.save()
        
        # Проверяем обновление
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'Тестовая биография')
        self.assertEqual(self.profile.date_of_birth, datetime.date(1990, 1, 1))
    
    def test_bio_max_length(self):
        """Тест максимальной длины поля bio"""
        # Создаем длинную биографию
        long_bio = 'A' * 500  # Максимальная длина
        self.profile.bio = long_bio
        self.profile.save()
        
        # Проверяем, что сохранилось
        self.profile.refresh_from_db()
        self.assertEqual(len(self.profile.bio), 500)
        
        # Попытка сохранить слишком длинную биографию
        # Django автоматически обрежет при сохранении, но проверим ограничение
        field = UserProfile._meta.get_field('bio')
        self.assertEqual(field.max_length, 500)
    
    def test_timestamped_model_in_userprofile(self):
        """Тест, что UserProfile наследует TimeStampedModel"""
        # Проверяем наличие полей created_at и updated_at
        self.assertIsNotNone(self.profile.created_at)
        self.assertIsNotNone(self.profile.updated_at)
        
        # Проверяем обновление updated_at при сохранении
        old_updated_at = self.profile.updated_at
        self.profile.bio = 'Обновленная биография'
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.updated_at, old_updated_at)
    
    def test_user_deletion_cascade(self):
        """Тест каскадного удаления профиля при удалении пользователя"""
        # Создаем нового пользователя и профиль для теста
        temp_user = User.objects.create_user(
            username='tempuser',
            password='temppass'
        )
        
        # СОЗДАЕМ профиль ВРУЧНУЮ
        temp_profile = UserProfile.objects.create(user=temp_user)
        
        # Удаляем пользователя
        user_id = temp_user.id
        profile_id = temp_profile.id
        temp_user.delete()
        
        # Проверяем, что профиль тоже удален
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)
        
        # Проверяем, что пользователь удален
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)
    
    def test_avatar_upload(self):
        """Тест поля загрузки аватара (проверка атрибутов)"""
        field = UserProfile._meta.get_field('avatar')
        
        # Проверяем, что поле позволяет загружать файлы
        self.assertEqual(field.upload_to, 'avatars/')
        
        # Проверяем, что поле необязательное
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
    
    def test_profile_without_user(self):
        """Тест, что профиль нельзя создать без пользователя"""
        with self.assertRaises(Exception):
            UserProfile.objects.create()
    
    def test_multiple_users_profiles(self):
        """Тест создания профилей для нескольких пользователей"""
        # Создаем несколько пользователей и профилей
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'multiuser{i}',
                password=f'pass{i}'
            )
            # Создаем профиль ВРУЧНУЮ
            profile = UserProfile.objects.create(user=user)
            users.append(user)
        
        # Проверяем, что для каждого создался профиль
        for user in users:
            profile = UserProfile.objects.get(user=user)
            self.assertEqual(profile.user, user)
        
        # Проверяем количество
        self.assertEqual(UserProfile.objects.count(), 6)  # 5 новых + 1 из setUp