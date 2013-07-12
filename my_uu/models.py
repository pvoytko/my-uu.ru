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

    RASHOD = 1
    DOHOD = 2
    PEREVOD = 3


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

    VISIT_UCH = 1
    VISIT_ANA = 2
    VISIT_SET = 3
    VISIT_IMP = 4
    ADD_UCH = 5
    EDT_UCH = 6
    DEL_UCH = 7
    IMP = 8
    ADD_SET = 9
    EDT_SET = 10
    DEL_SET = 11


# Журнал событий
class EventLog(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(Event)