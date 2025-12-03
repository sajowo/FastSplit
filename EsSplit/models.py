from django.db import models
from django.contrib.auth.models import User

# --- Modele pomocnicze (można usunąć Person/Membership jeśli ich nie używasz, ale zostawiam dla bezpieczeństwa) ---
class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

# --- NOWE MODELE ---

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user') # Nie można wysłać 2 zaproszeń do tej samej osoby

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username}"

class Group(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
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
    
    def amount_per_person(self):
        """Zwraca kwotę przypadającą na jednego uczestnika (równy podział)"""
        count = self.participants.count()
        if count == 0:
            return 0
        return round(self.amount / count, 2)