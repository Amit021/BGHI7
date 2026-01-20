from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name="landing"),
    path('login/', views.loginPage, name = "login"),
    path('logout/', views.logoutUser, name = "logout"),
    path('register/', views.registerPage, name = "register"),
    path('home/', views.home, name="home"),
    path('room/<str:pk>/', views.room, name ="room"),
    path('room/<str:pk>/vote/', views.voteRoom, name='vote-room'),
    path('profile/<str:pk>/', views.userProfile, name="user-profile"),
    path('create-room/', views.createRoom, name = "create-room"),
    path('update-room/<str:pk>/', views.updateRoom, name = "update-room"),
    path('delete-room/<str:pk>/', views.deleteRoom, name = "delete-room"),
    path('delete-message/<str:pk>/', views.deleteMessage, name = "delete-message"),
    path('update-user/', views.updateUser, name = "update-user"),
    path('demo/subscribe/', views.demoSubscribe, name='demo-subscribe'),
    path('demo/unsubscribe/', views.demoUnsubscribe, name='demo-unsubscribe'),
    # Messaging
    path('messages/', views.inbox, name='inbox'),
    path('messages/new/', views.start_conversation, name='start-conversation'),
    path('messages/<str:pk>/', views.conversation, name='conversation'),
    # Mentorship
    path('mentorship/profile/', views.mentorship_profile, name='mentorship-profile'),
    path('mentorship/profile/delete/', views.delete_mentorship_profile, name='delete-mentorship-profile'),
]