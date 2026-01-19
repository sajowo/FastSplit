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
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from .models import Person, Friend, Bill, FriendRequest, Group, BillShare, LoginLockout, NotificationReadStatus, UserTOTP

from datetime import timedelta
import pyotp
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64

from axes.helpers import get_client_ip_address

logger = logging.getLogger(__name__)


# --- STRONY INFORMACYJNE ---
@never_cache
def faq_view(request):
    return render(request, 'faq.html')


@never_cache
def about_view(request):
    return render(request, 'about.html')


@never_cache
def terms_view(request):
    return render(request, 'terms.html')

# --- WIDOK GŁÓWNY (DASHBOARD) ---
@never_cache
def index(request):
    if request.user.is_authenticated:
        friends = Friend.objects.filter(user=request.user)
        friend_requests = FriendRequest.objects.filter(to_user=request.user)
        my_groups = Group.objects.filter(creator=request.user)

        # Pobierz timestamp ostatniego odczytu powiadomień
        try:
            notification_status = NotificationReadStatus.objects.get(user=request.user)
            last_read_at = notification_status.read_at
        except NotificationReadStatus.DoesNotExist:
            last_read_at = None

        # Powiadomienia dla twórcy: odrzucone i opłacone udziały w AKTYWNYCH (PENDING) rachunkach
        rejected_bill_shares_qs = (
            BillShare.objects
            .select_related('bill', 'user')
            .filter(
                bill__creator=request.user,
                bill__status=Bill.Status.PENDING,
                rejected=True,
            )
            .order_by('-bill__date')
        )

        paid_bill_shares_qs = (
            BillShare.objects
            .select_related('bill', 'user')
            .filter(
                bill__creator=request.user,
                bill__status=Bill.Status.PENDING,
                paid=True,
                rejected=False,
            )
            .exclude(user=request.user)
            .order_by('-bill__date')
        )

        rejected_bill_shares_for_creator = list(rejected_bill_shares_qs[:5])
        paid_bill_shares_for_creator = list(paid_bill_shares_qs[:5])

        # Oblicz liczbę nieprzeczytanych powiadomień (nowszych niż last_read_at)
        # WAŻNE: Liczymy tylko powiadomienia z rachunków, które nadal są PENDING
        # Po sfinalizowaniu/odrzuceniu rachunku przez twórcę, te powiadomienia znikają
        if last_read_at:
            unread_friend_requests = friend_requests.filter(created_at__gt=last_read_at).count()
            unread_rejected = rejected_bill_shares_qs.filter(bill__date__gt=last_read_at).count()
            unread_paid = paid_bill_shares_qs.filter(bill__date__gt=last_read_at).count()
        else:
            # Jeśli nigdy nie odczytano, wszystkie są nieprzeczytane
            unread_friend_requests = friend_requests.count()
            unread_rejected = rejected_bill_shares_qs.count()
            unread_paid = paid_bill_shares_qs.count()

        notifications_count = unread_friend_requests + unread_rejected + unread_paid

        def decorate_bill_for_user(bill: Bill):
            if request.user == bill.creator:
                bill.display_amount = f"{bill.amount} PLN (Całość)"
                bill.debtors_list = bill.shares.filter(amount_owed__gt=0)
                bill.user_share_rejected = False
                bill.user_share_paid = True
                bill.user_effective_status = bill.status
                bill.user_status_label = bill.get_status_display()
                return bill

            try:
                share = bill.shares.get(user=request.user)
                bill.display_amount = f"{share.amount_owed} PLN (Twój udział)"
                bill.user_share_rejected = bool(getattr(share, 'rejected', False))
                bill.user_share_paid = bool(getattr(share, 'paid', False))

                if bill.status == Bill.Status.PENDING and bill.user_share_rejected:
                    bill.user_effective_status = Bill.Status.REJECTED
                    bill.user_status_label = "Odrzucony"
                else:
                    bill.user_effective_status = bill.status
                    bill.user_status_label = bill.get_status_display()
            except Exception:
                bill.display_amount = "0.00 PLN"
                bill.user_share_rejected = False
                bill.user_share_paid = False
                bill.user_effective_status = bill.status
                bill.user_status_label = bill.get_status_display()

            bill.debtors_list = None
            return bill

        # Prawy panel: 1) DO ZROBIENIA (opłać/odrzuć) – tylko Twoje, 2) HISTORIA (ostatnie 8)
        todo_bills = list(
            Bill.objects
            .filter(
                participants=request.user,
                status=Bill.Status.PENDING,
                shares__user=request.user,
                shares__paid=False,
                shares__rejected=False,
            )
            .exclude(creator=request.user)
            .distinct()
            .order_by('-date')[:8]
        )

        # Historia: rachunki które są zakończone LUB w których użytkownik opłacił/odrzucił swój udział
        history_bills_qs = Bill.objects.filter(
            Q(creator=request.user) | Q(participants=request.user)
        ).distinct()
        
        # Filtruj rachunki do historii:
        # 1. Rachunki ze statusem PAID lub REJECTED (dla wszystkich)
        # 2. Rachunki PENDING gdzie użytkownik opłacił swój udział (ale nie jest twórcą)
        # 3. Rachunki PENDING gdzie użytkownik odrzucił swój udział (ale nie jest twórcą)
        # Wykluczamy rachunki które są w todo_bills
        history_bills_ids = set()
        
        for bill in history_bills_qs:
            # Pomiń rachunki z todo_bills
            if bill.id in [b.id for b in todo_bills]:
                continue
                
            # Rachunki zakończone (PAID/REJECTED) - zawsze w historii
            if bill.status in [Bill.Status.PAID, Bill.Status.REJECTED]:
                history_bills_ids.add(bill.id)
                continue
            
            # Rachunki PENDING - sprawdź czy użytkownik opłacił/odrzucił swój udział
            if bill.status == Bill.Status.PENDING:
                # Jeśli użytkownik jest twórcą, nie dodawaj do historii (będzie w my_waiting_bills)
                if bill.creator == request.user:
                    continue
                    
                # Sprawdź czy użytkownik ma udział w tym rachunku
                try:
                    share = bill.shares.get(user=request.user)
                    # Jeśli opłacił lub odrzucił - dodaj do historii
                    if share.paid or share.rejected:
                        history_bills_ids.add(bill.id)
                except BillShare.DoesNotExist:
                    pass
        
        history_bills = list(
            Bill.objects
            .filter(id__in=history_bills_ids)
            .order_by('-date')[:8]
        )

        # Lewa strona: rachunki utworzone przeze mnie, oczekujące na innych
        my_waiting_bills = list(
            Bill.objects
            .filter(creator=request.user, status=Bill.Status.PENDING)
            .prefetch_related('shares__user')
            .order_by('-date')[:8]
        )

        # Statystyki (prawy panel): Do odebrania / Do zapłacenia (tylko oczekujące, bez odrzuconych udziałów)
        amount_to_receive = (
            BillShare.objects
            .filter(
                bill__creator=request.user,
                bill__status=Bill.Status.PENDING,
                rejected=False,
                paid=False,
            )
            .exclude(user=request.user)
            .aggregate(total=Coalesce(
                Sum('amount_owed'),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ))
            .get('total')
        )

        amount_to_pay = (
            BillShare.objects
            .filter(
                user=request.user,
                bill__status=Bill.Status.PENDING,
                rejected=False,
                paid=False,
            )
            .exclude(bill__creator=request.user)
            .aggregate(total=Coalesce(
                Sum('amount_owed'),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ))
            .get('total')
        )

        todo_bills = [decorate_bill_for_user(b) for b in todo_bills]
        history_bills = [decorate_bill_for_user(b) for b in history_bills]
        my_waiting_bills = [decorate_bill_for_user(b) for b in my_waiting_bills]

        for bill in my_waiting_bills:
            shares = list(bill.shares.exclude(user=request.user).select_related('user'))
            bill.waiting_total = len(shares)
            bill.waiting_paid_shares = [
                s for s in shares if getattr(s, 'paid', False) and not getattr(s, 'rejected', False)
            ]
            bill.waiting_paid = len(bill.waiting_paid_shares)
            bill.waiting_rejected = [s for s in shares if getattr(s, 'rejected', False)]
            bill.waiting_unpaid = [
                s for s in shares
                if (not getattr(s, 'paid', False) and not getattr(s, 'rejected', False))
            ]

        context = {
            'friends': friends,
            'friend_requests': friend_requests,
            'rejected_bill_shares_for_creator': rejected_bill_shares_for_creator,
            'paid_bill_shares_for_creator': paid_bill_shares_for_creator,
            'notifications_count': notifications_count,
            'my_groups': my_groups,
            'todo_bills': todo_bills,
            'history_bills': history_bills,
            'my_waiting_bills': my_waiting_bills,
            'amount_to_receive': amount_to_receive,
            'amount_to_pay': amount_to_pay,
        }
        return render(request, 'index.html', context)
    else:
        return redirect('login')

