from django.contrib import admin
from django.urls import path, include

from EsSplit import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('add_friend/', views.add_friend, name='add_friend'),
    path('search_user/', views.search_user, name='search_user'),  # Dodanie nowej ścieżki
    path('create_spill/', views.create_spill, name='create_spill'),
]