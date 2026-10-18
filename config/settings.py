from pathlib import Path
from decouple import config, Csv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  
    'usuarios',
    'funcionarios',
    'dashboard',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'anymail',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'usuarios.middleware.Exigir2FAMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'config' / 'templates'],  
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.menu_lateral',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}
# Expiração de sessão por inatividade
SESSION_COOKIE_AGE = 1800  
SESSION_SAVE_EVERY_REQUEST = True

# Hasher de senha Argon2id como primeira opção
# PBKDF2 como segunda opção
PASSWORD_HASHERS = [
    'usuarios.hashers.UsuarioArgon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

LOGIN_MAX_TENTATIVAS = 5
LOGIN_BLOQUEIO_MINUTOS = 15

AUTHENTICATION_BACKENDS = [
    'usuarios.backends.UsuarioBackend', 
    'allauth.account.auth_backends.AuthenticationBackend',  
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = "usuarios.Usuario"

ACCOUNT_USER_MODEL_USERNAME_FIELD = None 
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"  
LOGIN_REDIRECT_URL = '/dashboard/' 
LOGOUT_REDIRECT_URL = '/accounts/login/'

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']  

# CONFIGURAÇÕES DE E-MAIL

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

EMAIL_HOST = config('EMAIL_HOST', default='sandbox.smtp.mailtrap.io')
EMAIL_PORT = config('EMAIL_PORT', default=2525, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='erp@escolaprofissionalizante.com.br')
EMAIL_TIMEOUT = 10

# LOGS DE AUDITORIA

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_seguranca': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'auditoria_seguranca.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'auditoria_seguranca': {
            'handlers': ['file_seguranca', 'console'], 
            'level': 'INFO',
            'propagate': False,
        },
    },
}

OTP_LOGIN_URL = '/usuarios/verify-2fa/'
ACCOUNT_ADAPTER = 'usuarios.adapters.Custom2FAAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'usuarios.adapters.SocialAccountAdapterFechado'

TOKEN_RECUPERACAO_EXPIRACAO_HORAS = 24
LOGIN_URL = '/accounts/login/'

FIELD_ENCRYPTION_KEYS = config('FIELD_ENCRYPTION_KEYS', default='', cast=Csv())
BLIND_INDEX_KEY = config('BLIND_INDEX_KEY', default='')

# CONFIGURAÇÕES DE SEGURANÇA DE TRANSPORTE (HTTPS/TLS)

if not DEBUG:
    # Redireciona todas as requisições HTTP para HTTPS automaticamente
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS (HTTP Strict Transport Security)
    # Informa ao navegador que o site só deve ser acessado via HTTPS por um período de 1 ano (31536000 segundos)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Irá garantir que cookies de sessão e CSRF só trafeguem em conexões seguras
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Irá proteger cabeçalhos de segurança
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
else:
    # Configurações para o nosso ambiente de desenvolvimento
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
