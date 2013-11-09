# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template import RequestContext
from django.http.response import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.db.models import Count, Sum, Min, Max
from django.core.serializers.json import DjangoJSONEncoder
import django.core.exceptions
import django.db.utils
from django.conf import settings
from django import forms


import json
import datetime

import my_uu.models
import my_uu.utils

def _main_imp(request, templateName):

    # Если юзер уже прошел аутентификацию посылаем его в ЛК
    if request.user.id is not None:
        return HttpResponseRedirect(reverse('my_uu.views.lk_uch'))

    # Эта страница используется вместо главной пока
    return render(request, templateName)


# Главная страница.
def main(request):
    return _main_imp(request, 'lpgen_main.html')

# Главная страница 2.
def main_v(request):
    return _main_imp(request, 'lpgen_main_v.html')


class MyUUAuthForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()


# Класс инкапсулирует в себе знание о том какой
# формат взаимодействия между сервером и клиентом (JS).
# А именно пока он такой:
# ответ содержит 2 поля - status_ok (булевый, True если операция выполнена и False если что-то случилось)
# и response который содержит доп. данные в обоих случаях или может быть пустой.
class JsonResponseBuilder():

    def __init__(self):
        self._responseObject = {
            'status_ok': True
        }

    def setError(self, errorResponseObject):
        self._responseObject['status_ok'] = False
        self._responseObject['response'] = errorResponseObject

    def setSuccess(self, successResponseObject):
        self._responseObject['status_ok'] = True
        self._responseObject['response'] = successResponseObject

    def buildHttpJsonResponse(self):
        return HttpResponse(json.dumps(self._responseObject), content_type="application/json")


# Регистрация юзера по переданным email и паролю.
# Вернет body содержащий:
#     ok - зареген успешно
#     exists - уже существует
def register_user_ajax(request):
    resp = JsonResponseBuilder()
    data = json.loads(request.body)
    frm = MyUUAuthForm(data)
    if not frm.is_valid():
        # Тут такой финт с проверкой текста чтобы избежать случая когда
        # оба поля не заполнены и юзеру покажется 2 раа текст "Обязательное поле".
        txt = u''
        req = u''
        for i in frm.errors.items():
            for s in i[1]:
                if s == u"Обязательное поле.":
                    req = u"Оба поля обязательны для заполнения. "
                else:
                    txt += s + u" "
        resp.setError(req + txt)
        return resp.buildHttpJsonResponse()

    # Создаем юзера. Если эксепшен так как уже существует, то возвращаем код.
    try:
        u = User.objects.create_user(data['email'], data['email'], data['password'])
        u.save()
    except django.db.utils.IntegrityError as e:
        if u'Duplicate entry' in unicode(e):
            resp.setError(u'Пользователь с таким адресом эл. почты уже зарегистрирован в сервисе. ')
            return resp.buildHttpJsonResponse()

    # Для нового юзера надо создать счет и категорию
    my_uu.models.Category.objects.create(name = u'Не указана категория', user = u).save()
    my_uu.models.Category.objects.create(name = u'Жилье', user = u).save()
    my_uu.models.Category.objects.create(name = u'Питание', user = u).save()
    my_uu.models.Account.objects.create(name = u'Кошелек', user = u).save()
    my_uu.models.Account.objects.create(name = u'Карта', user = u).save()

    # Регистрация прошла успешно - высылаем email
    my_uu.utils.sendEmailRegistrationPerformed(data['email'], data['password'])

    # И теперь тут же логиним
    user = _authenticateByEmailAndPassword(**data)
    login(request, user)

    return resp.buildHttpJsonResponse()


# Отличие от стандартной django authenticate в том что принимает пароль и емейл (а в джанге - username и пароль).
def _authenticateByEmailAndPassword(**kwargs):
    kwargs['username'] = kwargs['email']
    return authenticate(**kwargs)


