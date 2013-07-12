# -*- coding: utf-8 -*-
from django.db import models
import django.contrib.auth.models
from django.core.validators import MinLengthValidator

class Account(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, unique=True, error_messages={
        'unique': u'Такое название счета уже есть в системе.',
        'blank': u'Название счета не должно быть пустым.',
        'max_length': u'Название счета не должно быть более 255 символов длинной.'
    })

class Category(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, unique=True, error_messages={
        'unique': u'Такое название категории уже есть в системе.',
        'blank': u'Название категории не должно быть пустым.',
        'max_length': u'Название категории не должно быть более 255 символов длинной.'
    })


# Тип записи учета - расход доход или перевод
class UType(models.Model):
    name = models.CharField(max_length=255, unique=True)

UTYPE_RASHOD = UType.objects.get(id=1)
UTYPE_DOHOD = UType.objects.get(id=2)
UTYPE_TRANSFER = UType.objects.get(id=3)


class Uchet(models.Model):

    user = models.ForeignKey(django.contrib.auth.models.User)
    date = models.DateField()
    utype = models.ForeignKey(UType)
    sum = models.DecimalField(max_digits=11, decimal_places=2)
    account = models.ForeignKey(Account)
    category = models.ForeignKey(Category)
    comment = models.CharField(max_length=1024)

    def dateDDMMYYYY(self):
        return self.date.strftime('%d.%m.%Y')


# Событие для сохранения в журнале (отслеживаемые события)
class Event(models.Model):

    name = models.CharField(max_length=255, unique=True)


# Константы-события (см. комментарии к ним в базе).
EVENT_VISIT_UCH = Event.objects.get(id=1)
EVENT_VISIT_ANA = Event.objects.get(id=2)
EVENT_VISIT_SET = Event.objects.get(id=3)
EVENT_VISIT_IMP = Event.objects.get(id=4)
EVENT_ADD_UCH = Event.objects.get(id=5)
EVENT_EDT_UCH = Event.objects.get(id=6)
EVENT_DEL_UCH = Event.objects.get(id=7)
EVENT_IMP = Event.objects.get(id=8)
EVENT_ADD_SET = Event.objects.get(id=9)
EVENT_EDT_SET = Event.objects.get(id=10)
EVENT_DEL_SET = Event.objects.get(id=11)


# Журнал событий
class EventLog(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(Event)