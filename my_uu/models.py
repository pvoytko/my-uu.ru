# -*- coding: utf-8 -*-
from django.db import models
import django.contrib.auth.models
from django.contrib.auth.models import User
import datetime
import utils
import plogic
from django.contrib import admin


# Роль юзера - либо админ, либо обычный.
# Возвращается из функции getUserRole.
UROLE_ADMIN = 'UROLE_ADMIN'
UROLE_USER = 'UROLE_USER'


# Платеж. Создается в момент инициации оплаты в адрес Робокассы, тогда хранит только ID (= номер счета)
# В момент поступления оплаты из сервиса устанавливается дата оплаты и дата активации.
# Дата активации нужна на случай если у юзера уже активирован платеж сейчас, тогда этот надо активировать
# не сразу, а начиная с даты завершения текущего.
class Payment(models.Model):
    sum = models.DecimalField(decimal_places=2, max_digits=5)
    user = models.ForeignKey('auth.User')
    date_created = models.DateTimeField()
    date_payment = models.DateTimeField(null=True)

    # Количество оплаченных дней
    days = models.PositiveIntegerField()

    # Дата, начиная с которой этот платеж начинает действовать. Заполняется при получении оплаты.
    date_from = models.DateField(null=True)

    # Дата, по которую включительно действует этот платеж. Заполняется при получении оплаты.
    date_to = models.DateField(null=True)

    # Код способа оплаты из Z-PAYMENT. Заполняется при получении оплаты.
    zpayment_type_code = models.CharField(max_length=50, null = True)

    # Сумма, которую фактически получает магазин (за вычетом комиссии платежного шлюза).
    sum_seller = models.DecimalField(decimal_places=2, max_digits=5, null=True)

    # Дата в формате "11 апр 2014 15:45" для отображения на странице "Оплата"
    @property
    def date_payment_formatted(self):
        return utils.formatDTWithYearAndTime(self.date_payment)

    # Сумма в формате "30 р." для оторажения на странице "Оплата"
    @property
    def sum_formatted(self):
        return utils.formatMoneyValue(self.sum)

    # Дата в формате "11 мар 2014 - 8 апр 2014" для отображения на странице "Оплата"
    @property
    def from_to_period(self):
        return utils.formatDTWithYear(self.date_from) + u" – " + utils.formatDTWithYear(self.date_to)


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
        return [["m{0}-{1:02}".format(m.year, m.month), verboseMonth(m)] for m in months]

    # Вычисляет дату по которую у юзера оплачено.
    # На основании информации о платежах из базы.
    # Либо None если оплаты нет или оплата уже не действует.
    # Гарантируется что дата возвращаемая этим методом больше или равна сегодняшней.
    # Это используется при проверке оплачена ли сейчас работа, если этот метод вернул дату - да, если None - нет.
    def getPaidByDate(self):

        import django.conf

        # Если для текущей копии задана дата по которую оплачено (для отладки на прог-копии) - ее и возвращем.
        if django.conf.settings.INSTANCE_SPECIFIC_PAID_FOR_DATE:
            return django.conf.settings.INSTANCE_SPECIFIC_PAID_FOR_DATE

        # Для этого находим все платежи в базе этого пользователя.
        # Сортируем по дате по которую оплачено.
        # И берем макс. значение.
        # Если оно сегодняшнее или позднее - возвращаем.
        payments = Payment.objects.filter(user = self.user, date_payment__isnull = False).order_by('-date_to')
        if not payments.exists():
            return None
        maxDate = payments[0].date_to
        today = datetime.date.today()
        if maxDate < today:
            return None

        return maxDate

    # Возвращает количество дней учета для этого юзера (используется на странице "Оплата") и для отображени ее в меню.
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
        paidLessThen2HoursAgo = (pbd != None) and ((datetime.datetime.now().date() - pbd) < datetime.timedelta(hours=2))

        # Аналогично, диалог блокируется при достижении 40 дней учета, а на сервере ошибка - при 45.
        daysUchetLessThen45 = self.getUchetDaysCount() < 45

        # Итог
        return (self.getPayModeCodeAndDescr()[0] == UserProfile.PAY_MODE_TRIAL_LIMITED) and not paidLessThen2HoursAgo and not daysUchetLessThen45


    PAY_MODE_NOT_LIMITED_FOR_USER_4 = 'PAY_MODE_NOT_LIMITED_FOR_USER_4'
    PAY_MODE_NOT_LIMITED = 'PAY_MODE_NOT_LIMITED'
    PAY_MODE_PAID = 'PAY_MODE_PAID'
    PAY_MODE_TRIAL = 'PAY_MODE_TRIAL'
    PAY_MODE_TRIAL_LIMITED = 'PAY_MODE_TRIAL_LIMITED'

    # Иногда при проблемах с оплатой я включаю режим "Оплаченный" юзерам на несколько дней
    # хотя оплата не поступила. Ввключаю как раз с помощью вот этого метода.
    def getAllowedModeDate(self):

        # Если для юзера есть запись в этом списке, то вернется его дата.
        # Формат записи: id, дата с включительно, дата по включительно, почему дал коммент для себя.
        allowedDates = (
            # enogtev@ya.ru
            (379, datetime.date(2014, 5, 1), datetime.date(2014, 5, 10), u'Юзер обратился что платеж банковский не зачислен и я ему на 5 дней дал статус оплаченный пока я выяснял в Z-PAYMENT что означает "Ожидает обработки" его платеж.'),
        )

        for ad in allowedDates:
            nowd = datetime.datetime.now().date()
            if (ad[0] == self.user.id) and (nowd >= ad[1]) and (nowd <= ad[2]):
                return ad[2]
        return None

    # Возвращает пару - код и текстовое описание.
    # По коду в программе можно проверить в каком сейчас режиме работает юзер.
    # А текст используется чтобы показать текстовое описание пользователю.
    def getPayModeCodeAndDescr(self):

        # Без ограничений режим работал по 7 апреля для меня лично и по 9 апреля всем остальным
        if self.user.id == 4 and (datetime.datetime.now().date() < datetime.date(2014, 4, 7)):
            return (UserProfile.PAY_MODE_NOT_LIMITED_FOR_USER_4, u"Без ограничений по 07.04.2014")
        elif self.user.id != 4 and datetime.datetime.now().date() < datetime.date(2014, 4, 9):
            return (UserProfile.PAY_MODE_NOT_LIMITED, u"Без ограничений по 09.04.2014")

        # Иногда при проблемах с оплатой я включаю режим "Оплаченный" юзерам на несколько дней
        # хотя оплата не поступила. Ввключаю как раз с помощью вот этого метода.
        elif self.getAllowedModeDate() is not None:
            d = self.getAllowedModeDate()
            return (UserProfile.PAY_MODE_NOT_LIMITED, u"Без ограничений по " + d.strftime('%d.%m.%Y'))

        # Далее если есть действующая оплата, то режим "Оплаченный"
        elif self.getPaidByDate() is not None:

            # Дату делаем "Оплаченный по ДД.ММ.ГГГГ", т.к. "Оплаченный по ДД май ГГГГ" не подходит
            d = self.getPaidByDate()
            return (UserProfile.PAY_MODE_PAID, u"Оплаченный по " +  d.strftime('%d.%m.%Y') + u". Осталось дней: " + str((d - datetime.datetime.now().date()).days))

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
                 'так Вы перейдете на режим "Оплаченный".').format(days))


    # Возвращает текстовое описание текущего режима работы с сервисом (на странице "Оплата")
    def getPayModeDescription(self):
        return self.getPayModeCodeAndDescr()[1]

    # Возвращает True если 20 дней учета добавлено.
    # Используется чтобы показать страницу "Оплата" для таких юзеров.
    def is20DaysUser(self):
        return self.getUchetDaysCount() >= 20

    # Возвращает 0-5 если осталось 0-5 дней оплаченнго режима или меенее, и None если текущий режим не оплаченный
    # или дней осталось другое количество. Используется чтобы напомнить юзерам что скоро придет пора плаить.
    # Шоб они платили заранее. В диалоге внесения учета.
    def get5DaysPaidLeft(self):
        paidMode = self.getPayModeCodeAndDescr()[0] == UserProfile.PAY_MODE_PAID
        if not paidMode:
            return None
        daysLeft = (self.getPaidByDate() - datetime.date.today()).days
        if daysLeft > 5:
            return None
        return daysLeft


