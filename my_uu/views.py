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


# Главная страница 2.
def main(request):
    return _main_imp(request, 'lpgen_main.html')


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

    # Для всех юзеров обязательно создаем профиль (доп. набор полей к джанговской модели юзера)
    profile = my_uu.models.UserProfile.objects.get_or_create(user=u)

    # Устанавливаем HTTP Referer для юзера
    import urllib
    if 'uu_ref' in request.COOKIES:

        # Эта сервия преобразований приводит к юникодной строке в которой русские буквы
        inpHttpRef = urllib.unquote(request.COOKIES['uu_ref']).decode('utf8')
        u.get_profile().http_referer = urllib.unquote(str(inpHttpRef)).decode('utf-8')
        u.get_profile().save()

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
        if settings.IS_DEVELOPER_COMP:
            user = django.contrib.auth.models.User.objects.get(email = data['email'])

            # Если не выставить бекэнд то потом ошибка при получении юзера.
            user.backend = "django.contrib.auth.backends.ModelBackend"
        else:
            user = _authenticateByEmailAndPassword(**data)

        if user is not None:
            login(request, user)
            resp.setSuccess(None)

            uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_LOGIN)

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
    return login_required(f, login_url='/')

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
            request.user.eventlog_set.create(event2 = eventConstant[0])
            return f(request, *args, **kwargs)
        return uuTrackEventWrapper
    return uuTrackEventDecorImpl

# Сохраняет запись о событии
def uuTrackEventDynamic(user, eventConstant):
    user.eventlog_set.create(event2 = eventConstant[0])


# Начало
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_BEGIN)
def lk_beg(request):
    return render(request, 'lk_beg.html')


# Преобразует Django-model в список словарьей чтобы можно было JSON выполнить.
def _getUchetRecordsList(uchetRecords):
    return list(uchetRecords.values('id', 'date', 'utype__name', 'sum', 'account__name', 'category__name', 'comment'))


def _getAccountBalanceList(request):
    accountBalanceList = my_uu.models.Account.objects.filter(user=request.user)
    accountBalanceList = accountBalanceList.annotate(balance = Sum('uchet__sum'))
    accountBalanceList = accountBalanceList.order_by('id')
    if len(accountBalanceList) > 28:
        raise RuntimeError('Слишком большое количество счетов, интерфейс пока не рассчитан на такое количество.')
    return list(accountBalanceList.values('id', 'name', 'balance'))


def _getCategoryList(request):
    categoryList = my_uu.models.Category.objects.filter(user=request.user)
    categoryList = categoryList.order_by('id')
    return list(categoryList.values('id', 'name'))


# Главная страница личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_UCH)
def lk_uch(request):

    return render(request, 'lk_uch.html', {
        'request': request,
        'uchetRecordsJson': json.dumps(_getUchetRecordsList(request.user.get_profile().getUchetRecordsInViewPeriod()), cls=DjangoJSONEncoder),
        'uTypeList': my_uu.models.UType.objects.all().order_by('id'),
        'accountList': my_uu.models.Account.objects.filter(user=request.user).order_by('id'),
        'categoryList': my_uu.models.Category.objects.filter(user=request.user).order_by('id'),
        'accountBalanceListJson': json.dumps(_getAccountBalanceList(request), cls=DjangoJSONEncoder),
        'categoryListJson': json.dumps(_getCategoryList(request), cls=DjangoJSONEncoder),
        'viewPeriodSetJson': json.dumps(my_uu.models.UserProfile.VIEW_PERIOD_CODE_CHOICES, cls=DjangoJSONEncoder),
        'viewPeriodMonthSetJson': json.dumps((request.user.get_profile().getUchetMonthSet()), cls=DjangoJSONEncoder),
        'viewPeriodCodeJson': json.dumps(request.user.get_profile().view_period_code),
        'showAddUchetDialog': 1 if request.user.get_profile().showAddUchetDialog() else 0 # 1 или 0 - т.к. JS не понимает True / False
    })


