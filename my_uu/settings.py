# -*- coding: utf-8 -*-
# Django settings for my_uu project.

import os

# Разработческая машина (не боевая)
IS_DEVELOPER_COMP = os.path.dirname(os.path.abspath(__file__)) == "D:\\HgRepos\\my-uu.ru\\my_uu"

# Тут хранится корневая папка проекта как юникод-строка. Важно юникод. Чтоб не было проблем с русскими буквами.
PROJECT_DIR = os.path.join(os.path.dirname(unicode(__file__)), "..")

# Блок настроек в зависимости от инстанса сайта включаем те или иные его части
UU_EMAIL_BACKEND_TYPE = 'filebased' if IS_DEVELOPER_COMP else 'jino'

DEBUG = IS_DEVELOPER_COMP
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Павел Войтко', 'pvoytko@gmail.com'),
)

# Отправка емейлов
if UU_EMAIL_BACKEND_TYPE == 'filebased':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.path.join(PROJECT_DIR, 'emails')
elif UU_EMAIL_BACKEND_TYPE == 'jino':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.jino.ru'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = 'support@my-uu.ru'
    EMAIL_HOST_PASSWORD = 'JqhGC9I2'
else:
    raise RuntimeError(u'Неподдерживаемое значыение UU_EMAIL_BACKEND_TYPE "{0}".'.format(UU_EMAIL_BACKEND_TYPE))

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'pvoytko',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'pvoytko',
        'PASSWORD': 'zQB5NDos',
        'HOST': '127.0.0.1',       # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['my-uu.ru', 'www.my-uu.ru']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Moscow'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru-ru'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# Эту настройку я выставил в False
# Если оставить ее True, то в БД хранится время минус 4 часа от текущего у меня на часх.
# Видимо Джанга нормализует к UTC время. Мне это нахрен не надо.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

CSRF_COOKIE_NAME = "XSRF-TOKEN"

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
# STATIC_ROOT = os.path.join(APP_ROOT, '../')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(APP_ROOT, '../static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '4n250zay-)_0h^^#qc3d(c93&8sb-qzfyyx#d7yccm_!o-du!h'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'my_uu.middleware.AngularCSRFRename',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'my_uu.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'my_uu.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'my_uu'
)


# Добавляем поле к классу юзеров
AUTH_PROFILE_MODULE = 'my_uu.UserProfile'


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
