from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from EsSplit import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Podstawowe strony
    path('main/', views.index, name='index'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.register, name='signup'),

    # Strony informacyjne
    path('faq/', views.faq_view, name='faq'),
    path('o-nas/', views.about_view, name='about'),
    path('regulamin/', views.terms_view, name='terms'),

    # Axes lockout (strona blokady logowania)
    path('lockout/', views.lockout_view, name='lockout'),
    
    # 2FA (weryfikacja dwuetapowa)
    path('2fa/setup/', views.setup_2fa_view, name='setup_2fa'),
    path('2fa/verify/', views.verify_2fa_view, name='verify_2fa'),
    path('2fa/disable/', views.disable_2fa_view, name='disable_2fa'),
    
    # Ustawienia profilu
    path('settings/', views.settings_view, name='settings'),
    
    # Znajomi i Wyszukiwanie
    path('search_user/', views.search_user, name='search_user'),
    path('invite_user/', views.invite_user, name='invite_user'),
    path('request/<int:request_id>/<str:action>/', views.handle_friend_request, name='handle_request'),
    path('friends/remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    
    # Grupy
    path('create_group/', views.create_group, name='create_group'),

    # Rachunki
    path('create_spill/', views.create_spill, name='create_spill'),
    path('update_bill/<int:bill_id>/<str:new_status>/', views.update_bill_status, name='update_bill'),

    # Powiadomienia o rachunkach (akceptacja udziału)
    path('bill/<int:bill_id>/accept/', views.accept_bill_share, name='accept_bill_share'),
    path('bill/<int:bill_id>/reject/', views.reject_bill_share, name='reject_bill_share'),
    path('bill/<int:bill_id>/pay/', views.pay_bill_share, name='pay_bill_share'),
    path('notifications/pending-bills/', views.get_pending_bill_notifications, name='pending_bill_notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)