# Страница Настройки личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_SET)
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

    # Итератору передается минимальная и макимальная дата.
    # А он делает итерацию от минимального номера недели к максимальному.
    def __init__(self, maxDate):

        # Макс номер недели - берем от макс. даты учета.
        # Мин номер недели - берем эту и 4 предыдущих недель (если есть).
        # На их основе формируем список недель для итерации.
        curDate = maxDate - datetime.timedelta(days=7*5)
        self.weekList = [self._getWeekNum(curDate)]
        while True:
            curDate += datetime.timedelta(days=7)
            if curDate > maxDate:
                break
            self.weekList.append(self._getWeekNum(curDate))


    def __iter__(self):
        return self.weekList.__iter__()

    @staticmethod
    def _getWeekNum(date):
        return date.isocalendar()[1]


    def getWeekIndexForDate(self, date):
        w = self._getWeekNum(date)
        if w in self.weekList:
            return self.weekList.index(w)
        else:
            return None


# Страница Анализ личного кабиета
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_ANA)
def lk_ana(request):

    # Уникальный список категорий
    categoryList = request.user.category_set.all().distinct()

    # Форматирует как деньги переданный список чисел
    def formatMoneyRow(moneyRow):
        return [my_uu.utils.formatMoneyValue(v) for v in moneyRow]

    # Возвращает номера недель от текущей даты 6 назад по типу
    # date текущей недели, date текущей недели - 1, date тн - 2, date тн - 3, date тн - 4, date тн - 5
    def getWeekPeriodsList(fromDate):
        periodCounter = 0
        periodsList = []
        while periodCounter < 6:
            periodsList.insert(0, fromDate)
            fromDate -= datetime.timedelta(days=7)
            periodCounter += 1
        return periodsList

    # Возврщает строку дат для недели года
    # Пример: 14-20 янв
    def getDatesForWeek(dateOfWeek):

        # Дату начала и конца
        startDate = dateOfWeek - datetime.timedelta(days=(dateOfWeek.isocalendar()[2]-1))
        endDate = dateOfWeek + datetime.timedelta(days=(7-dateOfWeek.isocalendar()[2]))

        def monthStr(date):
            monthL = [u'янв', u'фев', u'мар', u'апр', u'май', u'июн', u'июл', u'авг', u'сен', u'окт', u'ноя', u'дек']
            return monthL[date.month-1]

        # Печатаем число
        startDateStr = unicode(startDate.day)
        if startDate.month != endDate.month:
            startDateStr += u" " + monthStr(startDate)
        endDateStr = unicode(endDate.day) + u" " + monthStr(endDate);
        return startDateStr + u"–" + endDateStr;


    def addWeekAnaDataToPageData(pageData):

        # Максимальные и минимальные даты которые есть в учете для этого юзера
        minMaxDate = request.user.uchet_set.aggregate(min_date = Min('date'), max_date = Max('date'))

        # Список периодов, заголовки столбцов
        periodsList = getWeekPeriodsList(datetime.datetime.now())
        periodsHeaders = [dict( first = u'Неделя ' + str(d.isocalendar()[1]), second = getDatesForWeek(d) ) for d in periodsList]

        # Тут мы получаем таблицу данных для расходов и доходов и суммирующую строку
        l2 = {}
        totalRow = {}
        for type in (my_uu.models.UType.RASHOD, my_uu.models.UType.DOHOD):

            # Результат
            l = []

            # Если есть хотя бы одна запись учета, то формируем содержание списка на выдачу
            if minMaxDate['min_date'] != None:

                assert minMaxDate['max_date'] != None, u'Если минимальня дата не None, то и максимальная должна быть не None.'

                # Для каждой категории
                for (i, item) in enumerate(categoryList):

                    # Получаем суммы по дням (только для расходов)
                    sumForDays = request.user.uchet_set.filter(category = item, utype = type)
                    sumForDays = sumForDays.values('date').distinct()
                    sumForDays = sumForDays.annotate(sum = Sum('sum'))

                    # Если ни одной суммы для этой категории, то такую категорию пропускаем
                    if sumForDays.count() > 0:

                        # Номера недель (или ЧНДК)
                        rangeIter = AnaWeekIterator(datetime.datetime.now())

                        # Формируем список со значениями. Число элементов в списке = число заголовков.
                        from collections import OrderedDict
                        d = OrderedDict()
                        d['category'] = item.name
                        for c, w in enumerate(rangeIter):
                            d[c] = 0

                        # Сейчас проходим по всем дням и суммам и плюсуем эти суммы к неделям
                        skipCategory = True
                        for sumForDay in sumForDays:
                            weekIndex = rangeIter.getWeekIndexForDate(sumForDay['date'])
                            if weekIndex is not None:
                                d[weekIndex] += sumForDay['sum']
                                skipCategory = False

                        # Сохраняем результат
                        if not skipCategory:
                            l.append(d)

            l2[type] = []
            totalRow[type] = [0] * len(periodsList)
            for li in l:
                l2row = {}
                l2row['category'] = li['category']
                l2row['data'] = []
                dataCellIndex = -1
                for k in sorted(li.keys()):
                    if k != 'category':
                        dataCellIndex += 1
                        l2row['data'].append(float(li[k]))

                        # Подсчитываем суммирующую строку
                        totalRow[type][dataCellIndex] += float(li[k])

                l2row['data'] = formatMoneyRow(l2row['data'])

                l2[type].append(l2row)

            totalRow[type] = formatMoneyRow(totalRow[type])

        # Итог работы функции
        pageData['periods']['rashod-week'] = periodsHeaders
        pageData['periods']['dohod-week'] = periodsHeaders
        pageData['dataRows']['rashod-week'] = l2[my_uu.models.UType.RASHOD]
        pageData['dataRows']['dohod-week'] = l2[my_uu.models.UType.DOHOD]
        pageData['totalRow']['rashod-week'] = totalRow[my_uu.models.UType.RASHOD]
        pageData['totalRow']['dohod-week'] = totalRow[my_uu.models.UType.DOHOD]

    def addMonthAnaDataToPageData(pageData):

        # Создаем масив месяцев от текущего назад 5 месяцав (всего отображается 6).
        monthsData = [0] * 6
        curYear = datetime.datetime.now().year
        curMonth = datetime.datetime.now().month
        periodsList = []
        periodsCounter = 0
        while periodsCounter < 6:
            periodsList.insert(0, (curYear, curMonth))
            curMonth -= 1
            if curMonth == 0:
                curMonth = 12
                curYear -= 1
            periodsCounter += 1

        # Теперь в periodsList что-то вроде
        # (2014, 1), (2013, 12), (2013, 11), (2013, 10), (2013, 9), (2013, 8)
        # Создаем на основе этого списка заголовки таблицы анализа
        monthNames = [u'Январь', u'Февраль', u'Март', u'Апрель', u'Май', u'Июнь', u'Июль', u'Август', u'Сентябрь', u'Октябрь', u'Ноябрь', u'Декабрь']
        periodsHeaders = [dict(first = monthNames[i[1]-1], second = i[0]) for i in periodsList]

        # Строка суммы
        t = {}
        d = {}
        for type in (my_uu.models.UType.RASHOD, my_uu.models.UType.DOHOD):
            t[type] = [0] * len(periodsList)

            # Для каждой категории
            d[type] = []
            for (i, cat) in enumerate(categoryList):

                # Получаем суммы по месяцам (только для расходов)
                sumForDays = request.user.uchet_set.filter(category = cat, utype = type)
                sumForDays = sumForDays.extra(select={'month': 'extract( month from date )', 'year': 'extract( year from date )'}).values('year', 'month').annotate(sum = Sum('sum')).order_by('year', 'month')

                # Строка с данными для категории
                rowData = [0] * len(periodsList)
                for dbVal in sumForDays:
                    perVal = (dbVal['year'], dbVal['month'])
                    if perVal in periodsList:
                        periodIndex = periodsList.index(perVal)
                        rowData[periodIndex] += float(dbVal['sum'])
                        t[type][periodIndex] += float(dbVal['sum'])

                # Добавлям строку с категорией только если есть ненулевые данные
                if any(rowData):
                    d[type].append(dict(category = cat.name, data = formatMoneyRow(rowData)))

            t[type] = formatMoneyRow(t[type])

        # Итог работы функции
        pageData['periods']['rashod-month'] = periodsHeaders
        pageData['periods']['dohod-month'] = periodsHeaders
        pageData['dataRows']['rashod-month'] = d[my_uu.models.UType.RASHOD]
        pageData['dataRows']['dohod-month'] = d[my_uu.models.UType.DOHOD]
        pageData['totalRow']['rashod-month'] = t[my_uu.models.UType.RASHOD]
        pageData['totalRow']['dohod-month'] = t[my_uu.models.UType.DOHOD]

    pageData = {
        'periods': {},
        'dataRows': {},
        'totalRow': {}
    }

    addWeekAnaDataToPageData(pageData)
    addMonthAnaDataToPageData(pageData)

    return render(request, 'lk_ana.html', {
        'pageData': json.dumps(pageData, cls=DjangoJSONEncoder),
    } )


