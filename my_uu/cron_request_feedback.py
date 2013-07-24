# -*- coding: utf-8 -*-
import my_uu.models
import django.contrib.auth.models

# Скрипт вызывается по cron раз в 5 минут.
# Задача скрипта - выслать емейл всем юзерам кому еще не выслан и кто только что завершил знакомиться с сервисом.
# критерий - последнее событие по нему было более 15 минут назад.

users = django.contrib.auth.models.User.objects.filter(feedbackrequested = None)
for u in users:
    print u.id, u.email
