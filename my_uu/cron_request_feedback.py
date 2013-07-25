# -*- coding: utf-8 -*-

# Скрипт вызывается по cron раз в 5 минут.
# Задача скрипта - выслать емейл всем юзерам кому еще не выслан и кто только что завершил знакомиться с сервисом.
# критерий - последнее событие по нему было более 15 минут назад.

# Активация энвайронмента (чтобы находилась джанга и другие модули на боевом сервере)
import os, sys
IS_REAL_COMP = os.path.dirname(os.path.abspath(__file__)) == "/home/users2/p/pvoytko/domains/my-uu.ru/my_uu"
PROJECT_DIR = os.path.join(os.path.dirname(unicode(__file__)), "..")
if IS_REAL_COMP:
    virtual_env = os.path.expanduser('~/virtualenv/MyEnv')
    activate_this = os.path.join(virtual_env, 'bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

# Сам скрипт
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'my_uu.settings'
import django.contrib.auth.models
from django.db.models import Max

import datetime

import my_uu.utils


# Выборка юзеров кому еще не выслан емейл
# Важно перед запросом сделать import models чтобы поле feedbackrequested для модели auth.User
# добавилось Джангой. Если не импортить, то поле не добавится и будет не найдено (ошибка на боевом счервере
# толкьо проявлялась почему-то)
import models
users = django.contrib.auth.models.User.objects.filter(feedbackrequested = None)

# Перебираем
for u in users:

    # Если последнее событие более 15 мин назад
    # Если ни одного события то тоже пропускаем ничего не делаем спрашивать у такого смысла нет.
    maxDateTime = u.eventlog_set.all().aggregate(max_datetime = Max('datetime'))['max_datetime']
    if (maxDateTime is not None) and ((datetime.datetime.now()-maxDateTime) > datetime.timedelta(0, 15 * 60)):

        # То высылаем и сохраняем в БД что выслали
        # Печатаем чтобы когда отладочный запуск из консоли - было видно кому из юзеров отправляется.
        print u.id, u.email
        my_uu.utils.sendFeedbackRequest(u)
        my_uu.models.FeedbackRequested.objects.create(user = u)
