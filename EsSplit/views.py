from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .forms import RegisterForm, FriendForm  # Dodaj FriendForm do importu
from django.contrib.auth import get_user_model
import logging
import random
from .models import Person, Friend  # Importuj model Friend
from .models import Friend 


logger = logging.getLogger(__name__)


def index(request):
    if request.user.is_authenticated:
        # Dodaj print statement do debugowania
        print("Zalogowany użytkownik:", request.user)
        friends = Friend.objects.filter(user=request.user)  # Pobieramy znajomych dla aktualnego użytkownika
        print("Znajomi:", friends)
        # Wstawienie tutaj kodu, który wyświetla formularz do dodania znajomego
        return render(request, 'index.html', {'friends': friends})
    else:
        return redirect('login')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            user = None

        if user is not None and user.check_password(password):
            login(request, user)
            logger.info("Logowanie")
            return redirect(reverse('index'))  # Przekieruj na stronę główną
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password.'})
    else:
        return render(request, 'login.html')

def logout_view(request):
    logger.info("Wylogowywanie użytkownika")
    logout(request)
    return redirect('login') 

def generate_username(first_name, last_name):
    base_username = f"{first_name.lower()}{last_name.lower()}"
    username = base_username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{random.randint(1000, 9999)}"
    return username


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = generate_username(user.first_name, user.last_name)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Utwórz profil osoby i powiąż go z użytkownikiem
            person = Person(
                user=user, 
                first_name=user.first_name, 
                last_name=user.last_name 
            )
            person.save()

            login(request, user)
            return redirect('index')  # przekierowanie do strony głównej lub innej strony po rejestracji
    else:
        form = RegisterForm()
    return render(request, 'SignUp.html', {'form': form})

def add_friend(request):
    if request.method == 'POST':
        friend_name = request.POST.get('friend_name')
        if friend_name:
            new_friend = Friend(user=request.user, name=friend_name)
            new_friend.save()
            messages.success(request, f'Dodano znajomego: {friend_name}')
        else:
            messages.error(request, 'Proszę podać imię znajomego.')
    return redirect('index')

def search_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if username:
            try:
                user_to_add = User.objects.get(username=username)
                if user_to_add != request.user:
                    # Sprawdź, czy ten użytkownik już nie jest znajomym
                    if not request.user.friends.filter(name=user_to_add.username).exists():
                        new_friend = Friend(user=request.user, name=user_to_add.username)
                        new_friend.save()
                        messages.success(request, f'Dodano znajomego: {user_to_add.username}')
                    else:
                        messages.info(request, f"Użytkownik {user_to_add.username} jest już Twoim znajomym.")
                else:
                    messages.error(request, "Nie możesz dodać samego siebie do znajomych!")
            except User.DoesNotExist:
                messages.error(request, f"Użytkownik o nazwie '{username}' nie istnieje.")
        else:
            messages.error(request, "Proszę podać nazwę użytkownika.")
    return redirect('index') 