# Страница импорта
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_IMP)
def lk_imp(request):
    return render(request, 'lk_imp.html', { 'request': request })


# Страница экспорта
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_EXP)
def lk_exp(request):
    return render(request, 'lk_exp.html', { 'request': request })


# Импорт данных через аякс
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_IMP)
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


# Экспорт данных
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_EXP)
def lk_exp_csv(request):

    res = u""
    plainTextContentType = "text/plain; charset=utf-8"

    def uchetToPlainText(u, replaceCategoryName = None):
        category = u.category.name
        if replaceCategoryName:
            category = replaceCategoryName
        return u"{0};руб;{1};{2};{3};{4}\n".format(u.sum, category, u.account.name, u.date, u.comment)

    # Проходим все операции
    for u in request.user.uchet_set.order_by('date').all():

        category = u.category.name

        # Если операция перевода, то для нее создаем вместо категории - для расходной - КУДА, для доходной - ОТКУДА
        # if u.utype.id == my_uu.models.UType.PEREVOD:
        #     if u.sum < 0:
        #         corUchet = request.user.uchet_set.filter(date = u.date, utype = u.utype, sum = -u.sum, comment = u.comment)
        #     if u.sum > 0:
        #         corUchet = request.user.uchet_set.filter(date = u.date, utype = u.utype, sum = -u.sum, comment = u.comment)
        #     if corUchet.count() == 0:
        #         errMsg = u'Ошибка.\n'
        #         errMsg += u'Для указаной ниже ошибочной операции перевода не найдена парная ей операция перевода.\n'
        #         errMsg += u'Для каждой операции перевода должна быть ровно одна парная ей операция перевода: с той же суммой, только с противоположным знаком, от той же даты, с тем же комментарием.\n'
        #         errMsg += u'Ошибочная операция перевода:\n'
        #         errMsg += uchetToPlainText(u)
        #         return HttpResponse(errMsg, content_type=plainTextContentType)
        #     if corUchet.count() > 1:
        #         errMsg = u'Ошибка.\n'
        #         errMsg += u'Для указаной ниже ошибочной операции перевода найдено более одной парной ей операции перевода.\n'
        #         errMsg += u'Для каждой операции перевода должна быть ровно одна парная ей операция перевода: с той же суммой, только с противоположным знаком, от той же даты, с тем же комментарием.\n'
        #         errMsg += u'Ошибочная операция перевода:\n'
        #         errMsg += uchetToPlainText(u)
        #         return HttpResponse(errMsg, content_type=plainTextContentType)
        #     category = corUchet[0].account.name

        res += uchetToPlainText(u, category)

    httpResp = HttpResponse(res, content_type=plainTextContentType)
    return httpResp


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

    # Делаем проверку, если нужно оплатить, значит не даем сохранять запись.
    # По идее мы должны разрешать изменять, но тогда может возникнуть хак что юзер будет вносить записи
    # за старую дату а потом изменять за новую тем самым обойдет ограничение. Чтобы этого хака не было, да и
    # т.к. так проще реализовать, я запрещаю и редактирование и создание. Т.е. если у пользователя дохера записей
    # более 40, то он не сможет их даже редачить в бесплатном режиме.
    if request.user.get_profile().errorOnSaveUchet():
        raise RuntimeError('Попытка сохранить/отредактировать запись в режиме когда эта возможность ограничена и для снятия огранчения нужно оплатить')

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
            uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_EDT_UCH)
            serverRowId = rowDbData['serverRowId']
            del rowDbData['serverRowId']
        else:
            uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_ADD_UCH)

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
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_DEL_UCH)
def lk_delete_uchet_ajax(request):
    rowForDelete = json.loads(request.POST['rowForDelete'])
    rowId = rowForDelete['serverRowId']
    my_uu.models.Uchet.objects.get(id= rowId).delete()
    return JsonResponseWithStatusOk(accountBalanceList = _getAccountBalanceList(request))


