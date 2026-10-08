from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import hashlib
import hmac
from functools import lru_cache


class ErroDecifragem(Exception):
    pass


@lru_cache(maxsize=1)
def _obter_fernet():
    configuradas = getattr(settings, "FIELD_ENCRYPTION_KEYS", [])
    chaves = [c.strip() for c in configuradas if c and c.strip()]
    if not chaves:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS não está configurada.")
    try:
        return MultiFernet([Fernet(c) for c in chaves])
    except (ValueError, TypeError):
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEYS contém uma chave inválida."
        ) from None

# cifrar token
def cifrar(texto):
    return _obter_fernet().encrypt(texto.encode("utf-8")).decode("ascii")

# decifrar token
def decifrar(token):
    try:
        return _obter_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError):
        raise ErroDecifragem("Falha ao decifrar o valor.") from None

# rotacionar token
def rotacionar(token):
    try:
        return _obter_fernet().rotate(token.encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeError):
        raise ErroDecifragem("Falha ao decifrar o valor.") from None

# hmac pro cpf
def indice_cego(texto):
    chave = getattr(settings, "BLIND_INDEX_KEY", "")
    if len(chave) < 32:
        raise ImproperlyConfigured(
            "BLIND_INDEX_KEY não está configurada ou tem menos de 32 caracteres."
        )
    return hmac.new(
        chave.encode("utf-8"), texto.encode("utf-8"), hashlib.sha256
    ).hexdigest()