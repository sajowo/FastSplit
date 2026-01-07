from django.contrib import admin
from django.urls import path
from EsSplit import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Podstawowe strony
    path('main/', views.index, name='index'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.register, name='signup'),

    # Axes lockout (strona blokady logowania)
    path('lockout/', views.lockout_view, name='lockout'),
    
    # Znajomi i Wyszukiwanie
    path('search_user/', views.search_user, name='search_user'),
    path('invite_user/', views.invite_user, name='invite_user'),
    path('request/<int:request_id>/<str:action>/', views.handle_friend_request, name='handle_request'), # <-- TO BYŁO POTRZEBNE
    
    # Grupy (To naprawi Twój obecny błąd)
    path('create_group/', views.create_group, name='create_group'), # <-- TEGO BRAKOWAŁO

    # Rachunki
    path('create_spill/', views.create_spill, name='create_spill'),
    path('update_bill/<int:bill_id>/<str:new_status>/', views.update_bill_status, name='update_bill'),
]