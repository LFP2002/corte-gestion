from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import Usuario


class UsuarioCrearForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('first_name', 'username', 'email', 'rol')
        labels = {'first_name': 'Nombre', 'username': 'Usuario'}


class UsuarioEditarForm(forms.ModelForm):
    password = forms.CharField(
        label='Nueva contraseña (vacío = no cambiar)', required=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), min_length=8)

    class Meta:
        model = Usuario
        fields = ('first_name', 'username', 'email', 'rol', 'is_active')
        labels = {'first_name': 'Nombre', 'username': 'Usuario'}

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        u = super().save(commit=False)
        if self.cleaned_data.get('password'):
            u.set_password(self.cleaned_data['password'])
        if commit:
            u.save()
        return u
