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
from django.shortcuts import get_object_or_404
from django.db.models import Q

logger = logging.getLogger(__name__)

# --- POPRAWIONY INDEX (USUNĄŁEM DUPLIKAT Z DOŁU PLIKU) ---
def index(request):
    if request.user.is_authenticated:
        # Pobieramy znajomych (Tu na razie bez zmian - widzisz kogo dodałeś)
        friends = Friend.objects.filter(user=request.user)
        
        # POPRAWKA: Pobieramy rachunki gdzie jesteś twórcą LUB uczestnikiem
        # distinct() jest ważne, żeby nie pokazało tego samego rachunku 2 razy
        participated_bills = Bill.objects.filter(
            Q(creator=request.user) | Q(participants=request.user)
        ).distinct().order_by('-date')[:5]
        
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
                user_to_add = User.objects.get(username=username)
                
                if user_to_add != request.user:
                    # KROK 1: Sprawdź/Stwórz relację: Ty -> On
                    # get_or_create zwraca krotkę (obiekt, czy_utworzono)
                    obj, created = Friend.objects.get_or_create(
                        user=request.user, 
                        friend_account=user_to_add
                    )
                    
                    # KROK 2: ZAWSZE sprawdzaj/twórz relację: On -> Ty (Naprawa wzajemności)
                    Friend.objects.get_or_create(
                        user=user_to_add, 
                        friend_account=request.user
                    )

                    if created:
                        messages.success(request, f'Dodano znajomego: {user_to_add.username}')
                    else:
                        # Jeśli relacja już istniała, ale np. brakowało zwrotnej, to teraz jest naprawiona
                        messages.info(request, f"Zaktualizowano relację z {user_to_add.username} (teraz widzi Cię na liście).")
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

def update_bill_status(request, bill_id, new_status):
    # 1. Pobieramy rachunek (lub błąd 404 jak nie istnieje)
    bill = get_object_or_404(Bill, id=bill_id)
    
    # 2. Zabezpieczenie: Kto może zmieniać status?
    is_creator = request.user == bill.creator
    is_participant = request.user in bill.participants.all()
    
    if not (is_creator or is_participant):
        messages.error(request, "Nie masz uprawnień do tego rachunku.")
        return redirect('index')

    # 3. Logika statusów
    if new_status == 'REJECTED':
        # Odrzucić może każdy uczestnik
        bill.status = Bill.Status.REJECTED
        bill.save()
        messages.info(request, "Rachunek został odrzucony.")
        
    elif new_status == 'PAID':
        # Sfinalizować może TYLKO twórca (bo to on dostaje kasę)
        if is_creator:
            bill.status = Bill.Status.PAID
            bill.save()
            messages.success(request, "Rachunek oznaczono jako sfinalizowany!")
        else:
            messages.error(request, "Tylko twórca rachunku może go sfinalizować.")

    elif new_status == 'PENDING':
         # Np. przywrócenie do życia
         bill.status = Bill.Status.PENDING
         bill.save()

    return redirect('index')