# Вызывается чтобы залогинить юзера
# Вернет body содержащий:
#     ok - залогинен успешно
#     auth_email_password_incorrect - email и пароль не определены
def login_user_ajax(request):
    data = json.loads(request.body)
    resp = JsonResponseBuilder()

    frm = MyUUAuthForm(data)
    if frm.is_valid():

        # На разработческой машине можно войти под любым юзером без пароля
        # if settings.IS_DEVELOPER_COMP:
        #    user = django.contrib.auth.models.User.objects.get(email = data['email'])

            # Если не выставить бекэнд то потом ошибка при получении юзера.
        #   user.backend = "django.contrib.auth.backends.ModelBackend"
        # else:
        user = _authenticateByEmailAndPassword(**data)

        if user is not None:
            login(request, user)
            resp.setSuccess(None)
        else:
            resp.setError(u'Пользователь с таким паролем и адресом эл. почты не найден.')
    else:
        # Тут такой финт с проверкой текста чтобы избежать случая когда
        # оба поля не заполнены и юзеру покажется 2 раа текст "Обязательное поле".
        txt = u''
        req = u''
        for i in frm.errors.items():
            for s in i[1]:
                if s == u"Обязательное поле.":
                    req = u"Оба поля обязательны для заполнения. "
                else:
                    txt += s + u" "
        resp.setError(req + txt)

    return resp.buildHttpJsonResponse()
    
# ВЫход
def logout_user(request):
    import django.contrib.auth.views
    return django.contrib.auth.views.logout(request, next_page = reverse('my_uu.views.main'))


# Страница регистрации или входа
def begin(request):

    # Если юзер уже прошел аутентификацию посылаем его в ЛК
    if request.user.id is not None:
        return HttpResponseRedirect(reverse('my_uu.views.lk_uch'))

    return render(request, 'begin.html')


def uu_login_required(f):
    from django.contrib.auth.decorators import login_required
    return login_required(f, login_url='/begin/')

