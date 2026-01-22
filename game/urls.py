from django.urls import path
from . import views
from .views import SendFriendRequestView, AcceptFriendRequestView, RejectFriendRequestView, FriendsListView

urlpatterns = [
    path('session/save/', views.SaveGameSessionView.as_view()),
    path('session/load/', views.LoadLastSessionView.as_view()),
    path('leaderboard/', views.LeaderboardView.as_view()),
    path('achievements/', views.UserAchievementsView.as_view()),
    path('friends/send/', views.SendFriendRequestView.as_view(), name='send_friend_request'),
    path('friends/accept/', views.AcceptFriendRequestView.as_view(), name='accept_friend_request'),
    path('friends/reject/', views.RejectFriendRequestView.as_view(), name='reject_friend_request'),
    path('friends/remove/', views.RemoveFriendView.as_view(), name='remove_friend'),
    path('friends/', views.FriendsListView.as_view(), name='friends_list'),
]