# Шаги руководства
class ManualSteps(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)

    # Если юзер отвечает "Да, хочу получить" в этот момет сюда пишется дата-время
    datetime_subscribe = models.DateTimeField(null = True)

    # Если юзер отвечает "Нет, не хочу" или отписывается позже то сюда пишется дата-время
    datetime_cancel = models.DateTimeField(null = True)


# Счет
class Account(models.Model):
    user = models.ForeignKey(django.contrib.auth.models.User)
    name = models.CharField(max_length=255, error_messages={
        'blank': u'Название счета не должно быть пустым.',
        'max_length': u'Название счета не должно быть более 255 символов длинной.'
    })
    balance_start = models.DecimalField(max_digits=11, decimal_places=2, default=0)

    # Видимость, по умолчанию (при регистрации) - счета создаются видимыми
    visible = models.BooleanField(default=True)

    # Дефолтова позиция = 1000, т.о. при добавлениии она всегда бдует в конец ставиться.
    position = models.PositiveIntegerField(default=1000)

    # Скрыть можно счет только с тек. балансом = 0
    def clean(self):
        from django.core.exceptions import ValidationError
        from django.db.models import Count, Sum, Min, Max
        if not self.visible and self.uchet_set.aggregate(sum = Sum('sum')).values()[0] != 0:
            raise ValidationError(u'MUST_BE_ZERO')

    # Уникальность имени счета только в рамках одного юзера
    class Meta:
        unique_together = ('user', 'name',)


