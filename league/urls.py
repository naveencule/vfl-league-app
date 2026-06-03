from django.urls import path
from . import views

urlpatterns = [
    # Client Facing
    path('', views.standings_table, name='standings'),
    path('scorers/', views.top_scorers, name='top_scorers'),
    path('clean-sheets/', views.clean_sheets_leaderboard, name='clean_sheets'),
    path('discipline/', views.disciplinary_board, name='disciplinary_board'),
    
    # --- NEW Custom Workspace Admin Auth Gates ---
    path('dashboard/login/', views.custom_admin_login, name='custom_admin_login'),
    path('dashboard/logout/', views.custom_admin_logout, name='custom_admin_logout'),
    
    # Your Existing Custom Workspace Admin Routes (Unchanged)
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/match/<int:match_id>/manage/', views.manage_match_events, name='manage_match_events'),
    path('dashboard/rosters/', views.manage_rosters, name='manage_rosters'),
    path('dashboard/team/<int:team_id>/edit/', views.edit_team, name='edit_team'),
    path('dashboard/player/<int:player_id>/edit/', views.edit_player, name='edit_player'),
]