from django.db import models
from django.contrib.auth.models import User
import pyotp
import secrets

# --- Modele pomocnicze ---
class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    username_changed_at = models.DateTimeField(null=True, blank=True)

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username}"

class Group(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups', default=1)
    name = models.CharField(max_length=50)
    members = models.ManyToManyField(User, related_name='user_groups')

    def __str__(self):
        return f"{self.name} ({self.members.count()} członków)"

class Friend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends_added')
    friend_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name='added_by_others')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'friend_account')

    def __str__(self):
        return f"{self.user.username} -> {self.friend_account.username}"

class Bill(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Oczekujący'
        REJECTED = 'REJECTED', 'Odrzucony'
        PAID = 'PAID', 'Sfinalizowany'

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bills')
    participants = models.ManyToManyField(User, related_name='participated_bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(default="Rachunek")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f'{self.description} - {self.amount}'

    # Metoda pomocnicza dla starych rachunków (zabezpieczenie)
    @property
    def amount_per_person(self):
        count = self.participants.count()
        if count == 0:
            return 0
        return round(self.amount / count, 2)

    # Metoda do pobierania dokładnej kwoty z nowej tabeli
    def get_user_share(self, user):
        try:
            share = self.shares.get(user=user)
            return share.amount_owed
        except: # BillShare.DoesNotExist i inne błędy
            return 0

# --- TO MUSI BYĆ NA ZEWNĄTRZ (Równo z lewej strony) ---
class BillShare(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount_owed = models.DecimalField(max_digits=10, decimal_places=2)
    accepted = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)

    class Meta:
        unique_together = ('bill', 'user')

    def __str__(self):
        return f"{self.user.username} wisi {self.amount_owed} za {self.bill.description}"


class LoginLockout(models.Model):
    ip_address = models.CharField(max_length=64)
    email = models.CharField(max_length=254)
    failures = models.PositiveIntegerField(default=0)
    lockout_level = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ip_address', 'email')
        indexes = [
            models.Index(fields=['ip_address', 'email']),
            models.Index(fields=['locked_until']),
        ]

    def __str__(self):
        return f"{self.ip_address} / {self.email} (lvl={self.lockout_level}, failures={self.failures})"


class NotificationReadStatus(models.Model):
    """Przechowuje timestamp ostatniego odczytania powiadomień przez użytkownika."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_status')
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - read_at: {self.read_at}"


class UserTOTP(models.Model):
    """Przechowuje konfigurację 2FA (TOTP) dla użytkownika."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='totp')
    secret = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Kody zapasowe (backup codes) - 8 kodów po 8 znaków, oddzielone przecinkami
    backup_codes = models.TextField(blank=True, default='')

    def __str__(self):
        status = "włączone" if self.is_enabled else "wyłączone"
        return f"2FA dla {self.user.username} ({status})"

    def get_totp(self):
        """Zwraca obiekt pyotp.TOTP dla tego użytkownika."""
        return pyotp.TOTP(self.secret)

    def verify_code(self, code: str) -> bool:
        """Weryfikuje kod TOTP lub backup code."""
        code = code.strip().replace(' ', '')
        
        # Sprawdź kod TOTP
        if self.get_totp().verify(code, valid_window=1):
            return True
        
        # Sprawdź backup codes
        codes = [c.strip() for c in self.backup_codes.split(',') if c.strip()]
        if code.upper() in [c.upper() for c in codes]:
            # Usuń użyty backup code
            codes = [c for c in codes if c.upper() != code.upper()]
            self.backup_codes = ','.join(codes)
            self.save(update_fields=['backup_codes'])
            return True
        
        return False

    def get_provisioning_uri(self):
        """Zwraca URI do wygenerowania QR kodu."""
        return self.get_totp().provisioning_uri(
            name=self.user.email or self.user.username,
            issuer_name="FastSplit"
        )

    def generate_backup_codes(self) -> list[str]:
        """Generuje nowe kody zapasowe."""
        codes = [secrets.token_hex(4).upper() for _ in range(8)]
        self.backup_codes = ','.join(codes)
        self.save(update_fields=['backup_codes'])
        return codes

    def get_backup_codes_list(self) -> list[str]:
        """Zwraca listę pozostałych kodów zapasowych."""
        return [c.strip() for c in self.backup_codes.split(',') if c.strip()]

    @classmethod
    def create_for_user(cls, user):
        """Tworzy nową konfigurację TOTP dla użytkownika."""
        secret = pyotp.random_base32()
        totp_obj, created = cls.objects.get_or_create(
            user=user,
            defaults={'secret': secret, 'is_enabled': False}
        )
        if not created:
            # Reset jeśli już istnieje
            totp_obj.secret = secret
            totp_obj.is_enabled = False
            totp_obj.backup_codes = ''
            totp_obj.save()
        return totp_obj
