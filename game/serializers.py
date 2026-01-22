from rest_framework import serializers
from .models import GameSession, LeaderboardEntry, UserAchievement, Friendship
from django.contrib.auth.models import User

class GameSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = '__all__'

class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')

    class Meta:
        model = LeaderboardEntry
        fields = ('username', 'score', 'rank', 'date_achieved')

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_name = serializers.CharField(source='achievement.name')

    class Meta:
        model = UserAchievement
        fields = ('achievement_name', 'unlocked_at')

class FriendSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='to_user.username')

    class Meta:
        model = Friendship
        fields = ('username', 'accepted')