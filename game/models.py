from django.db import models
from django.contrib.auth.models import User

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Achievement(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(upload_to='achievements/', null=True, blank=True)

    def __str__(self):
        return self.name

class UserAchievement(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'achievement')

class GameSession(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    score = models.PositiveIntegerField()
    difficulty = models.CharField(max_length=20, choices=[('easy', 'Легко'), ('medium', 'Нормально'), ('hard', 'Тяжело')])
    time_played = models.PositiveIntegerField(help_text="В секундах")
    is_completed = models.BooleanField(default=True)
    game_state = models.JSONField(null=True, blank=True)  # Для сохранения прогресса

    def __str__(self):
        return f"{self.user.username} - {self.score} очков"

class LeaderboardEntry(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveIntegerField()
    rank = models.PositiveIntegerField(null=True, blank=True)
    date_achieved = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.score}"

# Система друзей
class Friendship(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_received')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} ({self.status})"