# --- LOGOWANIE (POPRAWIONE - CAPTCHA BLOKUJE) ---
@never_cache
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
            # NOTE: Email is not unique in Django's default User model.
            # We enforce uniqueness on registration, but also handle legacy duplicates here.
            user_qs = User.objects.filter(email__iexact=email_norm).order_by('id')
            if user_qs.count() == 1:
                username_to_check = user_qs.first().username
            elif user_qs.count() == 0:
                username_to_check = "nieistniejacy_uzytkownik_xyz"
            else:
                messages.error(
                    request,
                    'Wykryto kilka kont z tym samym e-mailem. Skontaktuj się z administratorem, aby scalić konto.'
                )
                return render(request, 'login.html', {'form': form})

            # Używamy authenticate (Wymagane dla Axes)
            user = authenticate(request, username=username_to_check, password=password)

            if user is not None:
                # Sprawdź czy user ma włączone 2FA
                try:
                    totp = user.totp
                    if totp.is_enabled:
                        # Zapisz user ID w sesji i przekieruj na weryfikację 2FA
                        request.session['pending_2fa_user_id'] = user.id
                        
                        # Reset blokady po poprawnym haśle
                        lock_rec.failures = 0
                        lock_rec.save(update_fields=['failures', 'updated_at'])
                        
                        return redirect('verify_2fa')
                except UserTOTP.DoesNotExist:
                    pass
                
                # Brak 2FA - normalne logowanie
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
@never_cache
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
            
            # Przekieruj na konfigurację 2FA
            request.session['pending_2fa_setup'] = True
            return redirect('setup_2fa')
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


