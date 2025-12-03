from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from .forms import RegisterForm
from django.contrib.auth import get_user_model
import logging
import random
from django.http import JsonResponse
from django.db.models import Q # Do zapytań złożonych
# Importujemy wszystkie modele
from .models import Person, Friend, Bill, FriendRequest, Group 

logger = logging.getLogger(__name__)

# --- WIDOK GŁÓWNY (DASHBOARD) ---
def index(request):
    if request.user.is_authenticated:
        # 1. Znajomi
        friends = Friend.objects.filter(user=request.user)
        
        # 2. Zaproszenia oczekujące (Ktoś -> Ja)
        friend_requests = FriendRequest.objects.filter(to_user=request.user)
        
        # 3. Moje grupy
        my_groups = Group.objects.filter(creator=request.user)

        # 4. Rachunki (Jako twórca LUB uczestnik)
        participated_bills = Bill.objects.filter(
            Q(creator=request.user) | Q(participants=request.user)
        ).distinct().order_by('-date')[:5]
        
        context = {
            'friends': friends,
            'friend_requests': friend_requests, # Ważne dla HTML
            'my_groups': my_groups,             # Ważne dla HTML
            'participated_bills': participated_bills
        }
        return render(request, 'index.html', context)
    else:
        return redirect('login')

# --- LOGOWANIE I REJESTRACJA ---
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

# --- WYSZUKIWANIE I ZAPROSZENIA ---
def search_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if username:
            try:
                target_user = User.objects.get(username=username)
                
                if target_user == request.user:
                    messages.error(request, "Nie możesz dodać samego siebie!")
                    return redirect('index')

                # 1. Czy już są znajomymi?
                if Friend.objects.filter(user=request.user, friend_account=target_user).exists():
                    messages.info(request, "Już jesteście znajomymi.")
                
                # 2. Czy zaproszenie już wysłano?
                elif FriendRequest.objects.filter(from_user=request.user, to_user=target_user).exists():
                    messages.warning(request, "Zaproszenie już czeka na akceptację.")
                
                # 3. Czy ON wysłał zaproszenie do MNIE? (Akceptuj automatycznie)
                elif FriendRequest.objects.filter(from_user=target_user, to_user=request.user).exists():
                     # Wywołujemy logikę akceptacji
                     req = FriendRequest.objects.get(from_user=target_user, to_user=request.user)
                     handle_friend_request(request, req.id, 'accept')
                     # handle_friend_request zrobi redirect, więc tu returnujemy
                     return redirect('index')

                # 4. Wyślij nowe zaproszenie
                else:
                    FriendRequest.objects.create(from_user=request.user, to_user=target_user)
                    messages.success(request, f"Wysłano zaproszenie do {target_user.username}.")
                    
            except User.DoesNotExist:
                messages.error(request, f"Użytkownik '{username}' nie istnieje.")
    return redirect('index')

# --- OBSŁUGA ZAPROSZEŃ (TEGO BRAKOWAŁO!) ---
def handle_friend_request(request, request_id, action):
    f_request = get_object_or_404(FriendRequest, id=request_id)
    
    # Zabezpieczenie: czy to zaproszenie do mnie?
    if f_request.to_user != request.user:
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    if action == 'accept':
        # Tworzymy relację W OBIE STRONY
        Friend.objects.get_or_create(user=f_request.to_user, friend_account=f_request.from_user)
        Friend.objects.get_or_create(user=f_request.from_user, friend_account=f_request.to_user)
        messages.success(request, f"Jesteś teraz znajomym z {f_request.from_user.username}!")
    elif action == 'reject':
        messages.info(request, "Odrzucono zaproszenie.")
    
    # Usuwamy zaproszenie z bazy
    f_request.delete()
    return redirect('index')

# --- GRUPY (TEGO TEŻ BRAKOWAŁO!) ---
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

# --- RACHUNKI ---
def create_spill(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        tip = request.POST.get('tip')
        friend_ids = request.POST.getlist('friends[]')

        if not amount: return JsonResponse({'message': 'Brak kwoty'}, status=400)
        if not tip: tip = '0'

        try:
            total_amount = float(amount) * (1 + float(tip) / 100)
            
            bill = Bill.objects.create(
                creator=request.user,
                description='Nowy rachunek',
                amount=total_amount
            )
            
            for fid in friend_ids:
                if fid:
                    bill.participants.add(int(fid))
            
            bill.save()
            return JsonResponse({'message': 'Success'})
            
        except ValueError:
             return JsonResponse({'message': 'Błąd danych'}, status=400)
    
    return JsonResponse({'message': 'Zła metoda'}, status=400)

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