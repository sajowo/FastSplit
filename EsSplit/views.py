from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info("Logowanie")
            return redirect(reverse('index'))  # Przekieruj na stronę główną
        else:
            # Wyświetl komunikat o błędnych danych logowania
            return render(request, 'login.html', {'error': 'Invalid username or password.'})
    else:
        return render(request, 'login.html')

def logout_view(request):
    logger.info("Wylogowywanie użytkownika")
    logout(request)
    return redirect('login')  # Przekieruj na stronę logowania
