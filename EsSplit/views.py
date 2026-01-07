from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib import messages
from django.contrib.messages import get_messages
from .forms import RegisterForm, LoginForm # <--- Upewnij się, że masz LoginForm w forms.py
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import logging
import random
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Person, Friend, Bill, FriendRequest, Group, BillShare, LoginLockout

from datetime import timedelta

from axes.helpers import get_client_ip_address

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

        for bill in participated_bills:
            if request.user == bill.creator:
                bill.display_amount = f"{bill.amount} PLN (Całość)"
                bill.debtors_list = bill.shares.filter(amount_owed__gt=0)
            else:
                try:
                    share = bill.shares.get(user=request.user)
                    bill.display_amount = f"{share.amount_owed} PLN (Twój udział)"
                except:
                    bill.display_amount = "0.00 PLN"
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

# --- LOGOWANIE (POPRAWIONE - CAPTCHA BLOKUJE) ---
def login_view(request):
    # Jeśli już trwa blokada (np. user odświeża stronę), przekieruj na lockout
    if getattr(request, 'session', None) is not None:
        lockout_id = request.session.get('lockout_id')
        if lockout_id:
            try:
                rec = LoginLockout.objects.get(id=lockout_id)
                if rec.locked_until and rec.locked_until > timezone.now():
                    return redirect('lockout')
            except LoginLockout.DoesNotExist:
                request.session.pop('lockout_id', None)

    if request.method == 'POST':
        # 1. Ładujemy dane do formularza (tu jest walidacja Captchy)
        form = LoginForm(request.POST)
        
        # 2. KLUCZOWE: Całe logowanie musi być W ŚRODKU tego ifa!
        if form.is_valid():
            # Skoro jesteśmy tutaj, to Captcha jest OK.
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            ip = get_client_ip_address(request) or ''
            email_norm = (email or '').strip().lower()

            # Progresywna blokada: sprawdź czy już jest lockout
            lock_rec, _ = LoginLockout.objects.get_or_create(
                ip_address=ip,
                email=email_norm,
                defaults={'failures': 0, 'lockout_level': 0, 'locked_until': None},
            )
            if lock_rec.locked_until and lock_rec.locked_until > timezone.now():
                request.session['lockout_id'] = lock_rec.id
                return redirect('lockout')
            
            User = get_user_model()
            
            # Logika szukania username po emailu
            try:
                user_obj = User.objects.get(email=email)
                username_to_check = user_obj.username
            except User.DoesNotExist:
                username_to_check = "nieistniejacy_uzytkownik_xyz"

            # Używamy authenticate (Wymagane dla Axes)
            user = authenticate(request, username=username_to_check, password=password)

            if user is not None:
                login(request, user)
                logger.info("Logowanie udane")

                # Reset blokady po sukcesie
                lock_rec.failures = 0
                lock_rec.lockout_level = 0
                lock_rec.locked_until = None
                lock_rec.save(update_fields=['failures', 'lockout_level', 'locked_until', 'updated_at'])
                request.session.pop('lockout_id', None)
                return redirect('index')
            else:
                # Błąd: nieudane logowanie -> inkrementujemy licznik
                failure_limit = int(getattr(settings, 'LOGIN_FAILURE_LIMIT', 3))
                schedule = list(getattr(settings, 'LOGIN_LOCKOUT_SCHEDULE_MINUTES', [1, 5, 10, 15]))
                if not schedule:
                    schedule = [1]

                lock_rec.failures += 1

                # Po każdych 3 próbach nakładamy blokadę z rosnącym czasem
                if lock_rec.failures >= failure_limit:
                    lock_rec.failures = 0
                    lock_rec.lockout_level += 1
                    idx = min(lock_rec.lockout_level - 1, len(schedule) - 1)
                    minutes = int(schedule[idx])
                    lock_rec.locked_until = timezone.now() + timedelta(minutes=minutes)
                    lock_rec.save(update_fields=['failures', 'lockout_level', 'locked_until', 'updated_at'])
                    request.session['lockout_id'] = lock_rec.id
                    return redirect('lockout')

                lock_rec.save(update_fields=['failures', 'updated_at'])
                remaining = max(0, failure_limit - lock_rec.failures)
                messages.error(request, f'Nieprawidłowy email lub hasło. Pozostało prób: {remaining}.')
        
        else:
            # 3. TUTAJ TRAFIASZ JEŚLI CAPTCHA JEST ZŁA
            # Formularz nie jest valid, więc nie próbujemy nawet logować
            messages.error(request, 'Potwierdź, że nie jesteś robotem (błąd Captcha).')
            
    else:
        form = LoginForm()

    # Zwracamy formularz z błędami do szablonu
    return render(request, 'login.html', {'form': form})