@login_required
@require_POST
def remove_friend(request, user_id: int):
    """Usuwa znajomego (relację Friend w obie strony)."""
    try:
        target_user = User.objects.get(id=int(user_id))
    except Exception:
        return JsonResponse({'ok': False, 'message': 'Nieprawidłowy użytkownik.'}, status=400)

    if target_user == request.user:
        return JsonResponse({'ok': False, 'message': 'Nie możesz usunąć samego siebie.'}, status=400)

    # usuń relacje w obie strony
    deleted = 0
    deleted += Friend.objects.filter(user=request.user, friend_account=target_user).delete()[0]
    deleted += Friend.objects.filter(user=target_user, friend_account=request.user).delete()[0]

    # usuń ewentualne zaległe zaproszenia między tymi użytkownikami
    FriendRequest.objects.filter(from_user=request.user, to_user=target_user).delete()
    FriendRequest.objects.filter(from_user=target_user, to_user=request.user).delete()

    if deleted == 0:
        msg = 'Nie znaleziono takiego znajomego.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': msg}, status=404)
        messages.info(request, msg)
        return redirect('index')

    msg = f"Usunięto znajomego: {target_user.username}."
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'message': msg})

    messages.success(request, msg)
    return redirect('index')

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
                            amount_owed=float(user_amount),
                            accepted=False  # Użytkownik musi zaakceptować
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
@never_cache
@login_required
def update_bill_status(request, bill_id, new_status):
    bill = get_object_or_404(Bill, id=bill_id)
    
    is_creator = request.user == bill.creator
    is_participant = request.user in bill.participants.all()

    if not (is_creator or is_participant):
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    # Zmiana statusu całego rachunku jest tylko dla twórcy.
    if not is_creator:
        messages.error(request, "Tylko twórca może zmieniać status rachunku.")
        return redirect('index')

    if new_status == 'REJECTED':
        bill.status = Bill.Status.REJECTED
        bill.save(update_fields=['status'])
        messages.info(request, "Rachunek odrzucony.")
        
    elif new_status == 'PAID':
        bill.status = Bill.Status.PAID
        bill.save(update_fields=['status'])
        messages.success(request, "Sfinalizowano!")

    elif new_status == 'PENDING':
         bill.status = Bill.Status.PENDING
         bill.save(update_fields=['status'])

    return redirect('index')


