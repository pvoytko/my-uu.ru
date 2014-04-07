# -*- coding: utf-8 -*-
from django.db import models
import django.contrib.auth.models
from django.contrib.auth.models import User
import datetime


# Платеж. Создается в момент инициации оплаты в адрес Робокассы, тогда хранит только ID (= номер счета)
# В момент поступления оплаты из сервиса устанавливается дата оплаты и дата активации.
# Дата активации нужна на случай если у юзера уже активирован платеж сейчас, тогда этот надо активировать
# не сразу, а начиная с даты завершения текущего.
class Payment(models.Model):
    sum = models.DecimalField(decimal_places=2, max_digits=5)
    user = models.ForeignKey('auth.User')
    date_created = models.DateTimeField()
    date_payment = models.DateTimeField(null=True)


# ДОбавляем поля в модель юзера
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

            # Тут важно возвращать не пустой список а пустой квери сет, т.к. к нему применяются ордер бай потом и пр.
            # а если пустой список будем возвращать то эксепшен там получим.
            if len(lastDates) == 0:
                return uchetRecords

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

    # Вычисляет дату по которую у юзера оплачено.
    # На основании информации о платежах из базы.
    # Либо None если оплаты нет.
    def getPaidByDate(self):

        # Для этого находим все платежи в базе этого пользователя.
        # Пока реализован алгоритм только если 1 платеж в базе, надо дореаизовать на случай 2-х.
        # В т.ч. если юзер платить до того как кончился перыдущий активированный платеж.
        activatedPayment = Payment.objects.filter(user = self.user, date_payment__isnull = False)
        if activatedPayment.count() == 0:
            return None
        if activatedPayment.count() > 1:
            raise RuntimeError(u'Возникла ситуация нескольких платежей, на которую алгорим не реализован и требуется дореализовать')

        # Зная дату активации и сумму платежа рассчитываем дату по которую режим "Оплаченный".
        return activatedPayment[0].date_payment + datetime.timedelta(days = int(activatedPayment[0].sum))

    # Возвращает количество дней учета для этого юзера (используется на странице "Оплата"
    def getUchetDaysCount(self):
        uchetRecords = Uchet.objects.filter(user = self.user)
        return uchetRecords.values_list('date', flat=True).distinct().count()

    # Возвращает True если пользователь не может вносить новые записи учета без оплаты, т.е. ему нужно оплатить.
    # Метод используется при формировании страницы "Учет". Если метод вернул True, то диалог внесения блокируется.
    def showAddUchetDialog(self):
        return self.getPayModeCodeAndDescr()[0] != UserProfile.PAY_MODE_TRIAL_LIMITED

    # Возвращает True если надо выдать ошибку при попытке сохранить запись учета т.к. ща режиме когда сохранение запрещено.
    def errorOnSaveUchet(self):
        # Когда кончился платный режим, т.е. мы находимся в неоплаченном режиме и достигли ограничения 40 записей,
        # тогда нельзя соранять, а надо показаь ошибку. Но мы даем еще 2 часа право сохранить после этого момента.
        # Зачем? Иначе возможна херовая ошибка, которая будет проявляться следующим образом.
        # Допустим, он открыл страничку в 23-59. Значит флаг на странице установился что вносить записи в диалоге можно.
        # Диалог внесения не блокирован. Но при попытке сохранить на сервере у него будет возникать ошибка сохранения.
        # Ведь сохранять-то он будет уже после 00-00. Чтобы ее не возникало, надо либо сложную клиентскую логику
        # делать отслеживать момент когда истечет время, либо просто разрешить пару часов после истечения срока
        # сохранять запии на сервере. Тогда точно за это время пользователь перегрузит хотя бы раз страницу и
        # диалог внесения будет заблокирован тоже. Вот именно этот второй вариант и реализован, он проще.
        pbd = self.getPaidByDate()
        paidLessThen2HoursAgo = pbd != None and (datetime.datetime.now() - pbd) < datetime.timedelta(hours=2)

        # Аналогично, диалог блокируется при достижении 40 дней учета, а на сервере ошибка - при 45.
        daysUchetLessThen45 = self.getUchetDaysCount() < 45

        # Итог
        return (self.getPayModeCodeAndDescr()[0] == UserProfile.PAY_MODE_TRIAL_LIMITED) and not paidLessThen2HoursAgo and not daysUchetLessThen45


    PAY_MODE_NOT_LIMITED_FOR_USER_4 = 'PAY_MODE_NOT_LIMITED_FOR_USER_4'
    PAY_MODE_NOT_LIMITED = 'PAY_MODE_NOT_LIMITED'
    PAY_MODE_PAID = 'PAY_MODE_PAID'
    PAY_MODE_TRIAL = 'PAY_MODE_TRIAL'
    PAY_MODE_TRIAL_LIMITED = 'PAY_MODE_TRIAL_LIMITED'

    # Возвращает пару - код и текстовое описание.
    # По коду в программе можно проверить в каком сейчас режиме работает юзер.
    # А текст используется чтобы показать текстовое описание пользователю.
    def getPayModeCodeAndDescr(self):

        # Без ограничений режим работал по 7 апреля для меня лично и по 9 апреля всем остальным
        if self.user.id == 4 and (datetime.datetime.now().date() < datetime.date(2014, 4, 7)):
            return (UserProfile.PAY_MODE_NOT_LIMITED_FOR_USER_4, u"Без ограничений по 07.04.2014")
        elif self.user.id != 4 and datetime.datetime.now().date() < datetime.date(2014, 4, 9):
            return (UserProfile.PAY_MODE_NOT_LIMITED, u"Без ограничений по 09.04.2014")

        # Далее если есть действующая оплата, то режим "Оплаченный"
        elif self.getPaidByDate() is not None and datetime.datetime.now().date() <= self.getPaidByDate():
            d = self.getPaidByDate()
            return (UserProfile.PAY_MODE_PAID, u"Оплаченный по " + d.format('%D.%m.%Y') + u". Осталось дней: " + str((datetime.datetime.now().date() - d).days))

        # Если же активной оплаты нет, то если количество дней учета менее 40, то режим - "Пробный"
        elif self.getUchetDaysCount() < 40:
            return (UserProfile.PAY_MODE_TRIAL, u"Пробный. Текущее количество дней учета: {0} из 40".format(self.getUchetDaysCount()))

        # Сюда попадаем если количество дней учета 40 и более, то
        # Пробный "исчерпанный"
        else:
            days = self.getUchetDaysCount()
            return (
                UserProfile.PAY_MODE_TRIAL_LIMITED,
                ('Пробный. Ваше количество дней учета: {0}, максимальное: 40. '  + \
                 'Вы достигли максимальное количество дней учета в режиме работы "Пробный". ' + \
                 'Для внесения новых операций в сервис Вам необходимо оплатить его использование, ' + \
                 'чтобы перейти на режим "Оплаченный".').format(days))


    # Возвращает текстовое описание текущего режима работы с сервисом (на странице "Оплата")
    def getPayModeDescription(self):
        return self.getPayModeCodeAndDescr()[1]



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


