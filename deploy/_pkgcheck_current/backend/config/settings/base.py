import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

def split_env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, '')
    if not raw.strip():
        return default
    return [item.strip() for item in raw.split(',') if item.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'django_filters',
    'channels',
    # Local apps
    'apps.equipment',
    'apps.monitoring',
    'apps.ai_analysis',
    'apps.quality',
    'apps.safety',
    'apps.users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'zs2_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS
CORS_ALLOWED_ORIGINS = split_env_list('CORS_ALLOWED_ORIGINS', [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
])

# Auth & Session
LOGIN_URL = '/api/users/login/'
SESSION_COOKIE_AGE = 86400  # 1 day
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'

# CSRF
CSRF_TRUSTED_ORIGINS = split_env_list('CSRF_TRUSTED_ORIGINS', [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3001',
    'http://127.0.0.1:3001',
])
CORS_ALLOW_CREDENTIALS = True
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'

# Reverse proxy (for HTTPS deployments behind nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SSO 云南中烟登录
SSO_ENABLED = os.getenv('SSO_ENABLED', 'False').lower() == 'true'
SSO_CLIENT_ID = os.getenv('SSO_CLIENT_ID', '')
SSO_CLIENT_SECRET = os.getenv('SSO_CLIENT_SECRET', '')
SSO_BASE_URL = os.getenv('SSO_BASE_URL', '')
SSO_AUTHORIZE_URL = os.getenv('SSO_AUTHORIZE_URL', '')
SSO_TOKEN_URL = os.getenv('SSO_TOKEN_URL', '')
SSO_USERINFO_URL = os.getenv('SSO_USERINFO_URL', '')
SSO_INTROSPECT_URL = os.getenv('SSO_INTROSPECT_URL', '')
SSO_REDIRECT_URI = os.getenv('SSO_REDIRECT_URI', '')
SSO_SCOPE = os.getenv('SSO_SCOPE', 'openid email profile custom_scope')
SSO_KC_IDP_HINT = os.getenv('SSO_KC_IDP_HINT', 'wechat-work')
SSO_STATE_TTL_SECONDS = int(os.getenv('SSO_STATE_TTL_SECONDS', '300'))
APP_EXTERNAL_BASE_URL = os.getenv('APP_EXTERNAL_BASE_URL', '')

# Media files (for hazard images)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# AI 配置
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:35b')
RAGFLOW_BASE_URL = os.getenv('RAGFLOW_BASE_URL', '')
RAGFLOW_API_KEY = os.getenv('RAGFLOW_API_KEY', '')
RAGFLOW_DATASET_ID = os.getenv('RAGFLOW_DATASET_ID', '')
RAGFLOW_QUALITY_DATASET_ID = os.getenv('RAGFLOW_QUALITY_DATASET_ID', '')
RAGFLOW_SAFETY_DATASET_ID = os.getenv('RAGFLOW_SAFETY_DATASET_ID', '')
