from django.db import models
from django.contrib.auth.models import User

# --- Modele pomocnicze ---
class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

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