# Журнал событий
class EventLog(models.Model):

    EVENT_VISIT_UCH = (1,"Заход на страницу учета")
    EVENT_VISIT_ANA = (2,"Заход на страницу анализа")
    EVENT_VISIT_SET = (3,"Заход на страницу настроек")
    EVENT_VISIT_IMP = (4,"Заход на страницу импорта")
    EVENT_ADD_UCH = (5,"Добавил запись учета")
    EVENT_EDT_UCH = (6,"Изменил запись учета")
    EVENT_DEL_UCH = (7,"Удалил запись учета")
    EVENT_IMP = (8,"Прислал данные для импорта")
    EVENT_ADD_SET = (9,"Добавил счет или категорию")
    EVENT_EDT_SET = (10,"Изменил счет или категорию")
    EVENT_DEL_SET = (11,"Удалил счет или категорию")
    EVENT_UNSUBSCR = (12,"Отписался от рассылки")
    EVENT_SUBSCR = (13,"Подписался на рассылку")

    EVENT_VISIT_PAY =               (14, "Заход на страницу оплаты")
    EVENT_DO_ORDER =                (15, "Нажал кнопку 'Оплатить'")
    EVENT_ROBOKASSA_PAY_NOTIFY =    (16, "Пришла оплата от ROBOKASSA")
    EVENT_ZPAYMENT_PAY_NOTIFY =     (21, "Пришла оплата от Z-PAYMENT")

    EVENT_VISIT_EXP =       (17, "Заход на страницу экспорта")
    EVENT_VISIT_BEGIN =     (18, "Заход на страницу начало")
    EVENT_LOGIN =           (19, "Авторизовался")

    EVENT_EXP =             (20, "Просмотрел данные для экспорта")
    # NEXT_ID = 22

    user = models.ForeignKey(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)
    event2 = models.IntegerField()

    @property
    def event_name(self):
        for a in dir(EventLog):
            if a.startswith('EVENT_'):
                if getattr(self, a)[0] == self.event2:
                    return getattr(self, a)[1]
        raise RuntimeError('Ошибка получения описания события. В базе соранен код события #{0}, но константа EVENT в классе EventLog с таким значением кода не найдена.'.format(self.event2))


# Заполняется если юзер отписался
class Unsubscribe(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)


# Заполняется в момент когда юзеру направлено первое письмо-запрос на обратную связь (больше высылать не надо).
class FeedbackRequested(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)