def lockout_view(request):
    """Strona blokady Axes z odliczaniem do kolejnej próby logowania."""
    remaining_seconds = 0
    lockout_id = request.session.get('lockout_id')

    rec = None
    if lockout_id:
        try:
            rec = LoginLockout.objects.get(id=lockout_id)
        except LoginLockout.DoesNotExist:
            request.session.pop('lockout_id', None)

    if rec is None:
        # Fallback: weź najdłuższą aktywną blokadę dla IP
        client_ip = get_client_ip_address(request) or ''
        rec = (
            LoginLockout.objects
            .filter(ip_address=client_ip, locked_until__gt=timezone.now())
            .order_by('-locked_until')
            .first()
        )

    if rec and rec.locked_until:
        remaining_seconds = max(0, int((rec.locked_until - timezone.now()).total_seconds()))

    return render(request, 'lockout.html', {
        'remaining_seconds': remaining_seconds,
    })

# --- WYLOGOWANIE ---
def logout_view(request):
    # Wyczyść komunikaty flash, żeby nie pojawiały się po wylogowaniu na stronie logowania
    storage = get_messages(request)
    for _ in storage:
        pass
    logout(request)
    return redirect('login')

# --- GENERATOR NAZWY UŻYTKOWNIKA ---
def generate_username(first_name, last_name):
    base_username = f"{first_name.lower()}{last_name.lower()}"
    username = base_username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{random.randint(1000, 9999)}"
    return username

# --- REJESTRACJA (POPRAWIONA) ---
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Generowanie nazwy użytkownika (Twoja funkcja)
            user.username = generate_username(user.first_name, user.last_name)
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Tworzenie profilu Person
            person = Person(user=user, first_name=user.first_name, last_name=user.last_name)
            person.save()

            # --- FIX: Przypisujemy backend ręcznie przed logowaniem ---
            # To naprawia błąd "ValueError: You have multiple authentication backends..."
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            
            login(request, user)
            messages.success(request, 'Konto utworzone!')
            return redirect('index')
        else:
            messages.error(request, 'Formularz zawiera błędy. Sprawdź poniżej.')
    else:
        form = RegisterForm()
    return render(request, 'SignUp.html', {'form': form})

