""" Esse Model está armazenando as configurações de 2FA (TOTP) dos usuários Marcos.
Então ele vai atender ao requisito de autenticação de dois fatores implementada.
"""
from django.db import models
from django.conf import settings
import pyotp
import qrcode
import base64
from io import BytesIO


class Configuracao2FA(models.Model):
    """
    Aqui vai armazenar a chave secreta TOTP e status do 2FA para cada usuário.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='config_2fa'
    )
    chave_secreta = models.CharField(max_length=32, unique=True)
    ativado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        """Isso aqui gera chave secreta automaticamente se não existir."""
        if not self.chave_secreta:
            self.chave_secreta = pyotp.random_base32()
        super().save(*args, **kwargs)

    def get_totp_uri(self):
        """Aqui retorna a URI para configuração no Google Authenticator."""
        totp = pyotp.TOTP(self.chave_secreta)
        return totp.provisioning_uri(
            name=self.usuario.email,
            issuer_name='ERP Escola Profissionalizante'
        )

    def get_qrcode_base64(self):
        """Aqui gera QR Code em base64 para exibição no template."""
        uri = self.get_totp_uri()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def verify_token(self, token):
        """Aqui verifica se o token TOTP é válido."""
        totp = pyotp.TOTP(self.chave_secreta)
        return totp.verify(token, valid_window=1)  # permite 30s de tolerância

    def __str__(self):
        return f"2FA - {self.usuario.email} ({'Ativo' if self.ativado else 'Inativo'})"