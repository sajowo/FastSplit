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