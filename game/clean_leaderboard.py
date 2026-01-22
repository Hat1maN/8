from django.core.management.base import BaseCommand
from game.models import LeaderboardEntry, GameSession
from django.db.models import Max
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Очищает лидерборд от дубликатов и восстанавливает правильные данные'

    def handle(self, *args, **options):
        self.stdout.write("Очистка лидерборда...")
        
        # 1. Удаляем ВСЕ записи лидерборда
        count, _ = LeaderboardEntry.objects.all().delete()
        self.stdout.write(f"Удалено {count} старых записей")
        
        # 2. Для каждого пользователя находим максимальный счет
        users_with_scores = GameSession.objects.filter(
            is_completed=True
        ).values('user').annotate(
            max_score=Max('score')
        ).filter(max_score__gt=0)
        
        # 3. Создаем новые записи
        created_count = 0
        for item in users_with_scores:
            user = User.objects.get(id=item['user'])
            LeaderboardEntry.objects.create(
                user=user,
                score=item['max_score']
            )
            created_count += 1
        
        self.stdout.write(f"Создано {created_count} уникальных записей")
        self.stdout.write(self.style.SUCCESS('Лидерборд успешно очищен!'))