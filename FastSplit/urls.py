from django.contrib import admin
from django.urls import path
from EsSplit import views  # Upewnij się, że importujesz widoki z odpowiedniej aplikacji
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('main/', views.index, name='index'),  # Ścieżka dla strony głównej
    path('', views.login_view, name='login'),  # Ścieżka dla strony logowania, używając widoku login_view
    path('logout/', views.logout_view, name='logout'),  # Ścieżka dla wylogowywania
    path('signup/', views.register, name='signup'),  # Ścieżka dla rejestracji
    path('search_user/', views.search_user, name='search_user'),  # Dodanie nowej ścieżki
    path('create_spill/', views.create_spill, name='create_spill'),
    path('update_bill/<int:bill_id>/<str:new_status>/', views.update_bill_status, name='update_bill'),
]