@login_required
@require_POST
def accept_bill_share(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    # tylko uczestnik (nie twórca)
    if request.user == bill.creator or request.user not in bill.participants.all():
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    share = BillShare.objects.filter(bill=bill, user=request.user).first()
    if not share:
        messages.error(request, "Nie znaleziono udziału w rozliczeniu.")
        return redirect('index')

    if bill.status != Bill.Status.PENDING:
        messages.info(request, "To rozliczenie nie jest już oczekujące.")
        return redirect('index')

    share.accepted = True
    # Akceptacja anuluje ewentualne wcześniejsze odrzucenie udziału
    if getattr(share, 'rejected', False):
        share.rejected = False
        share.save(update_fields=['accepted', 'rejected'])
    else:
        share.save(update_fields=['accepted'])

    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or '')
    if wants_json:
        return JsonResponse({'ok': True})

    messages.success(request, "Zaakceptowano rozliczenie.")
    return redirect('index')


@login_required
@require_POST
def reject_bill_share(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    # tylko uczestnik (nie twórca)
    if request.user == bill.creator or request.user not in bill.participants.all():
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    share = BillShare.objects.filter(bill=bill, user=request.user).first()
    if not share:
        messages.error(request, "Nie znaleziono udziału w rozliczeniu.")
        return redirect('index')

    if bill.status != Bill.Status.PENDING:
        messages.info(request, "To rozliczenie nie jest już oczekujące.")
        return redirect('index')

    share.accepted = True
    share.rejected = True
    if getattr(share, 'paid', False):
        share.paid = False
        share.save(update_fields=['accepted', 'rejected', 'paid'])
    else:
        share.save(update_fields=['accepted', 'rejected'])

    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or '')
    if wants_json:
        return JsonResponse({'ok': True})

    messages.info(request, "Odrzucono udział w rozliczeniu.")
    return redirect('index')