LKCM_BUDGET_PERIOD_ALL = "LKCM_BUDGET_PERIOD_ALL"
LKCM_BUDGET_PERIOD_DAY = "LKCM_BUDGET_PERIOD_DAY"
LKCM_BUDGET_PERIOD_WEEK = "LKCM_BUDGET_PERIOD_WEEK"
LKCM_BUDGET_PERIOD_MONTH = "LKCM_BUDGET_PERIOD_MONTH"
LKCM_BUDGET_PERIOD_QUART = "LKCM_BUDGET_PERIOD_QUART"
LKCM_BUDGET_PERIOD_YEAR = "LKCM_BUDGET_PERIOD_YEAR"
LKCM_BUDGET_PERIOD_NONE = "LKCM_BUDGET_PERIOD_NONE"
LKCM_BUDGET_PERIOD_CHOICES1 = [
    (LKCM_BUDGET_PERIOD_DAY, u'День'),
    (LKCM_BUDGET_PERIOD_WEEK, u'Неделя'),
    (LKCM_BUDGET_PERIOD_MONTH, u'Месяц'),
    (LKCM_BUDGET_PERIOD_QUART, u'Квартал'),
    (LKCM_BUDGET_PERIOD_YEAR, u'Год'),
]
LKCM_BUDGET_PERIOD_CHOICES2 = [
    (LKCM_BUDGET_PERIOD_ALL, u'Все'),
] + LKCM_BUDGET_PERIOD_CHOICES1 + [
    (LKCM_BUDGET_PERIOD_NONE, u'Не задано'),
]



LKCM_DOHOD_RASHOD_TYPE_RASHOD = "LKCM_DOHOD_RASHOD_TYPE_RASHOD"
LKCM_DOHOD_RASHOD_TYPE_DOHOD = "LKCM_DOHOD_RASHOD_TYPE_DOHOD"
LKCM_DOHOD_RASHOD_TYPE_CHOICES1 = [
    (LKCM_DOHOD_RASHOD_TYPE_RASHOD, u'Расход'),
    (LKCM_DOHOD_RASHOD_TYPE_DOHOD, u'Доход'),
]


# Категория
class Category(models.Model):

    # Пользователь
    user = models.ForeignKey(django.contrib.auth.models.User)

    # Имя
    name = models.CharField(max_length=255, error_messages={
        'blank': u'Название категории не должно быть пустым.',
        'max_length': u'Название категории не должно быть более 255 символов длинной.'
    })

    # Видимость, по умолчанию (при регистрации) - категории создаются видимыми
    visible = models.BooleanField(default=True)

    # Дефолтова позиция = 1000, т.о. при добавлениии она всегда бдует в конец ставиться.
    position = models.PositiveIntegerField(default=1000)

    # Периодичность бюджета
    lkcm_budget_period = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        choices = LKCM_BUDGET_PERIOD_CHOICES1,
    )
    lkcm_budget_value = models.PositiveIntegerField(null=True, blank=True, default=None)

    lkcm_dohod_rashod_type = models.CharField(
        max_length=255,
        default=LKCM_DOHOD_RASHOD_TYPE_RASHOD,
        choices = LKCM_DOHOD_RASHOD_TYPE_CHOICES1,
    )

    # Уникальность имени счета только в рамках одного юзера
    class Meta:
        unique_together = ('user', 'name',)

# Тип записи учета - расход доход или перевод
class UType(models.Model):
    name = models.CharField(max_length=255, unique=True)

    RASHOD = 1
    DOHOD = 2
    PEREVOD = 3


class Uchet(models.Model):

    user = models.ForeignKey(django.contrib.auth.models.User)
    date = models.DateField()
    myum_time = models.TimeField(
        default="00:00",
        help_text=u'Чтобы удобнее вспоминать какая операция за что отвечает',
    )
    utype = models.ForeignKey(UType)
    sum = models.DecimalField(max_digits=11, decimal_places=2)
    account = models.ForeignKey(Account)
    category = models.ForeignKey(Category)
    comment = models.CharField(max_length=1024)

    def dateDDMMYYYY(self):
        return self.date.strftime('%d.%m.%Y')


