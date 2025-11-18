from django import forms
from django.contrib.auth.models import User
from .models import Friend, Person # Upewnij się, że importujesz modele

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

# --- TU BYŁ BŁĄD ---
class FriendForm(forms.ModelForm):
    class Meta:
        model = Friend
        # Wcześniej było: fields = ['name']
        # Teraz 'name' nie istnieje. Zmieniamy na 'friend_account' lub '__all__'
        # Ale skoro dodajemy znajomych przez wyszukiwarkę, ten formularz jest teraz trochę zbędny.
        # Żeby jednak naprawić błąd, wpiszmy poprawne pole:
        fields = ['friend_account']