# Загрузить данные учета за период
@uu_login_required
def lk_load_uchet_ajax(request):

    # Сохраняем период за который юзер запросил просмотр
    userProfile = request.user.get_profile()
    userProfile.view_period_code = json.loads(request.body)['viewPeriodCode']
    userProfile.save()

    # Возвращаем записи за этот период
    uchetRecords = _getUchetRecordsList(userProfile.getUchetRecordsInViewPeriod())
    return JsonResponseWithStatusOk(uchetRecords = uchetRecords)


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
        uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_EDT_SET)
        a = getattr(request.user, userPropName).get(id = newAccountData['id'])
    else:
        uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_ADD_SET)
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
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_DEL_SET)
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


def _getAdmExpRecords():

    # Подсчитываем мин макс дату учета и число дней с журналами операций
    userStat = User.objects.all().annotate(
        min_dt = Min("eventlog__datetime"),
        max_dt = Max("eventlog__datetime"),
        http_referer = Max("userprofile__http_referer"),
    )
    userStat = userStat.order_by('id').values()
    for u in userStat:
        u['min_dt'] = u['min_dt'].date() if u['min_dt'] else None
        u['max_dt'] = u['max_dt'].date() if u['max_dt'] else None

        eventLogObjects = my_uu.models.EventLog.objects.filter(user = u['id']).extra(select = {'date': 'DATE(datetime)'})
        u['count_dt'] = len(eventLogObjects.values_list('date', flat=True).distinct())

        # Регулярность (дней работы за последне 6 дней, если 3 и более, то считаю его активным)
        u['reg'] = eventLogObjects.filter(datetime__gte = datetime.datetime.now()-datetime.timedelta(days=6))
        u['reg'] = len(u['reg'].values_list('date', flat=True).distinct())

        uchetRecords = my_uu.models.Uchet.objects.filter(user = u['id'])
        u['count_dt_op'] = uchetRecords.values_list('date', flat=True).distinct().count()
        u['count_op'] = uchetRecords.count()

    return userStat

