# -*- coding: utf-8 -*-
# Django settings for my_uu project.

import os
import datetime


# Разработческая машина (не боевая)
IS_DEVELOPER_COMP = os.path.dirname(os.path.abspath(__file__)) == "D:\\GitRepos\\my-uu.ru\\my_uu"

# Тут хранится корневая папка проекта как юникод-строка. Важно юникод. Чтоб не было проблем с русскими буквами.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(unicode(__file__))))


# ============
# Тут включаются настройки, специфичные для каждой копии сайта
# ============

# Путь до папки копии к примеру /home/webapp/installab.com_8001
INSTANCE_ROOT = PROJECT_DIR

# Далее перечислены все флаги, с помощью которых выбирается то или иное поведение различных копий сайтов.
#
# INSTANCE_SPECIFIC_DJANGO_DEBUG
#     В какое значение установить DEBUG переменную Джанго (желтые страницы с ошибками 500).
#     True - показывать желтые страницы (для копий программистов)
#     False - не показывать (вместо этого показаь 500.html шаблон) - для боевой копии
#
# INSTANCE_SPECIFIC_PAID_FOR_DATE
#     Возврвщает по какую дату оплачено. Используется в режиме отладки на дебаг-копии.
#
# INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES
#     Надо ли отображать кнопку "Добавить емейл-шаблон" и "Удалить" в разделе "Шаблоны сообщений".
#     Нужно для программиста - для добавления новых шаблонов.
#     True - показывать (используется на прог-копии). False - не надо показывать (на боевой).
#
# INSTANCE_SPECIFIC_DJANGO_DEBUG_STATIC
#     Надо ли в Урл Паттернс Джанги добавить media и static и обслуживать их Джангой
#     True - да, используется для копии сайта программистов
#     False - нет, используется для демонстрационной и боевой копии
#     (там nginx обрабатывает статику и STATIC_URL в этом случае будет такой чтобы указывать на nginx)
#
# Все копии программистов. Что значает эта секция см. комменты чуть выше.
if INSTANCE_ROOT.startswith('/var/www/pvoy_myuu_8') :
    INSTANCE_SPECIFIC_DJANGO_DEBUG = True
    INSTANCE_SPECIFIC_PAID_FOR_DATE = None
    INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES = True
    INSTANCE_SPECIFIC_DJANGO_DEBUG_STATIC = True

# Боевая копия
elif INSTANCE_ROOT == '/var/www/pvoy_myuu':
    INSTANCE_SPECIFIC_DJANGO_DEBUG = False
    INSTANCE_SPECIFIC_PAID_FOR_DATE = None
    INSTANCE_SPECIFIC_ADD_EMAIL_TEMPLATES = False
    INSTANCE_SPECIFIC_DJANGO_DEBUG_STATIC = False

# Если тут возник эксепшен, значит предпринята попытка запустить новую копию сайта.
# Для этой новой копии сайта надо прописать настройки, специфичные для этой копии, по аналогии с секциями выше.
# Детальное описание каждой настройки и ее значений см. чуть выше
else:
    print(INSTANCE_ROOT)
    print(u'Попытка запустить новую копию сайта. ')
    print(u'Укажите настройки для новой копии сайта в файле settings.py')
    print(u"Путь до копии сайта: " + INSTANCE_ROOT)
    print(u'Путь до settings.py' + __file__)
    raise RuntimeError("See above.")

# ============
# Конец
# ============


DEBUG = INSTANCE_SPECIFIC_DJANGO_DEBUG
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Павел Войтко', 'pvoytko@gmail.com'),
)


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
ALLOWED_HOSTS = [
    'my-uu.ru',
    'www.my-uu.ru',
    '5.200.55.208',
]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Moscow'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'ru-Ru'

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

# Статику брать из папки /static/ на боевом, а на прог-копии - и папок app/static
# media Брать из /media/ на боевом, а на прог-копии - из /media/ боевого.
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_DIR, '../pvoy_myuu', 'media')
if INSTANCE_SPECIFIC_DJANGO_DEBUG_STATIC:
    STATICFILES_DIRS = [
        # Тут важно без начального слеша, т.е. нельзя /static/, т.к. os.path.join возвращает
        # относительный путь а не абсолютный т.е. путь вида "static/" она и вернет и если
        # начальный слеш то при нахождении статики этот путь уже будет считаться абсолютным и
        # т.к. его нет в системе и статика находиться не будет.
        os.path.join(PROJECT_DIR, "static/"),
    ]
else:
    STATICFILES_DIRS = []
    STATIC_ROOT = os.path.join(PROJECT_DIR, 'static')



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


from django.conf import global_settings
TEMPLATE_CONTEXT_PROCESSORS = list(global_settings.TEMPLATE_CONTEXT_PROCESSORS) + [
    'django.core.context_processors.request',
    'django.core.context_processors.static',
]


INSTALLED_APPS = (

    # Мой УУ, чтоб шаблоны находились, должно быть до DAB
    'my_uu',
    'pvl_send_email',

    # Это dab админка
    'django_admin_bootstrapped',

    # Страница тестового поста
    'bootstrapform',

    # Убрать cdn
    'pvl_static_mtime',

    # django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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
        },
        # Эта секция обеспечивает вывод в консоль ошибок (удобно при отладке)
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # Эта секция обеспечивает вывод в консоль ошибок (удобно при отладке)
        'django.request': {
            'handlers':['console'],
            'level':'DEBUG',
            'propagate': True,
        },
    }
}



# Подкраска цветом сообщений в DAB админке.
# исочник - https://github.com/django-admin-bootstrapped/django-admin-bootstrapped
from django.contrib import messages
MESSAGE_TAGS = {
    messages.SUCCESS: 'alert-success success',
    messages.WARNING: 'alert-warning warning',
    messages.ERROR: 'alert-danger error',
    messages.INFO: 'alert-info error',
}


# Это папка в ней кешируется файлы cdn
# Ш-80
PVL_CDN_TO_STATIC_DIR_CACHE_NAME = ".cache_dir_pvl_cdn_to_static"
PVL_CDN_TO_STATIC_IS_SAVE_TO_STATIC_ROOT = False
STATICFILES_DIRS.append(
    os.path.join(INSTANCE_ROOT, PVL_CDN_TO_STATIC_DIR_CACHE_NAME)
)