from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from import_export.formats import base_formats
from .models import Achievement, UserAchievement, GameSession, LeaderboardEntry, Friendship

# Ресурс для экспорта GameSession
class GameSessionResource(resources.ModelResource):
    class Meta:
        model = GameSession
        fields = ('id', 'user__username', 'score', 'difficulty', 'time_played', 
                 'is_completed', 'created_at')
        export_order = fields

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'unlocked_at')
    list_filter = ('achievement',)
    search_fields = ('user__username', 'achievement__name')

@admin.register(GameSession)
class GameSessionAdmin(ImportExportModelAdmin):
    resource_class = GameSessionResource
    list_display = ('user', 'score', 'difficulty', 'time_played', 'is_completed', 'created_at')
    list_filter = ('difficulty', 'is_completed')
    search_fields = ('user__username',)
    
    def get_export_formats(self):
        # Включаем XLSX формат
        formats = (
            base_formats.XLSX,
            base_formats.CSV,
            base_formats.JSON,
            base_formats.HTML,
        )
        return [f for f in formats if f().can_export()]

@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'rank', 'date_achieved')
    ordering = ('-score',)
    search_fields = ('user__username',)

@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('from_user__username', 'to_user__username')
    ordering = ('-created_at',)