# Страница Анализ личного кабиета
@uuAdmLoginRequired
@uuRenderWith('adm_exp.html')
def adm_exp(request):

    userStat = _getAdmExpRecords()
    return locals()


# Аналогична adm_exp только выводит юзеров с регулярностью 3 и более (т.е. только действующих сейчас юзеров)
@uuAdmLoginRequired
@uuRenderWith('adm_exp.html')
def adm_exp_reg(request):

    userStat = filter(lambda i: i['reg'] >= 3, _getAdmExpRecords())
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
        uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_UNSUBSCR)

    # Подписка
    if 'sub' in request.POST:
        my_uu.models.Unsubscribe.objects.get(user=user).delete()
        uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_SUBSCR)

    return HttpResponseRedirect(reverse(unsubscr_view, kwargs={'obfuscatedUserId': obfuscatedUserId}))


# Запрос ОС почему не стали пользоваться
# Важно - доступ без авторизации на эту страницу.
@uuRenderWith('feedback_request.html')
def feedback_request(request, obfuscatedUserId):

    # Передаем в шаблон из УРЛа
    oUserId = obfuscatedUserId
    return locals()


# Этот УРЛ для получения ОС отказников (уже отпрвка)
def feedback_request_ajax(request):

    requestBody = json.loads(request.body)

    # Юзера важно брать не из request, а из ID из УРЛа.
    # Так как вход на эту страницу должен быть без авторизации (чтоб из емейла работали ссылки).
    obfuscatedUserId = requestBody['oUserId']
    user = User.objects.get(id = my_uu.utils.restoreId(int(obfuscatedUserId)))

    # Посылаем письмо
    my_uu.utils.sendFeedbackEmail(
        user.id,
        user.email,
        requestBody['text']
    )

    return JsonResponseBuilder().buildHttpJsonResponse()


