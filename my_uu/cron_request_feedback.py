# -*- coding: utf-8 -*-

# Скрипт вызывается по cron раз в 5 минут.
# Задача скрипта - выслать емейл всем юзерам кому еще не выслан и кто только что завершил знакомиться с сервисом.
# критерий - последнее событие по нему было более 120 минут назад.

# Флаги
import os, sys
IS_REAL_COMP = os.path.dirname(os.path.abspath(__file__)) == "/home/users2/p/pvoytko/domains/my-uu.ru/my_uu"
PROJECT_DIR = os.path.join(os.path.dirname(unicode(__file__)), "..")

# Сам скрипт
sys.path.insert(0, PROJECT_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'my_uu.settings'
import django.contrib.auth.models
from django.db.models import Max, Min
import datetime
import my_uu.utils


# Выборка юзеров кому еще не выслан емейл
# Важно перед запросом сделать import models чтобы поле feedbackrequested для модели auth.User
# добавилось Джангой. Если не импортить, то поле не добавится и будет не найдено (ошибка на боевом счервере
# толкьо проявлялась почему-то)
import my_uu.models
users = django.contrib.auth.models.User.objects.filter(feedbackrequested = None)

# Перебираем
for u in users:

    # Сценарий: юзер зашел 1 раз на 5-10 мин и ушел и больше не вернулся. В этом случае - узнать почему.
    # Т.е. Если дата регистрации < 3 дней.
    # Если последнее событие более 2 дней назад.
    # То выслать вопрос.
    # Если ни одного события то тоже пропускаем ничего не делаем спрашивать у такого смысла нет.
    maxDateTime = u.eventlog_set.all().aggregate(max_datetime = Max('datetime'))['max_datetime']
    minDateTime = u.eventlog_set.all().aggregate(min_datetime = Min('datetime'))['min_datetime']
    if (maxDateTime is not None) and ((datetime.datetime.now()-maxDateTime) > datetime.timedelta(0, 2 * 24 * 60 * 60)) and ((datetime.datetime.now()-minDateTime) < datetime.timedelta(0, 3 * 24 * 60 * 60)) :

        # То высылаем и сохраняем в БД что выслали
        # Печатаем чтобы когда отладочный запуск из консоли - было видно кому из юзеров отправляется.
        print u.id, u.email
        my_uu.utils.sendFeedbackRequest(u)
        my_uu.models.FeedbackRequested.objects.create(user = u)