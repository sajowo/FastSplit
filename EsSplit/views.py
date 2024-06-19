from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .forms import RegisterForm, FriendForm
from django.contrib.auth import get_user_model
import logging
import random
from .models import Person, Friend, Bill
from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)

def index(request):
    if request.user.is_authenticated:
        print("Zalogowany użytkownik:", request.user)
        friends = Friend.objects.filter(user=request.user)
        print("Znajomi:", friends)
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
            return redirect(reverse('index'))
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

            person = Person(
                user=user, 
                first_name=user.first_name, 
                last_name=user.last_name 
            )
            person.save()

            login(request, user)
            return redirect('index')
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

def create_spill(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        tip = request.POST.get('tip')
        friends = request.POST.getlist('friends[]')
        
        if not amount or not tip or not friends:
            return JsonResponse({'status': 'error', 'message': 'Wszystkie pola są wymagane'})

        try:
            total_amount = float(amount) + (float(amount) * (float(tip) / 100))
            description = f'Spill for friends: {", ".join(friends)}'
            Bill.objects.create(
                amount=total_amount,
                description=description,
                creator_id=request.user.id,
                date=timezone.now()
            )
            return JsonResponse({'status': 'success'})
        except ValueError as e:
            logger.error(f"Błąd przy przetwarzaniu wartości: {e}")
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowe dane wejściowe'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda'})

def index(request):
    if request.user.is_authenticated:
        participated_bills = Bill.objects.filter(creator_id=request.user.id)
        friends = Friend.objects.filter(user=request.user)
        context = {
            'participated_bills': participated_bills,
            'friends': friends
        }
        return render(request, 'index.html', context)
    else:
        return redirect('login')