# Требует администраторского логина. Иначе - выкидывает на 404 ошибку.
def uuAdmLoginRequired(f):
    def uuAdmLoginRequiredWrapper(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.email == 'pvoytko@gmail.com':
            return f(request, *args, **kwargs)
        else:
            raise Http404()
    return uuAdmLoginRequiredWrapper

# Декоратор до вызова view сохраняет в журнал событие
def uuTrackEventDecor(eventConstant):
    def uuTrackEventDecorImpl(f):
        def uuTrackEventWrapper(request, *args, **kwargs):
            # Отслеживаем (сохраняем в журнал) это действие юзера
            request.user.eventlog_set.create(event = my_uu.models.Event.objects.get(id = eventConstant))
            return f(request, *args, **kwargs)
        return uuTrackEventWrapper
    return uuTrackEventDecorImpl

# Сохраняет запись о событии
def uuTrackEventDynamic(user, eventConstant):
    user.eventlog_set.create(event = my_uu.models.Event.objects.get(id = eventConstant))


def _getAccountBalanceList(request):
    accountBalanceList = my_uu.models.Account.objects.filter(user=request.user)
    accountBalanceList = accountBalanceList.annotate(balance = Sum('uchet__sum'))
    accountBalanceList = accountBalanceList.order_by('id')
    if len(accountBalanceList) > 14:
        assert False, 'Слишком большое количество счетов, интерфейс пока не рассчитан на такое количество.'
    return list(accountBalanceList.values('id', 'name', 'balance'))


def _getCategoryList(request):
    categoryList = my_uu.models.Category.objects.filter(user=request.user)
    categoryList = categoryList.order_by('id')
    return list(categoryList.values('id', 'name'))


# Главная страница личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.VISIT_UCH)
def lk_uch(request):

    return render(request, 'lk_uch.html', {
        'request': request,
        'uchetRecords': my_uu.models.Uchet.objects.filter(user=request.user).order_by('date', '-utype', 'id'),
        'uTypeList': my_uu.models.UType.objects.all().order_by('id'),
        'accountList': my_uu.models.Account.objects.filter(user=request.user).order_by('id'),
        'categoryList': my_uu.models.Category.objects.filter(user=request.user).order_by('id'),
        'accountBalanceListJson': json.dumps(_getAccountBalanceList(request), cls=DjangoJSONEncoder),
        'categoryListJson': json.dumps(_getCategoryList(request), cls=DjangoJSONEncoder),
    })


# Страница Настройки личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.VISIT_SET)
def lk_set(request):
    import json

    # Получаем счета и категории с указанием количества записей
    rowsA = my_uu.models.Account.objects.annotate(count = Count('uchet'))
    rowsA = rowsA.filter(user=request.user).values('id', 'name', 'count')
    rowsC = my_uu.models.Category.objects.annotate(count = Count('uchet'))
    rowsC = rowsC.filter(user=request.user).values('id', 'name', 'count')

    # Отдаем на выход
    accountListJsonString = json.dumps(list(rowsA))
    categoryListJsonString = json.dumps(list(rowsC))

    return render(request, 'lk_set.html', {
        'request': request,
        'accountListJsonString': accountListJsonString,
        'categoryListJsonString': categoryListJsonString
    } )


# Итератор от самой ранней недели до самой поздней.
# Для построения отчета анализа.
# Получает на вход мин. дату и макс. дату записей учета.
# Итерирует по всем неделям в рамках этих дат (берутся лишь последние 5).
# Возвращает имя недели для даты (чтобы просуммировать суммы для всех дат по неделям).
# Заменяя недельный итератор месячным, квартальным и пр., можно построить любой
# отчет по одному алгоритму.
class AnaWeekIterator(object):

    def __init__(self, minDate, maxDate):
        # Ограничиваем 2013 годом на случай если записи будут за большой диапазон.
        self.maxWeek = min(maxDate, datetime.date(2013, 12, 31)).isocalendar()[1]
        self.minWeek = max(max(minDate, maxDate - datetime.timedelta(days=7*4)), datetime.date(2013, 1, 1)).isocalendar()[1]
        self.curWeek = self.minWeek

    def __iter__(self):
        return self

    def getRangeNameForDate(self, date):
        w = date.isocalendar()[1]
        if w in xrange(self.minWeek, self.maxWeek+1):
            return str(w)
        else:
            return None

    def next(self):
        if self.curWeek > self.maxWeek:
            raise StopIteration()
        else:
            self.curWeek += 1
            return str(self.curWeek - 1)


class AnaChndkIterator(object):

    def __init__(self, minDate, maxDate):
        # Ограничиваем 2013 годом на случай если записи будут за большой диапазон.
        self.maxChndk = (min(maxDate, datetime.date(2013, 12, 31)).isocalendar()[1] - 1) / 4 + 1
        self.minChndk = (max(max(minDate, maxDate - datetime.timedelta(days=7*4*4)), datetime.date(2013, 1, 1)).isocalendar()[1] - 1) / 4 + 1
        self.curChndk = self.minChndk

    def __iter__(self):
        return self

    def getRangeNameForDate(self, date):
        w = date.isocalendar()[1] / 4 + 1
        if w in xrange(self.minChndk, self.maxChndk+1):
            return str(w)
        else:
            return None

    def next(self):
        if self.curChndk > self.maxChndk:
            raise StopIteration()
        else:
            self.curChndk += 1
            return str(self.curChndk - 1)


# Страница Анализ личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.VISIT_ANA)
def lk_ana(request):

    # Уникальный список категорий
    categoryList = request.user.category_set.all().distinct()

    # Максимальные и минимальные номера недель которые есть в учете для этого юзера
    minMaxDate = request.user.uchet_set.aggregate(min_date = Min('date'), max_date = Max('date'))

    # Результат
    l = []

    # Если есть хотя бы одна запись учета, то формируем содержание списка на выдачу
    if minMaxDate['min_date'] != None:
        assert minMaxDate['max_date'] != None, u'Если минимальня дата не None, то и максимальная должна быть не None.'

        # Для каждой категории
        for (i, item) in enumerate(categoryList):

            # Получаем суммы по дням (только для расходов)
            sumForDays = request.user.uchet_set.filter(category = item, utype = my_uu.models.UType.RASHOD)
            sumForDays = sumForDays.values('date').distinct()
            sumForDays = sumForDays.annotate(sum = Sum('sum'))

            # Если ни одной суммы для этой категории, то такую категорию пропускаем
            if sumForDays.count() > 0:

                # Номера недель (или ЧНДК)
                rangeIter = AnaWeekIterator(minMaxDate['min_date'], minMaxDate['max_date'])
                if 'chndk' in request.GET:
                    rangeIter = AnaChndkIterator(minMaxDate['min_date'], minMaxDate['max_date'])

                # Формируем словарь с суммами по неделям для категорий (сначала заполняем его нулями)
                # Чтобы для каждой недели стояло значение (этого ждет клиентский код).
                d = dict()
                d['category'] = item.name
                for w in rangeIter:
                    d[w] = 0

                # Сейчас проходим по всем дням и суммам и плюсуем эти суммы к неделям
                skipCategory = True
                for sumForDay in sumForDays:
                    rangeName = rangeIter.getRangeNameForDate(sumForDay['date'])
                    if rangeName is not None:
                        d[rangeName] += sumForDay['sum']
                        skipCategory = False

                # Сохраняем результат
                if not skipCategory:
                    l.append(d)

    return render(request, 'lk_ana.html', {
        'request': request,
        'anaDataJson': json.dumps(l, cls=DjangoJSONEncoder)
    } )


# Страница импорта
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.VISIT_IMP)
def lk_imp(request):
    return render(request, 'lk_imp.html', { 'request': request })