# Страница оплаты
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_PAY)
def lk_pay(request):
    return render(request, 'lk_pay.html', {
        'payModeDescription': request.user.get_profile().getPayModeDescription()
    })


def confirmPayment(invId, eventConstant):

    # Находим запись платежа, созданную вначале процесса оплаты
    #p = my_uu.models.Payment.objects.get(id = invId)
    p = my_uu.models.Payment.objects.get(id = 11)

    # Сохраняем событие что платеж поступил
    #uuTrackEventDynamic(p.user, eventConstant)

    # Отмечаем платеж принятым, с этого момента режим юзера будет сменен на "Оплаченный"
    #p.date_payment = datetime.datetime.now()
    #p.save()

    # Письмо мне что юзер оплатил
    import utils
    utils.sendEmailPaymentReceived(p)


# Уведомление об оплате, надо внести платеж юзера в БД, от РОБОКАССЫЫ
def robokassa_result_url(request):
    confirmPayment(request.POST['InvId'], my_uu.models.EventLog.EVENT_ROBOKASSA_PAY_NOTIFY)
    return HttpResponse('OK' + request.POST['InvId'])


# Уведомление об оплате, надо внести платеж юзера в БД, от Z-PAYMENT
def zpayment_result_url(request):
    confirmPayment(request.POST['LMI_PAYMENT_NO'], my_uu.models.EventLog.EVENT_ZPAYMENT_PAY_NOTIFY)
    return HttpResponse('YES')


# Возвращает УРЛ на который надо отредиректить юзера чтобы инициализировать оплату в платежном шлюзе.
def getPaymentGatewayInitPayUrl(userEmail, cost, invId):

    # УРЛ интерфейса оплаты для юзера в Z-PAYMENT
    import urllib
    if True:
        return "https://z-payment.com/merchant.php?" + urllib.urlencode({
                u'LMI_PAYEE_PURSE': 14574,
                u'LMI_PAYMENT_AMOUNT': cost,
                u'LMI_PAYMENT_DESC': 'Оплата использования сервиса my-uu.ru',
                u'LMI_PAYMENT_NO': invId,
                u'CLIENT_MAIL': userEmail
            })
    else:

        # Формирование подписи
        def getCrc(login, outSum, invId, shpItem, mrchPass):
            sCrcBase = u"{0}:{1}:{2}:{3}:shpItem={4}".format(login, outSum, invId, mrchPass, shpItem)
            import md5
            s = md5.new(sCrcBase).hexdigest()
            return s

        # Тестовый сервер робокассы для отладки
        server1 = u"http://test.robokassa.ru/Index.aspx?"

        # Боевой сервер робокассы
        server2 = u"http://auth.robokassa.ru:80/Merchant/Index.aspx?"

        return server2 +  + urllib.urlencode({
            u'MerchantLogin': u'my-uu.ru',
            u'OutSum': cost,
            u'InvoiceID': invId,
            u'shpItem': 1,
            u'SignatureValue': getCrc(u'my-uu.ru', cost, invId, 1, u'RFCDeH8w'),
            u'Description': u'Оплата использования сервиса my-uu.ru',
            u'Culture': u'ru',
            u'Encoding': u'utf-8'
        })


# Этот метод вызывается со страницы "Оплата" для того чтобы сформировать УРЛ по которому отредиректить юзера
# для оплаты выбранного им периода работы сервиса. УРЛ содержит параметры которые должен передать магазин
# платежному шлюзу. Все эти параметры вычисляются в этом методе на сервере.
@uu_login_required
@uuTrackEventDecor(my_uu.models.EventLog.EVENT_DO_ORDER)
def do_order_ajax(request):

    periodCode = json.loads(request.body)['period']
    COST_DICT = {
        'days30': 30,
        'days60': 60,
        'days90': 90,
        'days120': 120,
    }

    # Цена которую должен заплатить юзер
    cost = COST_DICT[periodCode]
    payment = my_uu.models.Payment(date_created = datetime.datetime.now(), sum = cost, user = request.user)
    payment.save()

    # Получаем УРЛ и пост-данные которые надо полать на этот УРЛ в платежный шлюз
    url = getPaymentGatewayInitPayUrl(request.user.email, cost, payment.id)
    return JsonResponseWithStatusOk(url = url)
