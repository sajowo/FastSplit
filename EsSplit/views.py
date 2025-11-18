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

# --- POPRAWIONY INDEX (USUNĄŁEM DUPLIKAT Z DOŁU PLIKU) ---
def index(request):
    if request.user.is_authenticated:
        print("Zalogowany użytkownik:", request.user)
        friends = Friend.objects.filter(user=request.user)
        # Scaliłem logikę: pobiera ostatnie 5 rachunków (lepiej widzieć więcej niż 1 czy 2)
        participated_bills = Bill.objects.filter(creator_id=request.user.id).order_by('-date')[:5]
        
        context = {
            'friends': friends,
            'participated_bills': participated_bills
        }
        return render(request, 'index.html', context)
    else:
        return redirect('login')

# --- NAPRAWIONE LOGOWANIE ---
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
            logger.info("Logowanie udane")
            return redirect(reverse('index'))
        else:
            # ZMIANA: Zamiast context={'error': ...}, używamy messages
            messages.error(request, 'Nieprawidłowy email lub hasło.')
            return render(request, 'login.html')
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
            messages.success(request, 'Konto zostało utworzone pomyślnie!')
            return redirect('index')
        else:
            # Tutaj też warto dodać komunikaty o błędach formularza
            messages.error(request, 'Błąd rejestracji. Sprawdź poprawność danych.')
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
                # 1. Szukamy prawdziwego użytkownika
                user_to_add = User.objects.get(username=username)
                
                if user_to_add != request.user:
                    # 2. Sprawdzamy czy relacja już istnieje (teraz po ID, a nie po nazwie)
                    if not Friend.objects.filter(user=request.user, friend_account=user_to_add).exists():
                        # 3. Tworzymy relację
                        Friend.objects.create(user=request.user, friend_account=user_to_add)
                        messages.success(request, f'Dodano znajomego: {user_to_add.username}')
                    else:
                        messages.info(request, f"Użytkownik {user_to_add.username} jest już Twoim znajomym.")
                else:
                    messages.error(request, "Nie możesz dodać samego siebie!")
            except User.DoesNotExist:
                messages.error(request, f"Użytkownik '{username}' nie istnieje.")
        else:
            messages.error(request, "Podaj nazwę użytkownika.")
    return redirect('index')

def create_spill(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        tip = request.POST.get('tip')
        # JS wyśle nam teraz listę ID (np. ['1', '4']), a nie nazwy
        friend_ids = request.POST.getlist('friends[]') 

        # Walidacja (skrócona dla czytelności)
        if not amount: return JsonResponse({'message': 'Amount required'}, status=400)
        if not tip: tip = '0'

        try:
            total_amount = float(amount) * (1 + float(tip) / 100)
            
            bill = Bill.objects.create(
                creator=request.user,
                description='Rachunek', # Możesz dodać pole description do formularza w HTML
                amount=total_amount
            )
            
            # CZYSTA LOGIKA:
            for fid in friend_ids:
                # Teraz po prostu bierzemy ID. Jeśli JS wysłał ID, to musi być User.
                # Ewentualnie dodajemy try/except na wypadek gdyby user został usunięty w międzyczasie
                if fid:
                    bill.participants.add(int(fid))
            
            bill.save()
            return JsonResponse({'message': 'Success'})
            
        except ValueError:
             return JsonResponse({'message': 'Invalid data'}, status=400)
    
    return JsonResponse({'message': 'Bad method'}, status=400)