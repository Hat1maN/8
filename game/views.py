from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Max
from django.db import models, IntegrityError
from django.contrib.auth.models import User
from .models import GameSession, LeaderboardEntry, UserAchievement, Friendship
from .serializers import GameSessionSerializer, LeaderboardSerializer, UserAchievementSerializer, FriendSerializer

class SaveGameSessionView(APIView):
    def post(self, request):
        data = request.data
        data['user'] = request.user.id
        
        serializer = GameSessionSerializer(data=data)
        if serializer.is_valid():
            session = serializer.save()
            
            # ОБНОВЛЯЕМ ЛИДЕРБОРД - ТОЛЬКО ЕСЛИ ИГРА ЗАВЕРШЕНА
            if data.get('is_completed', False):
                self.update_leaderboard(request.user)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update_leaderboard(self, user):
        """
        Обновляет лидерборд для пользователя.
        Гарантирует только ОДНУ запись на пользователя.
        """
        # 1. Находим ЛУЧШИЙ счет пользователя среди завершенных игр
        best_score = GameSession.objects.filter(
            user=user, 
            is_completed=True
        ).aggregate(Max('score'))['score__max'] or 0
        
        print(f"Обновление лидерборда для {user.username}: лучший счет = {best_score}")
        
        # 2. УДАЛЯЕМ ВСЕ старые записи этого пользователя
        deleted_count, _ = LeaderboardEntry.objects.filter(user=user).delete()
        print(f"Удалено старых записей: {deleted_count}")
        
        # 3. Создаем ТОЛЬКО ОДНУ новую запись (если есть счет)
        if best_score > 0:
            LeaderboardEntry.objects.create(
                user=user,
                score=best_score
            )
            print(f"Создана новая запись: {user.username} - {best_score} очков")
        
        # 4. ОБНОВЛЯЕМ ранги для всех пользователей
        self.update_all_ranks()
    
    def update_all_ranks(self):
        """
        Обновляет ранги для всех записей в лидерборде.
        """
        # Получаем все записи, отсортированные по счету (по убыванию)
        entries = LeaderboardEntry.objects.all().order_by('-score', 'date_achieved')
        
        current_rank = 1
        for entry in entries:
            entry.rank = current_rank
            entry.save()
            current_rank += 1
        
        print(f"Обновлены ранги для {entries.count()} записей")

class LoadLastSessionView(APIView):
    def get(self, request):
        session = GameSession.objects.filter(user=request.user).order_by('-created_at').first()
        if session:
            return Response(GameSessionSerializer(session).data)
        return Response({'message': 'Нет сохранений'})

class LeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # 1. ОЧИСТКА ДУБЛИКАТОВ (на всякий случай)
        self.clean_duplicates()
        
        # 2. ОБНОВЛЕНИЕ РАНГОВ
        self.update_ranks()
        
        # 3. ПОЛУЧЕНИЕ ДАННЫХ
        entries = LeaderboardEntry.objects.all().order_by('-score', 'date_achieved')[:50]
        
        # 4. СЕРИАЛИЗАЦИЯ
        serializer = LeaderboardSerializer(entries, many=True)
        
        print(f"Отправлено {len(entries)} записей в лидерборд")
        return Response(serializer.data)
    
    def clean_duplicates(self):
        """
        Удаляет дубликаты: оставляет только запись с максимальным счетом для каждого пользователя
        """
        from django.db.models import Max
        
        # Находим ID пользователей с дубликатами
        duplicate_users = LeaderboardEntry.objects.values('user').annotate(
            count=models.Count('id'),
            max_score=Max('score')
        ).filter(count__gt=1)
        
        for dup in duplicate_users:
            user_id = dup['user']
            max_score = dup['max_score']
            
            # Удаляем ВСЕ записи пользователя
            LeaderboardEntry.objects.filter(user_id=user_id).delete()
            
            # Создаем ОДНУ запись с максимальным счетом
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            LeaderboardEntry.objects.create(
                user=user,
                score=max_score
            )
            
            print(f"Очищен дубликат для {user.username}: оставлен счет {max_score}")
    
    def update_ranks(self):
        """
        Присваивает правильные ранги
        """
        entries = LeaderboardEntry.objects.all().order_by('-score', 'date_achieved')
        
        rank = 1
        for entry in entries:
            entry.rank = rank
            entry.save(update_fields=['rank'])
            rank += 1

class UserAchievementsView(APIView):
    def get(self, request):
        achievements = UserAchievement.objects.filter(user=request.user)
        serializer = UserAchievementSerializer(achievements, many=True)
        return Response(serializer.data)

class SendFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите username'}, status=status.HTTP_400_BAD_REQUEST)
        if username == request.user.username:
            return Response({'error': 'Нельзя добавить себя'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            to_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Удаляем rejected, если была
        Friendship.objects.filter(from_user=request.user, to_user=to_user, status='rejected').delete()
        
        # Проверяем существующие
        try:
            existing = Friendship.objects.get(from_user=request.user, to_user=to_user)
            if existing.status == 'pending':
                return Response({'error': 'Заявка уже отправлена'}, status=status.HTTP_400_BAD_REQUEST)
            if existing.status == 'accepted':
                return Response({'error': 'Вы уже друзья'}, status=status.HTTP_400_BAD_REQUEST)
        except Friendship.DoesNotExist:
            pass
        
        Friendship.objects.create(from_user=request.user, to_user=to_user, status='pending')
        return Response({'message': 'Заявка отправлена'}, status=status.HTTP_200_OK)

class AcceptFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите username'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from_user = User.objects.get(username=username)
            friendship = Friendship.objects.get(from_user=from_user, to_user=request.user, status='pending')
            friendship.status = 'accepted'
            friendship.save()
            # Симметричная дружба
            Friendship.objects.get_or_create(from_user=request.user, to_user=from_user, defaults={'status': 'accepted'})
            return Response({'message': 'Заявка принята'}, status=status.HTTP_200_OK)
        except Friendship.DoesNotExist:
            return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)

class RejectFriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите username'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from_user = User.objects.get(username=username)
            friendship = Friendship.objects.get(from_user=from_user, to_user=request.user, status='pending')
            friendship.delete()  # Удаляем запись полностью
            return Response({'message': 'Заявка отклонена'}, status=status.HTTP_200_OK)
        except Friendship.DoesNotExist:
            return Response({'error': 'Заявка не найдена'}, status=status.HTTP_404_NOT_FOUND)

class RemoveFriendView(APIView):  # Добавлен новый класс
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите username'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Находим друга
            friend_user = User.objects.get(username=username)
            
            # Удаляем обе связи (симметрично)
            Friendship.objects.filter(
                from_user=request.user, 
                to_user=friend_user, 
                status='accepted'
            ).delete()
            
            Friendship.objects.filter(
                from_user=friend_user, 
                to_user=request.user, 
                status='accepted'
            ).delete()
            
            return Response({'message': 'Друг удален'}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': 'Ошибка удаления'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FriendsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Входящие заявки
        incoming = Friendship.objects.filter(
            to_user=request.user, 
            status='pending'
        ).values_list('from_user__username', flat=True)
        incoming = list(incoming)
        
        # Друзья (accepted) - находим всех пользователей, с которыми есть дружба
        # Ищем где пользователь является from_user
        friendships_as_from = Friendship.objects.filter(
            from_user=request.user, 
            status='accepted'
        ).select_related('to_user')
        
        # Ищем где пользователь является to_user
        friendships_as_to = Friendship.objects.filter(
            to_user=request.user, 
            status='accepted'
        ).select_related('from_user')
        
        friend_set = set()  # Используем set для уникальности
        friend_list = []
        
        # Обрабатываем дружбу, где пользователь является from_user
        for friendship in friendships_as_from:
            friend_user = friendship.to_user
            if friend_user.id not in friend_set:
                friend_set.add(friend_user.id)
                max_score = GameSession.objects.filter(
                    user=friend_user, 
                    is_completed=True
                ).aggregate(max_score=models.Max('score'))['max_score'] or 0
                rank = LeaderboardEntry.objects.filter(score__gt=max_score).count() + 1
                friend_list.append({
                    'username': friend_user.username,
                    'max_score': max_score,
                    'rank': rank
                })
        
        # Обрабатываем дружбу, где пользователь является to_user
        for friendship in friendships_as_to:
            friend_user = friendship.from_user
            if friend_user.id not in friend_set:
                friend_set.add(friend_user.id)
                max_score = GameSession.objects.filter(
                    user=friend_user, 
                    is_completed=True
                ).aggregate(max_score=models.Max('score'))['max_score'] or 0
                rank = LeaderboardEntry.objects.filter(score__gt=max_score).count() + 1
                friend_list.append({
                    'username': friend_user.username,
                    'max_score': max_score,
                    'rank': rank
                })
        
        return Response({
            'incoming_requests': incoming,
            'friends': friend_list
        })