from django.db import models
from django.contrib.auth.models import User

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=None)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Person, through='Membership')
    
class Membership(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date_joined = models.DateField()

# --- ZMIANA TUTAJ ---
class Friend(models.Model):
    # Kto dodaje (Ty)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends_added')
    
    # Kogo dodano (Link do konta kolegi)
    friend_account = models.ForeignKey(User, on_delete=models.CASCADE, related_name='added_by_others')
    
    # Data dodania (opcjonalnie)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Zabezpieczenie: nie możesz dodać tej samej osoby dwa razy
        unique_together = ('user', 'friend_account')

    def __str__(self):
        return f"{self.user.username} -> {self.friend_account.username}"

class Bill(models.Model):
    # Definiujemy możliwe opcje (dla bazy danych i dla wyświetlania)
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Oczekujący'
        REJECTED = 'REJECTED', 'Odrzucony'
        PAID = 'PAID', 'Sfinalizowany'

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bills')
    participants = models.ManyToManyField(User, related_name='participated_bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(default="Rachunek")
    
    # NOWE POLE:
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    def __str__(self):
        return f'{self.description} - {self.amount} ({self.get_status_display()})'