# Импорт данных через аякс
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.IMP)
def lk_imp_ajax(request):
    importedData = json.loads(request.body)

    def getOrCreateAccount(accName):
        return request.user.account_set.get_or_create(name = accName)[0]

    def getOrCreateCategory(catName):
        return request.user.category_set.get_or_create(name = catName)[0]

    for uchet in importedData:
        request.user.uchet_set.create(
            date = datetime.datetime.strptime(uchet[0], '%d.%m.%Y'),
            utype = my_uu.models.UType.objects.get(name__iexact = uchet[1]),
            sum = uchet[2],
            account = getOrCreateAccount(uchet[3]),
            category = getOrCreateCategory(uchet[4]),
            comment = uchet[5],
        )
    return JsonResponseWithStatusOk(importedCount = len(importedData))


class JsonResponseWithStatusError(HttpResponse):
    def __init__(self, exception):
        super(JsonResponseWithStatusError, self).__init__(
            json.dumps({
                'status': 'error',
                'text': unicode(exception)
            }, cls=DjangoJSONEncoder)
        )


class JsonResponseWithStatusOk(HttpResponse):
    def __init__(self, **kwargs):
        d = kwargs
        d['status'] = 'ok'
        super(JsonResponseWithStatusOk, self).__init__(
            json.dumps(d, cls=DjangoJSONEncoder)
        )


# Сохранить данные учета (через Аякс вызывается)
@uu_login_required
def lk_save_uchet_ajax(request):
    rowsForUpdateAndInsert = json.loads(request.POST['rows_json'])

    # Перебираем все полученные строки
    # Если в ней есть serverRecordId, значит эта строка есть уже в БД, ее надо update.
    # Если в полученных данны нет serverRecordId, значит эту строку надо insert
    for r in rowsForUpdateAndInsert:

        # На основе пришедших данных делаем стркоу для вставки в БД
        import copy
        rowDbData = copy.copy(r)

        # Шаг №1 - заменить названия счетов и категорий на их id в БД
        rowDbData['account'] = my_uu.models.Account.objects.get(name=r['account'], user=request.user)
        rowDbData['category'] = my_uu.models.Category.objects.get(name=r['category'], user=request.user)
        rowDbData['utype'] = my_uu.models.UType.objects.get(name=r['utype'])
        rowDbData['date'] = datetime.datetime.strptime(r['date'], '%d.%m.%Y')
        rowDbData['user'] = request.user

        # С клиента приходят в формате с ",", меняем на "."
        rowDbData['sum'] = r['sum'].replace(',', '.')

        # Если коммент очистить через del в jqxGrid, то на сервер приходят null. Преобразуем в пустые строки.
        # Иначе в БД эксепшен получим. Если зарегиться и добавить строку от нового юзера то коммент вообще
        # такое поле отсутствует в прищедших данных.
        rowDbData['comment'] = u'' if (('comment' not in r) or (r['comment'] is None)) else r['comment']

        # Получаем id строки на сервере если есть и удаляем лишние поля (чтоб не вылазило ошибки при update)
        serverRowId = None
        if 'serverRowId' in r:
            uuTrackEventDynamic(request.user, my_uu.models.Event.EDT_UCH)
            serverRowId = rowDbData['serverRowId']
            del rowDbData['serverRowId']
        else:
            uuTrackEventDynamic(request.user, my_uu.models.Event.ADD_UCH)

        del rowDbData['uid']

        # Обновление, если есть serverRowId
        if serverRowId is not None:
            my_uu.models.Uchet.objects.filter(id=serverRowId).update(**rowDbData)

        # Добавление
        # Полученный serverRecordId устанавливаем для этой строки.
        else:
            u = my_uu.models.Uchet.objects.create(**rowDbData)
            u.save()
            r['serverRowId'] = u.id

    # Возвращаем то же самое (только серверные id поставили)
    return JsonResponseWithStatusOk(
        rows_json = rowsForUpdateAndInsert,
        accountBalanceList = _getAccountBalanceList(request)
    )