# --- WYSZUKIWANIE ZNAJOMYCH ---
@login_required
def search_user(request):
    """
    GET: zwraca listę pasujących użytkowników (JSON) do dropdownu.
    POST: fallback bez JS (nie wysyła zaproszeń automatycznie).
    """
    if request.method == 'GET':
        q = (request.GET.get('q') or request.GET.get('username') or '').strip()
        if len(q) < 2:
            return JsonResponse({'results': []})

        users = list(
            User.objects
            .filter(username__icontains=q)
            .exclude(id=request.user.id)
            .order_by('username')[:8]
        )

        if not users:
            return JsonResponse({'results': []})

        user_ids = [u.id for u in users]
        friend_ids = set(
            Friend.objects
            .filter(user=request.user, friend_account_id__in=user_ids)
            .values_list('friend_account_id', flat=True)
        )
        pending_sent_ids = set(
            FriendRequest.objects
            .filter(from_user=request.user, to_user_id__in=user_ids)
            .values_list('to_user_id', flat=True)
        )
        pending_received_ids = set(
            FriendRequest.objects
            .filter(to_user=request.user, from_user_id__in=user_ids)
            .values_list('from_user_id', flat=True)
        )

        results = []
        for u in users:
            if u.id in friend_ids:
                status = 'friend'
            elif u.id in pending_sent_ids:
                status = 'pending_sent'
            elif u.id in pending_received_ids:
                status = 'pending_received'
            else:
                status = 'invite'
            results.append({'id': u.id, 'username': u.username, 'status': status})

        return JsonResponse({'results': results})

    # POST fallback: nie wysyłamy zaproszeń automatycznie
    username = (request.POST.get('username') or '').strip()
    if not username:
        return redirect('index')

    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"Użytkownik '{username}' nie istnieje.")
        return redirect('index')

    if target_user == request.user:
        messages.error(request, "Nie możesz dodać samego siebie!")
        return redirect('index')

    messages.info(request, f"Znaleziono użytkownika {target_user.username}. Kliknij 'Zaproś' w liście wyników.")
    return redirect('index')


@login_required
@require_POST
def invite_user(request):
    """Wysyła zaproszenie do znajomych dopiero po kliknięciu 'Zaproś'."""
    user_id = request.POST.get('user_id')
    if not user_id and request.content_type == 'application/json':
        try:
            import json
            payload = json.loads(request.body.decode('utf-8') or '{}')
            user_id = payload.get('user_id')
        except Exception:
            user_id = None

    try:
        target_user = User.objects.get(id=int(user_id))
    except Exception:
        return JsonResponse({'ok': False, 'message': 'Nieprawidłowy użytkownik.'}, status=400)

    if target_user == request.user:
        return JsonResponse({'ok': False, 'message': 'Nie możesz zaprosić samego siebie.'}, status=400)

    if Friend.objects.filter(user=request.user, friend_account=target_user).exists():
        return JsonResponse({'ok': False, 'message': 'Już jesteście znajomymi.'}, status=409)

    if FriendRequest.objects.filter(from_user=request.user, to_user=target_user).exists():
        return JsonResponse({'ok': False, 'message': 'Zaproszenie już czeka na akceptację.'}, status=409)

    if FriendRequest.objects.filter(from_user=target_user, to_user=request.user).exists():
        return JsonResponse({'ok': False, 'message': 'Masz już zaproszenie od tego użytkownika — zaakceptuj w Powiadomieniach.'}, status=409)

    FriendRequest.objects.create(from_user=request.user, to_user=target_user)
    return JsonResponse({'ok': True, 'message': f"Wysłano zaproszenie do {target_user.username}."})

# --- OBSŁUGA ZAPROSZEŃ ---
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

# --- TWORZENIE GRUPY ---
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

# --- TWORZENIE RACHUNKU (SPILL) ---
def create_spill(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        tip = request.POST.get('tip')
        custom_splits_json = request.POST.get('custom_splits')
        description = request.POST.get('description') 

        if not amount: return JsonResponse({'message': 'Brak kwoty'}, status=400)
        if not tip: tip = '0'
        if not description: description = "Rachunek"

        try:
            total_amount = float(amount) * (1 + float(tip) / 100)
            
            bill = Bill.objects.create(
                creator=request.user,
                description=description,
                amount=total_amount
            )
            
            if custom_splits_json:
                splits_data = json.loads(custom_splits_json)
                for item in splits_data:
                    user_id = item.get('id')
                    user_amount = item.get('amount')
                    if user_id and user_amount:
                        user = User.objects.get(id=int(user_id))
                        bill.participants.add(user)
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
             print(f"Błąd create_spill: {e}")
             return JsonResponse({'message': str(e)}, status=500)
    
    return JsonResponse({'message': 'Zła metoda'}, status=400)

# --- STATUSY RACHUNKU ---
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