from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth import get_user_model
import logging
import random
import json  # <--- 1. NOWY IMPORT (Niezbędny do odczytania danych z JS)
from django.http import JsonResponse
from django.db.models import Q 
# 2. DODAJ BillShare do importów!
from .models import Person, Friend, Bill, FriendRequest, Group, BillShare 

logger = logging.getLogger(__name__)

# --- WIDOK GŁÓWNY (DASHBOARD) ---
def index(request):
    if request.user.is_authenticated:
        friends = Friend.objects.filter(user=request.user)
        friend_requests = FriendRequest.objects.filter(to_user=request.user)
        my_groups = Group.objects.filter(creator=request.user)

        participated_bills = Bill.objects.filter(
            Q(creator=request.user) | Q(participants=request.user)
        ).distinct().order_by('-date')[:5]
        
        # Logika wyświetlania kwot (To miałeś dobrze, ale zostawiam dla pewności)
        for bill in participated_bills:
            if request.user == bill.creator:
                # 1. Główny tekst
                bill.display_amount = f"{bill.amount} PLN (Całość)"
                
                # 2. NOWOŚĆ: Doklejamy listę dłużników, żeby wyświetlić ją w HTML
                # Pobieramy wszystkich, którzy mają coś do oddania (>0)
                bill.debtors_list = bill.shares.filter(amount_owed__gt=0)
                
            else:
                # Uczestnik widzi tylko swoje
                try:
                    share = bill.shares.get(user=request.user)
                    bill.display_amount = f"{share.amount_owed} PLN (Twój udział)"
                except:
                    bill.display_amount = "0.00 PLN"
                
                # Uczestnik nie potrzebuje pełnej listy dłużników
                bill.debtors_list = None

        context = {
            'friends': friends,
            'friend_requests': friend_requests,
            'my_groups': my_groups,
            'participated_bills': participated_bills
        }
        return render(request, 'index.html', context)
    else:
        return redirect('login')

# --- LOGOWANIE I REJESTRACJA (BEZ ZMIAN) ---
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
            messages.error(request, 'Nieprawidłowy email lub hasło.')
            return render(request, 'login.html')
    else:
        return render(request, 'login.html')

def logout_view(request):
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

            person = Person(user=user, first_name=user.first_name, last_name=user.last_name)
            person.save()

            login(request, user)
            messages.success(request, 'Konto utworzone!')
            return redirect('index')
        else:
            messages.error(request, 'Błąd rejestracji. Sprawdź dane.')
    else:
        form = RegisterForm()
    return render(request, 'SignUp.html', {'form': form})

# --- WYSZUKIWANIE I ZAPROSZENIA (BEZ ZMIAN) ---
def search_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if username:
            try:
                target_user = User.objects.get(username=username)
                
                if target_user == request.user:
                    messages.error(request, "Nie możesz dodać samego siebie!")
                    return redirect('index')

                if Friend.objects.filter(user=request.user, friend_account=target_user).exists():
                    messages.info(request, "Już jesteście znajomymi.")
                
                elif FriendRequest.objects.filter(from_user=request.user, to_user=target_user).exists():
                    messages.warning(request, "Zaproszenie już czeka na akceptację.")
                
                elif FriendRequest.objects.filter(from_user=target_user, to_user=request.user).exists():
                     req = FriendRequest.objects.get(from_user=target_user, to_user=request.user)
                     handle_friend_request(request, req.id, 'accept')
                     return redirect('index')

                else:
                    FriendRequest.objects.create(from_user=request.user, to_user=target_user)
                    messages.success(request, f"Wysłano zaproszenie do {target_user.username}.")
                    
            except User.DoesNotExist:
                messages.error(request, f"Użytkownik '{username}' nie istnieje.")
    return redirect('index')

def handle_friend_request(request, request_id, action):
    f_request = get_object_or_404(FriendRequest, id=request_id)
    
    if f_request.to_user != request.user:
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    if action == 'accept':
        Friend.objects.get_or_create(user=f_request.to_user, friend_account=f_request.from_user)
        Friend.objects.get_or_create(user=f_request.from_user, friend_account=f_request.to_user)
        messages.success(request, f"Jesteś teraz znajomym z {f_request.from_user.username}!")
    elif action == 'reject':
        messages.info(request, "Odrzucono zaproszenie.")
    
    f_request.delete()
    return redirect('index')

def create_group(request):
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        member_ids = request.POST.getlist('group_members') 
        
        if group_name and member_ids:
            group = Group.objects.create(creator=request.user, name=group_name)
            for uid in member_ids:
                group.members.add(int(uid))
            group.save()
            messages.success(request, f"Utworzono grupę '{group_name}'.")
        else:
            messages.error(request, "Wybierz nazwę i członków grupy.")
            
    return redirect('index')

# --- RACHUNKI - TU BYŁ BŁĄD, POPRAWIONA WERSJA ---
def create_spill(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        tip = request.POST.get('tip')
        custom_splits_json = request.POST.get('custom_splits')
        
        # 1. ODBIERAMY OPIS
        description = request.POST.get('description') 

        if not amount: return JsonResponse({'message': 'Brak kwoty'}, status=400)
        if not tip: tip = '0'
        
        # Zabezpieczenie, gdyby opis był pusty
        if not description: 
            description = "Rachunek"

        try:
            total_amount = float(amount) * (1 + float(tip) / 100)
            
            # 2. ZAPISUJEMY W BAZIE
            bill = Bill.objects.create(
                creator=request.user,
                description=description, # <--- TU WKLEJAMY ZMIENNĄ
                amount=total_amount
            )
            
            # 2. Przetwarzamy JSON-a z dokładnymi kwotami
            if custom_splits_json:
                splits_data = json.loads(custom_splits_json)
                
                for item in splits_data:
                    user_id = item.get('id')
                    user_amount = item.get('amount')
                    
                    if user_id and user_amount:
                        user = User.objects.get(id=int(user_id))
                        
                        # A. Dodajemy do uczestników (żeby działało wyszukiwanie)
                        bill.participants.add(user)
                        
                        # B. Zapisujemy dokładną kwotę w BillShare
                        BillShare.objects.create(
                            bill=bill,
                            user=user,
                            amount_owed=float(user_amount)
                        )
            
            bill.save()
            return JsonResponse({'message': 'Success'})
            
        except ValueError:
             return JsonResponse({'message': 'Błąd danych'}, status=400)
        except Exception as e:
             # Warto wypisać błąd w konsoli serwera, żebyś widział co się dzieje
             print(f"Błąd create_spill: {e}")
             return JsonResponse({'message': str(e)}, status=500)
    
    return JsonResponse({'message': 'Zła metoda'}, status=400)

# --- STATUSY (BEZ ZMIAN) ---
def update_bill_status(request, bill_id, new_status):
    bill = get_object_or_404(Bill, id=bill_id)
    
    is_creator = request.user == bill.creator
    is_participant = request.user in bill.participants.all()
    
    if not (is_creator or is_participant):
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    if new_status == 'REJECTED':
        bill.status = Bill.Status.REJECTED
        bill.save()
        messages.info(request, "Rachunek odrzucony.")
        
    elif new_status == 'PAID':
        if is_creator:
            bill.status = Bill.Status.PAID
            bill.save()
            messages.success(request, "Sfinalizowano!")
        else:
            messages.error(request, "Tylko twórca może sfinalizować.")

    elif new_status == 'PENDING':
         bill.status = Bill.Status.PENDING
         bill.save()

    return redirect('index')