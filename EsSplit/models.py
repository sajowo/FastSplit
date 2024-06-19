from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,default=None)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    
class Group(models.Model):
    name = models.CharField(max_length=30)
    members = models.ManyToManyField(Person, through='Membership')
    
class Membership(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date_joined = models.DateField()


class Friend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends')
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} (przyjaciel {self.user.username})"

class Bill(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bills')
    participants = models.ManyToManyField(User, related_name='participated_bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    def __str__(self):
        return f'{self.description} - {self.amount}'