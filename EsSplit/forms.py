from django import forms
from django.contrib.auth.models import User
from .models import Friend

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']

class FriendForm(forms.ModelForm):
    class Meta:
        model = Friend
        fields = ['name']