# Журнал событий
class EventLog(models.Model):

    # Устарели не используются больше в новом коде (только старые события отображаются с их помощью)
    OLD_EVENT_ADD_SET = (9,"Добавил счет или категорию")
    OLD_EVENT_EDT_SET = (10,"Изменил счет или категорию")
    OLD_EVENT_DEL_SET = (11,"Удалил счет или категорию")
    OLD_EVENT_VISIT_SET = (3,"Заход на страницу настроек")

    # Новые события
    EVENT_VISIT_UCH = (1,"Заход на страницу учета")
    EVENT_VISIT_ANA = (2,"Заход на страницу анализа")
    EVENT_VISIT_IMP = (4,"Заход на страницу импорта")
    EVENT_ADD_UCH = (5,"Добавил запись учета")
    EVENT_EDT_UCH = (6,"Изменил запись учета")
    EVENT_DEL_UCH = (7,"Удалил запись учета")
    EVENT_IMP = (8,"Прислал данные для импорта")
    EVENT_UNSUBSCR = (12,"Отписался от рассылки")
    EVENT_SUBSCR = (13,"Подписался на рассылку")

    EVENT_VISIT_PAY =               (14, "Заход на страницу оплаты")
    EVENT_DO_ORDER =                (15, 'Нажал кнопку "Оплатить"')
    EVENT_ROBOKASSA_PAY_NOTIFY =    (16, "Пришла оплата от ROBOKASSA")
    EVENT_ZPAYMENT_PAY_NOTIFY =     (21, "Пришла оплата от Z-PAYMENT")

    EVENT_VISIT_EXP =       (17, "Заход на страницу экспорта")
    EVENT_VISIT_BEGIN =     (18, "Заход на страницу начало")
    EVENT_LOGIN =           (19, "Авторизовался")

    EVENT_EXP =             (20, "Просмотрел данные для экспорта")

    EVENT_PAYMENT_NEED_DIALOG = (22, 'Отослана страница с диалогом "Нужна оплата"')
    EVENT_VISIT_FEEDBACK_REQUEST = (23, 'Заход на страницу "Почему не стал использовать"')
    EVENT_SEND_FEEDBACK_REQUEST = (24, 'Отправил "Почему не стал использовать"')
    EVENT_REGISTERED = (25, 'Зарегистрировался')
    EVENT_LOGOUT = (26, 'Выход')

    EVENT_ADD_ACC = (27,"Добавил счет")
    EVENT_EDT_ACC = (28,"Изменил счет")
    EVENT_DEL_ACC = (29,"Удалил счет")

    EVENT_ADD_CAT = (30,"Добавил категорию")
    EVENT_EDT_CAT = (31,"Изменил категорию")
    EVENT_DEL_CAT = (32,"Удалил категорию")
    EVENT_VISIT_ACCOUNTS = (33,"Заход на страницу счетов")
    EVENT_VISIT_CATEGORIES = (34, "Заход на страницу категорий")
    EVENT_REORDER_ACCOUNTS = (35, "Изменен порядок счетов")
    EVENT_REORDER_CATEGORIES = (36, "Изменен порядок категорий")
    EVENT_5DAYS_PAID_LEFT_MESSAGE = (37, 'Отослана страница с сообщением "5 и менее дней оплаты осталось"')
    EVENT_SAVE_MANUAL_ANSWER = (38, 'Сохранен ответ по руководству')

    user = models.ForeignKey(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)
    event2 = models.IntegerField()

    @property
    def event_name(self):
        for a in dir(EventLog):
            if a.startswith('EVENT_') or a.startswith('OLD_EVENT_') :
                if getattr(self, a)[0] == self.event2:
                    return getattr(self, a)[1]
        raise RuntimeError('Ошибка получения описания события. В базе соранен код события #{0}, но константа EVENT (или OLD_EVENT) в классе EventLog с таким значением кода не найдена.'.format(self.event2))


# Заполняется если юзер отписался
class Unsubscribe(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)


# Заполняется в момент когда юзеру направлено первое письмо-запрос на обратную связь (больше высылать не надо).
class FeedbackRequested(models.Model):
    user = models.OneToOneField(django.contrib.auth.models.User)
    datetime = models.DateTimeField(auto_now_add=True)


class UchetAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'date',
        'myum_time',
        'category',
        'account',
        'sum',
    )

    raw_id_fields = (
        'user',
        'account',
        'category',
    )

    list_per_page = 50


# Данная функция создана для того чтобы исключить ошибки что забыли указать требование авторизации админа
# для доступа в админку. С помощью этой функции надо всегда явно указать роль
# при регистрации интерфейса админки.
def registerModelAndAdmin(model_class, admin_class):

    # Только с заданной ролью можно входить на эту страницу
    admin_class.get_urls = plogic.getDjangoAdminUrlsWithAdminCheck()
    admin.site.register(model_class, admin_class)


registerModelAndAdmin(Uchet, UchetAdmin)