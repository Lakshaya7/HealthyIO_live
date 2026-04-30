from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Main Pages
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tips/', views.tips, name='tips'),
    path('profile/', views.profile, name='profile'),
    
    # Auth System
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Log Management & Export
    path('add-log/', views.add_log, name='add_log'),
    path('edit-log/<int:log_id>/', views.edit_log, name='edit_log'),
    path('delete-log/<int:log_id>/', views.delete_log, name='delete_log'),
    path('download-report/', views.download_report, name='download_report'), # <-- NEW PDF URL
    
    # AI Tools & Games
    path('ai-coach/', views.ai_coach, name='ai_coach'),
    path('scripty-log/', views.scripty_log, name='scripty_log'),
    path('food-search/', views.food_search, name='food_search'),
    path('game/', views.game, name='game'),
    path('healy-chat/', views.healy_chat, name='healy_chat'),
]