# Удалить строку учета (через Аякс вызывается)
@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.DEL_UCH)
def lk_delete_uchet_ajax(request):
    rowForDelete = json.loads(request.POST['rowForDelete'])
    rowId = rowForDelete['serverRowId']
    my_uu.models.Uchet.objects.get(id= rowId).delete()
    return JsonResponseWithStatusOk(accountBalanceList = _getAccountBalanceList(request))


class MyUUUIException(BaseException):
    pass


class AccountNameValidationError(MyUUUIException):
    def __init__(self, errText):
        super(AccountNameValidationError, self).__init__(
            u"Не удалось сохранить изменения. " + errText
        )


class DeleteAccountWithUchetRecordsException(MyUUUIException):
    def __init__(self):
        super(DeleteAccountWithUchetRecordsException, self).__init__(
            u"Есть связанные записи учета. Удаление невозможно."
        )


class DeleteLastAccountException(MyUUUIException):
    def __init__(self, isAccount):
        texts = {
            True: u"Нельзя удалить последний счет. Должен оставаться хотя бы один счет.",
            False: u"Нельзя удалить последнюю категорию. Должна оставаться хотя бы одна категория.",
        }

        super(DeleteLastAccountException, self).__init__( texts[isAccount] )


def _lk_save_settings_ajax(request, userPropName, modelClass):

    newAccountData = json.loads(request.body)

    # Создаем новый или изменяем существующий счет
    if 'id' in newAccountData:
        uuTrackEventDynamic(request.user, my_uu.models.Event.EDT_SET)
        a = getattr(request.user, userPropName).get(id = newAccountData['id'])
    else:
        uuTrackEventDynamic(request.user, my_uu.models.Event.ADD_SET)
        a = modelClass()
        a.user = request.user

    a.name = newAccountData['name']


    try:
        try:
            a.full_clean()
            a.save()

        # Если исключение в поле name, то такой вид исключений обрабатываем переделываем в наш вид
        # который мы умеем обрабатывать.
        except django.core.exceptions.ValidationError, e:
            if 'name' in e.message_dict:
                raise AccountNameValidationError(u" ".join(e.message_dict['name']))

    # Если исключение при проверке поля Account.name, то показываем текст этой ошибки юзеру.
    except MyUUUIException, e:
        return JsonResponseWithStatusError(e)

    # Ошибок не возникло, все ОК.
    return JsonResponseWithStatusOk(id = a.id)


@uu_login_required
@uuTrackEventDecor(my_uu.models.Event.DEL_SET)
def _lk_delete_settings_ajax(request, userPropName):
    try:

        accountData = json.loads(request.body)
        a = getattr(request.user, userPropName).get(id = accountData['id'])

        # Нельзя удалять если есть связанные записи учета
        if a.uchet_set.count() != 0:
            raise DeleteAccountWithUchetRecordsException()

        # Нельзя удалять если это последний счет (категория).
        # Так как в этом случае заглючит таблица учета в которой ни одного счета ни одной категории.
        if getattr(request.user, userPropName).count() == 1:
            assert userPropName == 'account_set' or userPropName == 'category_set', u'Должно быть либо то либо другое.'
            isAccount = userPropName == 'account_set'
            raise DeleteLastAccountException(isAccount)

        a.delete()

    except MyUUUIException, e:
        return JsonResponseWithStatusError(e)

    # Ошибок не возникло, все ОК.
    return JsonResponseWithStatusOk()


