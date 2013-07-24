# -*- coding: utf-8 -*-

# Скрипт вызывается по cron раз в 5 минут.
# Задача скрипта - выслать емейл всем юзерам кому еще не выслан и кто только что завершил знакомиться с сервисом.
# критерий - последнее событие по нему было более 15 минут назад.

# Подключение Джанги
import os, sys
sys.path.insert(0, '../')
os.environ['DJANGO_SETTINGS_MODULE'] = 'my_uu.settings'

# Сам скрипт
import django.contrib.auth.models
from django.db.models import Max
from django.conf import settings

import datetime

import my_uu.emails


# Защита от рассылки спама юзерам с локальной машины
# Если убрать эту проверку то надо отправку писем заблокировать.
assert settings.IS_DEVELOPER_COMP == False, u'Ошибка, скрипт должен запускаться только на боевом сервере.'

# Выборка юзеров кому еще не выслан емейл
users = django.contrib.auth.models.User.objects.filter(feedbackrequested = None)

# Перебираем
for u in users:

    # Если последнее событие более 15 мин назад
    # Если ни одного события то тоже пропускаем ничего не делаем спрашивать у такого смысла нет.
    maxDateTime = u.eventlog_set.all().aggregate(max_datetime = Max('datetime'))['max_datetime']
    if (maxDateTime is not None) and ((datetime.datetime.now()-maxDateTime) > datetime.timedelta(0, 15 * 60)):

        # То высылаем и сохраняем в БД что выслали
        print u.id, u.email
        my_uu.emails.sendFeedbackRequest(u)
        my_uu.models.FeedbackRequested.objects.create(user = u)