@login_required
@require_POST
def pay_bill_share(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    # tylko uczestnik (nie twórca)
    if request.user == bill.creator or request.user not in bill.participants.all():
        messages.error(request, "Brak uprawnień.")
        return redirect('index')

    share = BillShare.objects.filter(bill=bill, user=request.user).first()
    if not share:
        messages.error(request, "Nie znaleziono udziału w rozliczeniu.")
        return redirect('index')

    if bill.status != Bill.Status.PENDING:
        messages.info(request, "To rozliczenie nie jest już oczekujące.")
        return redirect('index')

    if getattr(share, 'rejected', False):
        messages.error(request, "Odrzuciłeś udział w tym rozliczeniu.")
        return redirect('index')

    share.paid = True
    share.save(update_fields=['paid'])

    # Jeśli wszyscy uczestnicy (bez twórcy) opłacili swoje udziały, automatycznie finalizujemy rachunek.
    all_paid = not BillShare.objects.filter(
        bill=bill,
        rejected=False,
    ).exclude(user=bill.creator).exclude(paid=True, accepted=True).exists()

    if all_paid:
        bill.status = Bill.Status.PAID
        bill.save(update_fields=['status'])

    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (request.headers.get('Accept') or '')
    if wants_json:
        return JsonResponse({'ok': True, 'bill_paid': all_paid})

    messages.success(request, "Oznaczono jako opłacone.")
    return redirect('index')


@login_required
@require_GET
def get_pending_bill_notifications(request):
    pending = (
        BillShare.objects
        .select_related('bill', 'bill__creator')
        .filter(
            user=request.user,
            bill__status=Bill.Status.PENDING,
            accepted=False,
            rejected=False,
        )
        .exclude(bill__creator=request.user)
        .order_by('-bill__date')
    )

    data = []
    for share in pending:
        data.append({
            'bill_id': share.bill_id,
            'creator': share.bill.creator.username,
            'description': share.bill.description,
            'amount_owed': str(share.amount_owed),
            'date': share.bill.date.isoformat(),
        })

    return JsonResponse({'pending': data})


@login_required
@require_POST
def mark_notifications_read(request):
    """Oznacza powiadomienia jako przeczytane (zapisuje timestamp)."""
    status, _ = NotificationReadStatus.objects.get_or_create(user=request.user)
    status.read_at = timezone.now()
    status.save(update_fields=['read_at'])
    return JsonResponse({'ok': True})


@login_required
@require_GET
def get_notifications_count(request):
    """Zwraca całkowitą liczbę nieprzeczytanych powiadomień."""
    friend_requests = FriendRequest.objects.filter(to_user=request.user)
    
    # Pobierz timestamp ostatniego odczytu powiadomień
    try:
        notification_status = NotificationReadStatus.objects.get(user=request.user)
        last_read_at = notification_status.read_at
    except NotificationReadStatus.DoesNotExist:
        last_read_at = None

    # Powiadomienia dla twórcy: odrzucone i opłacone udziały w AKTYWNYCH (PENDING) rachunkach
    rejected_bill_shares_qs = (
        BillShare.objects
        .filter(
            bill__creator=request.user,
            bill__status=Bill.Status.PENDING,
            rejected=True,
        )
    )

    paid_bill_shares_qs = (
        BillShare.objects
        .filter(
            bill__creator=request.user,
            bill__status=Bill.Status.PENDING,
            paid=True,
            rejected=False,
        )
        .exclude(user=request.user)
    )

    # Nowe rozliczenia do akceptacji
    pending_bill_shares_qs = (
        BillShare.objects
        .filter(
            user=request.user,
            bill__status=Bill.Status.PENDING,
            accepted=False,
            rejected=False,
        )
        .exclude(bill__creator=request.user)
    )

    # Oblicz liczbę nieprzeczytanych powiadomień
    if last_read_at:
        unread_friend_requests = friend_requests.filter(created_at__gt=last_read_at).count()
        unread_rejected = rejected_bill_shares_qs.filter(bill__date__gt=last_read_at).count()
        unread_paid = paid_bill_shares_qs.filter(bill__date__gt=last_read_at).count()
        unread_pending_bills = pending_bill_shares_qs.filter(bill__date__gt=last_read_at).count()
    else:
        # Jeśli nigdy nie odczytano, wszystkie są nieprzeczytane
        unread_friend_requests = friend_requests.count()
        unread_rejected = rejected_bill_shares_qs.count()
        unread_paid = paid_bill_shares_qs.count()
        unread_pending_bills = pending_bill_shares_qs.count()

    notifications_count = unread_friend_requests + unread_rejected + unread_paid + unread_pending_bills

    return JsonResponse({
        'count': notifications_count,
        'friend_requests': unread_friend_requests,
        'rejected': unread_rejected,
        'paid': unread_paid,
        'pending_bills': unread_pending_bills,
    })


# --- 2FA (TOTP) ---

def generate_qr_code_base64(uri: str) -> str:
    """Generuje QR kod jako base64 PNG."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@never_cache
def setup_2fa_view(request):
    """
    Strona konfiguracji 2FA - pokazywana po rejestracji lub z ustawień.
    Użytkownik może pominąć (skip) lub skonfigurować.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    # Sprawdź czy user już ma włączone 2FA
    try:
        totp = request.user.totp
        if totp.is_enabled:
            messages.info(request, "Masz już włączone 2FA.")
            return redirect('index')
    except UserTOTP.DoesNotExist:
        totp = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'skip':
            # Użytkownik pomija konfigurację 2FA
            request.session.pop('pending_2fa_setup', None)
            messages.info(request, "Pominięto konfigurację 2FA. Możesz ją włączyć później w ustawieniach.")
            return redirect('index')

        elif action == 'generate':
            # Generuj nowy sekret
            totp = UserTOTP.create_for_user(request.user)
            uri = totp.get_provisioning_uri()
            qr_base64 = generate_qr_code_base64(uri)
            
            return render(request, 'setup_2fa.html', {
                'step': 'scan',
                'qr_code': qr_base64,
                'secret': totp.secret,
                'show_skip': request.session.get('pending_2fa_setup', False),
            })

        elif action == 'verify':
            # Weryfikuj kod i włącz 2FA
            code = request.POST.get('code', '').strip()
            
            if not totp:
                try:
                    totp = request.user.totp
                except UserTOTP.DoesNotExist:
                    messages.error(request, "Najpierw wygeneruj kod QR.")
                    return redirect('setup_2fa')

            if totp.get_totp().verify(code, valid_window=1):
                totp.is_enabled = True
                backup_codes = totp.generate_backup_codes()
                totp.save()
                
                request.session.pop('pending_2fa_setup', None)
                
                return render(request, 'setup_2fa.html', {
                    'step': 'success',
                    'backup_codes': backup_codes,
                })
            else:
                messages.error(request, "Nieprawidłowy kod. Spróbuj ponownie.")
                uri = totp.get_provisioning_uri()
                qr_base64 = generate_qr_code_base64(uri)
                return render(request, 'setup_2fa.html', {
                    'step': 'scan',
                    'qr_code': qr_base64,
                    'secret': totp.secret,
                    'show_skip': request.session.get('pending_2fa_setup', False),
                })

    # GET - pokaż stronę startową
    return render(request, 'setup_2fa.html', {
        'step': 'start',
        'show_skip': request.session.get('pending_2fa_setup', False),
    })


@never_cache
def verify_2fa_view(request):
    """
    Strona weryfikacji kodu 2FA po zalogowaniu.
    User jest już "częściowo" zalogowany (w sesji).
    """
    pending_user_id = request.session.get('pending_2fa_user_id')
    
    if not pending_user_id:
        return redirect('login')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        
        try:
            user = User.objects.get(id=pending_user_id)
            totp = user.totp
        except (User.DoesNotExist, UserTOTP.DoesNotExist):
            messages.error(request, "Błąd weryfikacji. Zaloguj się ponownie.")
            request.session.pop('pending_2fa_user_id', None)
            return redirect('login')

        if totp.verify_code(code):
            # Kod poprawny - zaloguj użytkownika
            request.session.pop('pending_2fa_user_id', None)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, "Zalogowano pomyślnie!")
            return redirect('index')
        else:
            messages.error(request, "Nieprawidłowy kod. Spróbuj ponownie lub użyj kodu zapasowego.")

    return render(request, 'verify_2fa.html')


