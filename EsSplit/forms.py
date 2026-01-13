from django import forms
from django.contrib.auth.models import User
#from django_recaptcha.fields import ReCaptchaField
#from django_recaptcha.widgets import ReCaptchaV2Checkbox
import re

# --- Formularz Rejestracji ---
class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, 
        label="Hasło",
        # Usunąłem help_text, bo komunikaty błędów będą teraz jasne
    )
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potwierdź hasło")
    
    #captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']
        # Usunąłem 'username' z fields, bo i tak generujesz go automatycznie w views.py!
        # Jeśli jednak chcesz, żeby użytkownik sam wpisywał nick, przywróć 'username'.

    # --- ULEPSZONA WALIDACJA HASŁA ---
    def clean_password(self):
        password = self.cleaned_data.get('password')
        errors = [] # Lista na błędy
        
        if len(password) < 8:
            errors.append("Hasło jest za krótkie (min. 8 znaków).")
        
        if not any(char.isdigit() for char in password):
            errors.append("Brakuje cyfry (0-9).")
            
        if not any(char.isupper() for char in password):
            errors.append("Brakuje dużej litery (A-Z).")
            
        if not re.search(r"[ !#$%&'()*+,-./:;<=>?@[\]^_`{|}~]", password):
             errors.append("Brakuje znaku specjalnego (np. !, @, #, $).")

        # Jeśli są błędy, wyrzucamy wszystkie naraz
        if errors:
            raise forms.ValidationError(errors)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Hasła nie są identyczne.")
        return cleaned_data

# --- Formularz Logowania ---
class LoginForm(forms.Form):
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    #captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)