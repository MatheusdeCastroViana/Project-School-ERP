from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

Usuario = get_user_model()


class SolicitarRecuperacaoForm(forms.Form):  
    email = forms.EmailField(
        label='E-mail',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'auth-field__input',
            'placeholder': 'seu@email.com',
            'autocomplete': 'email'
        }),
        help_text='Informe o e-mail cadastrado no sistema.'
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        try:
            usuario = Usuario.objects.get(email=email)
            self.usuario_encontrado = usuario
        except Usuario.DoesNotExist:
            self.usuario_encontrado = None
        
        return email


class NovaSenhaForm(forms.Form):  
    senha1 = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs={
            'class': 'auth-field__input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    senha2 = forms.CharField(
        label='Confirme a nova senha',
        widget=forms.PasswordInput(attrs={
            'class': 'auth-field__input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        })
    )
    
    def clean_senha1(self):
        senha = self.cleaned_data.get('senha1')
        
        if senha:
            try:
                validate_password(senha)
            except ValidationError as e:
                raise forms.ValidationError(list(e.messages))
        
        return senha
    
    def clean(self):
        cleaned_data = super().clean()
        senha1 = cleaned_data.get('senha1')
        senha2 = cleaned_data.get('senha2')
        
        if senha1 and senha2 and senha1 != senha2:
            raise forms.ValidationError({
                'senha2': 'As senhas não coincidem. Por favor, digite-as novamente.'
            })
        
        return cleaned_data