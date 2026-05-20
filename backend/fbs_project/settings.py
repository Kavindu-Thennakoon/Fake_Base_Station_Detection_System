# fbs_project/settings.py

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-in-production-fbs-2026'

DEBUG = True

ALLOWED_HOSTS = ['*']

# ===== INSTALLED APPS =====
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
    # Your apps
    'detection',
    'alerts',
    'analytics',
    'accounts',
]

# ===== MIDDLEWARE =====
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',        # MUST BE FIRST
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fbs_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fbs_project.wsgi.application'

# ===== DATABASE =====
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ===== REST FRAMEWORK =====
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Open for dev, lock down later
    ],
    
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": 50,

}

# ===== CORS (Allow React frontend) =====
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",     # Vite React dev server
    "http://127.0.0.1:5173",
]


# Set to False when ml_service scripts are available on this machine
ML_DEMO_MODE = True


# ===== ML SERVICE PATHS =====
ML_SERVICE_DIR = os.path.join(BASE_DIR, '..', 'ml_service')
ML_MODEL_DIR = os.path.join(ML_SERVICE_DIR, 'model', 'v4_model')
ML_OUTPUT_DIR = os.path.join(ML_SERVICE_DIR, 'output')
ML_SCRIPTS_DIR = os.path.join(ML_SERVICE_DIR, 'scripts')
ML_DATA_DIR = os.path.join(ML_SERVICE_DIR, 'data')

# ===== MEDIA (for CSV uploads) =====
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Colombo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'