# -*- coding: utf-8 -*-
from django.db import models
import django.contrib.auth.models
from django.contrib.auth.models import User


# ДОбавляем поле HTTP_REFERER в модель юзера
class UserProfile(models.Model):
    user = models.OneToOneField(User)

    # Значение берется из куки и выставляется сюда (если не задано)
    http_referer = models.CharField(max_length = 1024, blank = True, null = True)

    # Подтверждение емейла дата и время нажатия ссылки активации (шоб быть уверенным что юзер получает письма)
    # email_confirmed = models.DateTimeField(default=None, null=True)

    # Пеиод за который юзер задал показывать записи учета.
    # В этом поле может храниться месяц в формате 'YYYY-MM' или одно из спец. значений 'last3' и 'last30'
    VIEW_PERIOD_CODE_LAST3 = 'last3'
    VIEW_PERIOD_CODE_LAST30 = 'last30'
    VIEW_PERIOD_CODE_CHOICES=(
        (VIEW_PERIOD_CODE_LAST30, 'последние 30 дней'),
        (VIEW_PERIOD_CODE_LAST3, 'последние 3 дня'),
    )
    view_period_code = models.CharField(max_length=10, default='last3')

    # Фильтрует записи учета согласно выбранному фильтру дат
    def _filterUchetByViewPeriod(self, uchetRecords):

        import datetime
        import dateutil.relativedelta

        # Спец. значения
        if self.view_period_code in (UserProfile.VIEW_PERIOD_CODE_LAST3, UserProfile.VIEW_PERIOD_CODE_LAST30):
            lastIndex = 3 if self.view_period_code == UserProfile.VIEW_PERIOD_CODE_LAST3 else 30
            lastDates = list(uchetRecords.values_list('date', flat=True).distinct().order_by('-date')[0:lastIndex])
            if len(lastDates) == 0:
                return []
            return uchetRecords.filter(date__gte = lastDates[-1])

        # Месяц
        else:
            year, month = self.view_period_code.split('-')
            year, month = int(year), int(month)
            d1 = datetime.date(year, month, 1)
            d2 = d1 + dateutil.relativedelta.relativedelta(months=1) - datetime.timedelta(days=1)
            return uchetRecords.filter(date__gte = d1, date__lte = d2)

    # Возвращает список списков из 2 элементов: код месяца (YYYY-MM) и русскоязычное "январь 2014"
    # Это для поля view_period_code
    def getUchetMonthSet(self):
        months = self.user.uchet_set.dates('date', 'month')
        def verboseMonth(d):
            months = [
                u'январь', u'февраль', u'март', u'апрель', u'май', u'июнь',
                u'июль', u'август', u'сентябрь', u'октябрь', u'ноябрь', u'декабрь'
                ]
            return months[d.month-1] + " " + str(d.year)
        return [["{0}-{1:02}".format(m.year, m.month), verboseMonth(m)] for m in months]

    # Возвращает UchetRecords для этого юзера причем только из периода view_period_code
    # Используется для получения записей учета для отображения на главной.
    # Все показывать, если их много, то долго. Потому по периодам приходится разделить.
    def getUchetRecordsInViewPeriod(self):
        urecs = Uchet.objects.filter(user=self.user)
        return self._filterUchetByViewPeriod(urecs).order_by('date', '-utype', 'id')


# Счет
class Account(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, error_messages={
        'blank': u'Название счета не должно быть пустым.',
        'max_length': u'Название счета не должно быть более 255 символов длинной.'
    })

class Category(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, error_messages={
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
    UNSUBSCR = 12
    SUBSCR = 13
    # При добавлении сюда констант надо:
    # 1 добавить примечание в БД с этим ID
    # 2 создать python manage.py dumpdata --indent=4 my_uu.Event > my_uu/fixtures/event_initial.json
    # 3 загрузить ее manage.py loaddata event_initial.json на боевом


# Журнал событий
class EventLog(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(Event)


# Заполняется если юзер отписался
class Unsubscribe(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)


# Заполняется в момент когда юзеру направлено первое письмо-запрос на обратную связь (больше высылать не надо).
class FeedbackRequested(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)