@login_required
@never_cache
def disable_2fa_view(request):
    """Wyłącza 2FA dla użytkownika."""
    try:
        totp = request.user.totp
    except UserTOTP.DoesNotExist:
        messages.info(request, "Nie masz włączonego 2FA.")
        return redirect('index')

    if not totp.is_enabled:
        messages.info(request, "2FA nie jest włączone.")
        return redirect('index')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        
        if totp.verify_code(code):
            totp.is_enabled = False
            totp.backup_codes = ''
            totp.save()
            messages.success(request, "Wyłączono weryfikację dwuetapową.")
            return redirect('index')
        else:
            messages.error(request, "Nieprawidłowy kod.")

    return render(request, 'disable_2fa.html')


# --- USTAWIENIA PROFILU ---

@login_required
@never_cache
def settings_view(request):
    """Strona ustawień profilu użytkownika."""
    try:
        person = request.user.person
    except Person.DoesNotExist:
        person = Person.objects.create(
            user=request.user,
            first_name=request.user.first_name or '',
            last_name=request.user.last_name or ''
        )

    # Sprawdź status 2FA
    try:
        totp = request.user.totp
        has_2fa = totp.is_enabled
    except UserTOTP.DoesNotExist:
        has_2fa = False

    # Sprawdź czy można zmienić nazwę użytkownika (raz na 30 dni)
    can_change_username = True
    days_until_change = 0
    if person.username_changed_at:
        days_since_change = (timezone.now() - person.username_changed_at).days
        if days_since_change < 30:
            can_change_username = False
            days_until_change = 30 - days_since_change

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_username':
            if not can_change_username:
                messages.error(request, f'Możesz zmienić nazwę użytkownika za {days_until_change} dni.')
                return redirect('settings')
            
            new_username = request.POST.get('username', '').strip()
            
            if not new_username:
                messages.error(request, 'Nazwa użytkownika nie może być pusta.')
            elif len(new_username) < 3:
                messages.error(request, 'Nazwa użytkownika musi mieć co najmniej 3 znaki.')
            elif len(new_username) > 30:
                messages.error(request, 'Nazwa użytkownika może mieć maksymalnie 30 znaków.')
            elif not new_username.replace('_', '').isalnum():
                messages.error(request, 'Nazwa użytkownika może zawierać tylko litery, cyfry i podkreślenia.')
            elif User.objects.filter(username__iexact=new_username).exclude(id=request.user.id).exists():
                messages.error(request, 'Ta nazwa użytkownika jest już zajęta.')
            elif new_username == request.user.username:
                messages.info(request, 'To jest Twoja aktualna nazwa użytkownika.')
            else:
                request.user.username = new_username
                request.user.save(update_fields=['username'])
                person.username_changed_at = timezone.now()
                person.save(update_fields=['username_changed_at'])
                messages.success(request, 'Nazwa użytkownika została zmieniona.')
            return redirect('settings')

        elif action == 'update_avatar':
            if 'avatar' in request.FILES:
                avatar_file = request.FILES['avatar']
                
                # Walidacja rozmiaru (max 2MB)
                if avatar_file.size > 2 * 1024 * 1024:
                    messages.error(request, 'Plik jest za duży. Maksymalny rozmiar to 2MB.')
                    return redirect('settings')
                
                # Walidacja typu
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if avatar_file.content_type not in allowed_types:
                    messages.error(request, 'Dozwolone formaty: JPG, PNG, GIF, WEBP.')
                    return redirect('settings')
                
                # Usuń stary avatar jeśli istnieje
                if person.avatar:
                    person.avatar.delete(save=False)
                
                person.avatar = avatar_file
                person.save()
                messages.success(request, 'Avatar został zaktualizowany.')
            else:
                messages.error(request, 'Nie wybrano pliku.')
            return redirect('settings')

        elif action == 'remove_avatar':
            if person.avatar:
                person.avatar.delete(save=False)
                person.avatar = None
                person.save()
                messages.success(request, 'Avatar został usunięty.')
            return redirect('settings')

    context = {
        'person': person,
        'has_2fa': has_2fa,
        'can_change_username': can_change_username,
        'days_until_change': days_until_change,
    }
    return render(request, 'settings.html', context)
