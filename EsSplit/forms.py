from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
import re

# --- Formularz Rejestracji ---
class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, 
        label="Hasło",
        # Usunąłem help_text, bo komunikaty błędów będą teraz jasne
    )
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potwierdź hasło")
    
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password']
        # Usunąłem 'username' z fields, bo i tak generujesz go automatycznie w views.py!
        # Jeśli jednak chcesz, żeby użytkownik sam wpisywał nick, przywróć 'username'.

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            return email

        # Django's default User does not enforce unique email.
        # Enforce it here to avoid ambiguous logins and MultipleObjectsReturned.
        exists = (
            User.objects
            .filter(email__iexact=email)
            .exclude(pk=getattr(self.instance, 'pk', None))
            .exists()
        )
        if exists:
            raise forms.ValidationError("Konto z tym adresem e-mail już istnieje.")
        return email

    # --- ULEPSZONA WALIDACJA HASŁA ---
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Dodatkowe wymagania: wielka litera i znak specjalny
        errors = []
        
        if not any(char.isupper() for char in password):
            errors.append("Hasło musi zawierać co najmniej jedną wielką literę (A-Z).")
            
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):
            errors.append("Hasło musi zawierać co najmniej jeden znak specjalny (np. !, @, #, $).")

        if errors:
            raise forms.ValidationError(errors)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Hasła nie są identyczne.")
        
        # Walidacja hasła z danymi użytkownika (dla UserAttributeSimilarityValidator)
        if password:
            # Tworzymy tymczasowy obiekt użytkownika z danymi z formularza
            temp_user = User(
                first_name=cleaned_data.get('first_name', ''),
                last_name=cleaned_data.get('last_name', ''),
                email=cleaned_data.get('email', ''),
                username=cleaned_data.get('email', '')  # username będzie generowany z email
            )
            try:
                validate_password(password, user=temp_user)
            except ValidationError as e:
                self.add_error('password', e.messages)
        
        return cleaned_data

# --- Formularz Logowania ---
class LoginForm(forms.Form):
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)