@uu_login_required
def lk_save_account_ajax(request):
    return _lk_save_settings_ajax(request, 'account_set', my_uu.models.Account)

@uu_login_required
def lk_delete_account_ajax(request):
    return _lk_delete_settings_ajax(request, 'account_set')

@uu_login_required
def lk_save_category_ajax(request):
    return _lk_save_settings_ajax(request, 'category_set', my_uu.models.Category)

@uu_login_required
def lk_delete_category_ajax(request):
    return _lk_delete_settings_ajax(request, 'category_set')


@uu_login_required
def lk_improove_ajax(request):
    my_uu.utils.sendImprooveEmail(request.user.id, request.user.email, json.loads(request.body)['improoveText'])
    return JsonResponseWithStatusOk()


# http://djangosnippets.org/snippets/1022/
def uuRenderWith(template):
    def render_with_decorator(view_func):
        def wrapper(*args, **kwargs):
            request = args[0]
            context = view_func(*args, **kwargs)
            return render_to_response(
                template,
                context,
                context_instance=RequestContext(request),
            )
        return wrapper
    return render_with_decorator


# Страница Анализ личного кабиета
@uuAdmLoginRequired
@uuRenderWith('adm_act.html')
def adm_act(request):

    date10DaysAgo = datetime.datetime.now() - datetime.timedelta(10)
    eventLogObjects = my_uu.models.EventLog.objects.filter(datetime__gt = date10DaysAgo)
    eventLogObjects = eventLogObjects.order_by('datetime')

    return locals()


# Страница Анализ личного кабиета
@uuAdmLoginRequired
@uuRenderWith('adm_exp.html')
def adm_exp(request):

    # Подсчитываем мин макс дату учета и число дней с журналами операций
    userStat = User.objects.all().annotate(min_dt = Min("eventlog__datetime"), max_dt = Max("eventlog__datetime"))
    userStat = userStat.order_by('id').values()
    for u in userStat:
        u['min_dt'] = u['min_dt'].date() if u['min_dt'] else None
        u['max_dt'] = u['max_dt'].date() if u['max_dt'] else None

        eventLogObjects = my_uu.models.EventLog.objects.filter(user = u['id']).extra(select = {'date': 'DATE(datetime)'})
        u['count_dt'] = len(eventLogObjects.values_list('date', flat=True).distinct())

        uchetRecords = my_uu.models.Uchet.objects.filter(user = u['id'])
        u['count_dt_op'] = uchetRecords.values_list('date', flat=True).distinct().count()
        u['count_op'] = uchetRecords.count()

    return locals()



# Отписка юзера - показывает состояние
# Важно - доступ без авторизации на эту страницу.
@uuRenderWith('unsubscr.html')
def unsubscr_view(request, obfuscatedUserId):
    user = User.objects.get(id = my_uu.utils.restoreId(int(obfuscatedUserId)))
    isUnsubscribed = my_uu.models.Unsubscribe.objects.filter(user=user).count() == 1
    return locals()


# Выполняет либо отписку либо подписку ничего не пказывает редиректит обратно.
def unsubscr_do(request, obfuscatedUserId):

    # Юзера важно брать не из request, а из ID из УРЛа.
    # Так как вход на эту страницу должен быть без авторизации (чтоб из емейла работали ссылки).
    user = User.objects.get(id = my_uu.utils.restoreId(int(obfuscatedUserId)))

    # Отписка
    if 'uns' in request.POST:
        my_uu.models.Unsubscribe.objects.get_or_create(user=user)
        uuTrackEventDynamic(user, my_uu.models.Event.UNSUBSCR)

    # Подписка
    if 'sub' in request.POST:
        my_uu.models.Unsubscribe.objects.get(user=user).delete()
        uuTrackEventDynamic(user, my_uu.models.Event.SUBSCR)

    return HttpResponseRedirect(reverse(unsubscr_view, kwargs={'obfuscatedUserId': obfuscatedUserId}))