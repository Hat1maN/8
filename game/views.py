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
            # Обновляем лидерборд
            best_score = GameSession.objects.filter(user=request.user, is_completed=True).aggregate(Max('score'))['score__max'] or 0
            entry, created = LeaderboardEntry.objects.update_or_create(
                user=request.user,
                defaults={'score': best_score}
            )
            # Здесь можно добавить логику достижений
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoadLastSessionView(APIView):
    def get(self, request):
        session = GameSession.objects.filter(user=request.user).order_by('-created_at').first()
        if session:
            return Response(GameSessionSerializer(session).data)
        return Response({'message': 'Нет сохранений'})

class LeaderboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        entries = LeaderboardEntry.objects.all().order_by('-score')[:50]
        for i, entry in enumerate(entries):
            entry.rank = i + 1
            entry.save()
        serializer = LeaderboardSerializer(entries, many=True)
        return Response(serializer.data)

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