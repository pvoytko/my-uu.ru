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
import utils
import simplejson
import io
import decimal
import calendar
import annoying.decorators
import annoying.functions

import json
import datetime

import my_uu.models
import my_uu.utils
import plogic
from django.views.decorators.csrf import csrf_exempt
import django.http
import pvl_http.funcs
import pvl_datetime_format.funcs
import os.path
import pvl_async.funcs

import pvl_backend_ajax.funcs
from django.views.decorators.csrf import csrf_exempt
import annoying.decorators

import pvl_version.funcs

from django.db.models import Q


def extractAngularPostData(request, *keys):
    postData = simplejson.loads(request.body)
    result = []
    if keys:
        for k in keys:
            result.append(postData[k])
    return result


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


# Главная страница 2.
@annoying.decorators.render_to("lpgen_main.html")
def page_main(request):

    # Год в футере
    return {
        'lpgm_cur_year': datetime.datetime.now().year,
    }


# Калькулятор
@annoying.decorators.render_to("page_fin_calc.html")
def page_fin_calc(request):

    return {

    }


class MyUUAuthForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField()


# Данный класс получает на вход Python-объект, и возвращает его в формате JSON браузеру.
class JsonResponse(HttpResponse):
    def __init__( self, request, data, *args, **kwargs ):
        data = simplejson.dumps( data )

        # Тут раньше была такая строка
        # mime = "application/json" if "application/json" in request.META['HTTP_ACCEPT_ENCODING'] else 'text/plain'
        # Но обнаружилось что в старых раузерах заголовок не HTTP_ACCEPT_ENCODING а HTTP_ACCEPT и тут возникала ошибка
        # и тогда я решил зачем вообще эта проверка буду всегда json отдавать.
        mime = "application/json"

        super( JsonResponse, self ).__init__( data, mime, *args, **kwargs )


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

    # Для всех юзеров обязательно создаем профиль (доп. набор полей к джанговской модели юзера) и шаги руководства
    profile = my_uu.models.UserProfile.objects.get_or_create(user=u)
    manualSteps = my_uu.models.ManualSteps.objects.get_or_create(user = u)

    # Устанавливаем HTTP Referer для юзера
    import urllib
    if 'uu_ref' in request.COOKIES:

        # Эта сервия преобразований приводит к юникодной строке в которой русские буквы
        inpHttpRef = urllib.unquote(request.COOKIES['uu_ref']).decode('utf8')
        u.userprofile.http_referer = urllib.unquote(str(inpHttpRef)).decode('utf-8')
        u.userprofile.save()

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

    uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_REGISTERED)

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

            # Находим юзера или записываем None
            user = django.contrib.auth.models.User.objects.filter(email = data['email'])
            user = user[0] if user.exists() else None

            # Если не выставить бекэнд то потом ошибка при получении юзера.
            if user:
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
    uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_LOGOUT)
    return django.contrib.auth.views.logout(request, next_page = reverse('page_main_url'))


# Страница регистрации или входа
def begin(request):

    # Если юзер уже прошел аутентификацию посылаем его в ЛК
    if request.user.id is not None:
        return HttpResponseRedirect(reverse('page_lk_uch_url'))

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


# Сохраняет запись о событии
def uuTrackEventDynamic(user, eventConstant):
    user.eventlog_set.create(event2 = eventConstant[0])


# Начало
@uu_login_required
@annoying.decorators.render_to('lk_beg.html')
def lk_beg(request):

    # ms = request.user.manualsteps
    # showManualStepsIfNotDisplayedEarler = ms.datetime_subscribe is None and ms.datetime_cancel is None
    
    return locals()


# Эта фукцния возвращает список счетов
# для показа под таблией учета на странице учета.
def _getAccountBalanceList(request):

    # Список счетов юзера со суммой
    accountBalanceList = my_uu.models.Account.objects.filter(user=request.user, visible=True)
    accountBalanceList = accountBalanceList.annotate(balance = Sum('uchet__sum'))
    accountBalanceList = accountBalanceList.order_by('position', 'id')

    # Если счетов много то ошибка
    if len(accountBalanceList) > 28:
        raise RuntimeError('Слишком большое количество счетов, интерфейс пока не рассчитан на такое количество.')

    # Формируем из querysert список словарей с полями
    ll = list(accountBalanceList.values('id', 'name', 'balance', 'balance_start'))
    for r in ll:
        if r['balance'] is None:
            r['balance'] = 0
        r['balance'] += r['balance_start']

        # Урл на
        r['al_filter_url'] = pvl_version.funcs.getUrlByName('page_lk_uch_url') + 'last_all/{}/None/'.format(r['id'])

    return ll


# Список категорий на старнице учета в окне добавления операции - без групп
def _getCategoryListForAddUchetDlg(request):
    categoryList_qs = my_uu.models.Category.objects.filter(
        user=request.user,
        scf_visible=True,
    )
    categoryList_qs = categoryList_qs.order_by('position', 'id')
    res = []
    for n, cat in enumerate(categoryList_qs):

        indent = my_uu.plogic.getCategoryIndentLevel(cat)

        is_group = cat.scf_is_group

        text_caption = u'[[[[ {} ]]]]'.format(cat.scf_name) if is_group else cat.scf_name
        display_and_indent = (u'....' * indent) + text_caption

        res.append({
            'id': cat.id,
            'scf_name': u"" if is_group else cat.scf_name,
            'lkcm_dohod_rashod_type': cat.lkcm_dohod_rashod_type,
            'scf_display_name': display_and_indent,
        })
    return res


# Главная страница личного кабиета
@uu_login_required
def page_lk_uch(request, period = None, account_id = None, category_id = None):

    # Определяем надо ли показать юзеру сообщение что нужна оплата, и если надо, отслеживем событие.
    # тут была ошибка что нет профиля так что удаляем
    # showAddUchetDialog = request.user.userprofile.showAddUchetDialog()
    # if not showAddUchetDialog:
    #     uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_PAYMENT_NEED_DIALOG)

    # Определяем надо ли показать юзеру сообщение что осталось менее 5 дней
    # get5DaysPaidLeft = request.user.userprofile.get5DaysPaidLeft()
    # if not (get5DaysPaidLeft is None):
    #     uuTrackEventDynamic(request.user, my_uu.models.EventLog.EVENT_5DAYS_PAID_LEFT_MESSAGE)

    # ID выбранного account_id и category_id для фильтра или None
    period_id, account_id, category_id = plogic.getAccountIdAndCategoryIdFromUchetPageUrl(request.path)

    # Если период - по дням или неделям или кварталам, для такого периода нет значений в списке фильтров
    # поэтому добавляем значениям.
    addFilterPeriodChoices = []
    if period_id[0] in ('d', 'q', 'w', 'y'):
        caps = {
            'd': u'день',
            'w': u'неделя',
            'q': u'квартал',
            'y': u'год',
        }
        period_str = u"{0} {1}".format(caps[period_id[0]], period_id[1:])
        addFilterPeriodChoices.append((period_id, period_str))

    # QS записей учета для отображения в таблице при открытии страницы
    # фильтруем согласно выбранного счета и категории
    uchet_records_qs = plogic.getUserUchetRecords(request.user)
    uchet_records_filtered = plogic.filterUchetRecordsByPeriodAndAccountAndCategory(
        uchet_records_qs,
        period_id,
        account_id,
        category_id,
    )
    uchet_records = list(uchet_records_filtered.values(
        'id',
        'date',
        'utype__name',
        'myum_date_rep',
        'myum_time',
        'sum',
        'account__name',
        'category__scf_name',
        'comment',
    ))

    # Форматируем дату
    for u in uchet_records:
        u['ur_date_str'] = pvl_datetime_format.funcs.dateToStr(u['date'])
        u['ur_time_str'] = pvl_datetime_format.funcs.timeToStr(u['myum_time'])

    return render(request, 'page_lk_uch.html', {
        'uchetRecordsJson': json.dumps(list(uchet_records), cls=DjangoJSONEncoder),
        'uTypeList': my_uu.models.UType.objects.all().order_by('id'),
        'accountList': my_uu.models.Account.objects.filter(user=request.user, visible=True).order_by('position', 'id'),
        'categoryList': my_uu.models.Category.objects.filter(user=request.user, scf_visible=True).order_by('position', 'id'),
        'accountBalanceListJson': json.dumps(_getAccountBalanceList(request), cls=DjangoJSONEncoder),
        'categoryListNoGroupJson': json.dumps(_getCategoryListForAddUchetDlg(request), cls=DjangoJSONEncoder),
        'viewPeriodSetJson': json.dumps(list(my_uu.models.UserProfile.VIEW_PERIOD_CODE_CHOICES) + addFilterPeriodChoices, cls=DjangoJSONEncoder),
        'viewPeriodMonthSetJson': json.dumps(my_uu.plogic.getUchetMonthSet(request.user), cls=DjangoJSONEncoder),
        # 'showAddUchetDialog': 1 if showAddUchetDialog else 1, # 1 или 0 - т.к. JS не понимает True / False
        # 'get5DaysPaidLeft': get5DaysPaidLeft,

        # ID счета, который был выбран в фильтре в списке счетов, и передан в параметре УРЛ
        # преобразование к целому нужно т.к. сравнние с id не работает иначе.
        'lku_filtered_account_id': account_id,
        'lku_filtered_category_id': category_id,

        # Текущий просматриваемый период
        'lku_filtered_period_id': period_id,
    })


# Страница Счета личного кабиета
@uu_login_required
def lk_acc(request):


    # Получаем счета и категории с указанием количества записей
    rowsA = my_uu.models.Account.objects.annotate(count = Count('uchet'), balance_current = Sum('uchet__sum')).order_by('position')
    rowsA = rowsA.filter(user=request.user).values('id', 'name', 'count', 'position', 'visible', 'balance_start', 'balance_current')
    for r in rowsA:
        if r['balance_current'] is None:
            r['balance_current'] = 0
        r['balance_current'] += r['balance_start']

    # Результат
    return render(request, 'lk_acc.html', {
        'request': request,
        'accountListJsonString': simplejson.dumps(list(rowsA), use_decimal=True),
    } )


# Страница Категории личного кабиета
@uu_login_required
def lk_cat(request):

    # Получаем счета и категории с указанием количества записей
    # Категории у кого задан родитель - игнорим, т.к. они будут обработаны ниже.
    user = plogic.getAuthorizedUser(request)
    user_categories_qs = my_uu.models.Category.objects.filter(
        user=user,
    ).annotate(
        lkcm_count = Count('uchet')
    ).order_by('position', 'id')

    categories_list = list(
        user_categories_qs.filter(
            scf_parent__isnull=True,
        )
    )

    result = []
    while categories_list:

        # Извлекем очередную категорию
        c = categories_list[0]
        categories_list = categories_list[1:]

        # Получаем все дочерни категории если есмть
        childs_list = list(user_categories_qs.filter(scf_parent = c.id))
        if childs_list:
            categories_list = childs_list + categories_list

        # Поля из БД читаем
        dict_cat = {}
        for f in (
            'id',
            'scf_name',
            'scf_comment',
            'lkcm_count',
            'scf_visible',
            'lkcm_dohod_rashod_type',
        ):
            dict_cat[f] = getattr(c, f)
        result.append(dict_cat)

        # Для группы количество не имеет смысла
        if c.scf_is_group:
            dict_cat['lkcm_count'] = '--'

        # бюджет в виде строки
        # Если задана периодичность и значение то выводим
        if c.lkcm_budget_period and c.lkcm_budget_value is not None:
            budget_with_period_str = my_uu.plogic.getBudgetStr(
                c.lkcm_budget_period, c.lkcm_budget_value
            )

        else:

            # Для группы не имеет смысла
            if c.scf_is_group:
                budget_with_period_str = u'--'

            # Расход или додход которому не задана периодиность или сумма
            else:
                budget_with_period_str = u'не задано'


        # строковое значение типа категории - расход или доход
        type_val = result[-1]['lkcm_dohod_rashod_type']
        type_str = my_uu.plogic.convertChoicesDbValueToDisplayValue(
            my_uu.models.LKCM_DOHOD_RASHOD_TYPE_CHOICES1,
            type_val,
        )
        if c.scf_is_group:
            type_str = u'Группа'

        result[-1].update({

            # бюджет в виде строки
            'lkc_budget_with_period_str': budget_with_period_str,

            # строковое значение типа категории - расход или доход
            'lkc_cat_type_str': type_str,

            # Флаг используется для показа разного окна редактирования - для группы свое
            'lkc_is_group': c.scf_is_group,

            # Для родительской категории в поле надо выозвращать ID
            # а не объхект иначе не json свериализейбл
            # Это используется для редактирования в форме (выбор текущей группыы)
            # и для передачи обратно на сервер.
            'scf_parent': c.scf_parent_id,

            # Уровень отступа (для дочерних) - 0, 1, 2 и т.п.
            # для отображения дерева в списке
            'scfs_indent': my_uu.plogic.getCategoryIndentLevel(c),
        })

    # Значения для выпадающего списка групп
    groups_qs = my_uu.models.Category.objects.filter(user=user, scf_is_group=True).order_by('position', 'id')
    groups_choices = [ [g.id, g.scf_name] for g in groups_qs ]

    return render(
        request,
        'lk_cat.html',
        {
            'request': request,

            # Перечень категорий
            'lkc_category_list_json': json.dumps(result),

            # Варианты периодичности для бюджета категорий, кроме варианта "Все"
            'lkc_budget_periods_choices_json': json.dumps(my_uu.models.LKCM_BUDGET_PERIOD_CHOICES1),

            # Варианты Групп
            'acs_group_choices_json': json.dumps(groups_choices),
        }
    )


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
        return (date.isocalendar()[1], date.year)


    def getWeekIndexForDate(self, date):
        w = self._getWeekNum(date)
        if w in self.weekList:
            return self.weekList.index(w)
        else:
            return None


# Страница Анализ личного кабиета
@uu_login_required
def lk_ana(request):

    period = request.GET.get('lka_period', None)
    end_date = request.GET.get('lka_end_date', '')

    # Если период не задан, то берем месяц.
    if period is None:
        period = 'month'

    return render(request, 'lk_ana.html', {
        'lka_period': period,

        # Дата по которую отчет
        'lkas_end_date': end_date,

    })


# Получая список словарей, сортирует их по одному или нескольким полям.
# Пример использования
# resultList - список входных данных, например
#      date                        client_code_name        sum
#      01.06.2016                LESC_2                1000
#      01.07.2016                LESC_        2                2000
#      01.06.2016                LESC_1                3000
#      01.07.2016                LESC_1                1000
# Вызываем
#      # Сортируем входной список по полям date в прямом
#      # и затем по полю client_code_name в обратном порядке
#      resultList = soryByFields(resultList, ['date', '-client_code_name'])
# На выходе будет
#      date                        client_code_name        sum
#      01.06.2016                LESC_2                1000
#      01.06.2016                LESC_1                3000
#      01.07.2016                LESC_        2                2000
#      01.07.2016                LESC_1                1000
def sortByFields(iterable, sortFields):
   def getSortFuncByFields(fields):
       def srtFunc(a, b):
           for f in fields:
               isInverse = f.startswith('-')
               cleanFieldName = f[1:] if isInverse else f
               r = cmp(a[cleanFieldName], b[cleanFieldName])
               if isInverse:
                   r = -r
               if r != 0:
                   break
           return r
       return srtFunc
   data2 = sorted(iterable, getSortFuncByFields(sortFields))
   return data2


# Получая список словарей, группирует их по полям (одному или нескольким),
# выполня агрегацию (sum, min, max) для заданных полей (одного или нескольких)
# Входной список д.б. предварительно отсортирован по полям по которым группируем
# иначе непредсказуемый результат. Для сортировки см. функцию sortByFields
# Пример использования
# resultList - список входных данных, например такой
#      date                        client_code_name        sum
#      01.06.2016                LESC                        1000
#      01.06.2016                LESC                        2000
#      01.06.2016                LESC                        3000
#      01.07.2016                LESC                        1000
# Вызываем
#      # Группируем по полю date, а поле sum суммируем
#      resultList = groupByFields(resultList, ['date', ], {'sum': lambda a,b: a+b})
# На выходе будет
#      date                        client_code_name        sum
#      01.06.2016                LESC                        6000
#      01.07.2016                LESC                        1000
# Что произошло
#      пройти по всем словаряем списка resultList и для каждого нового значения 'date'
#      включить этот словарь на выход, а столбец 'sum' образовать как
#      сумма всех полей sum из всех словарей с одним полем date
# Внимание! agregates аргумент не работает пока как надо, только суммирует всегда (см. код функции).
# Надо доработать функцию.
def groupByFields(iterableWithDicts, groupFields, agregates):
   r = []
   prevItem = None
   for i in iterableWithDicts:

       # Для первого элемента - просто добавляем его на выход
       if not r:
           r.append(i)
           prevItem = i
           continue

       # Определяем именилось ли одно из группрующий полей
       isGroupChanged = False
       for f in groupFields:
           if prevItem[f]!=i[f]:
               isGroupChanged = True

       # Если группа изменилась, то добавить новый элемент
       if isGroupChanged:
           prevItem = i
           r.append(i)

       # Иначе - выполнить агрегацию по каждому из полей
       else:
           for ak, av in agregates.iteritems():
               prevItem[ak] = prevItem[ak] + i[ak]

   return r


# Преобразуем данные из вида списка в вид сводной таблицы
# rowField = строка или список. Если список, то попадут все уникалные по переданным названиям полей.
#             Название поля во входной таблице, в котором содержатся значения, которые в сводной
#             таблице должны попасть в строки.
# colField = аналогично rowField, только для столбцов.
# valField - название поля во входных строках, в котором значение для отображения в сводной таблице
# sortRowsFunc - может быть None. функция, на вход которой поступают заголовки всех строк, и она должна вернуть их в отсортированном нужном виде образом
# sortColsFunc - см. sortRowsFunc, только эта функция для столбцов.
# rowsTotalHeader строка заголовок итогового столбца, если None то заголовок пустой
# rowsTotalFunc функция получающая на вход список значений строки
#             и возвращающая значние для итогового столбца если None то итогового столбца нет
# rowsValues - если указаны значения, то берутся для строк
# colsValues - см. rowsValues, тлько для столбцов.
# colsTotalHeader - аналогично как и для строк.
# colsTotalFunc - аналогично как и для строк.
# Возвращает словарь из значений
#     isEmpty - True - False - есть ли данные
#     rows - заголовки строк
#     columns - заголовки столбцов
#     values - словарь словарей (значения, сначала строки, потом столбцы)
def convertTableDataToPivotDate(
        tableData,
        rowField,
        colField,
        valField,
        sortRowsFunc = None,
        sortColsFunc = None,
        rowsValues = None,
        colsValues = None,
        rowsTotalHeader = None,
        rowsTotalFunc = None,
        colsTotalHeader = None,
        colsTotalFunc = None
    ):
    this = {}
    this['rows'] = []
    if rowsValues:
        this['rows'] = rowsValues
    this['columns'] = []
    if colsValues:
        this['columns'] = colsValues
    this['values'] = {}

    def getOneOrSeveralFields(record, fieldOrFields):
        if isinstance(fieldOrFields, basestring):
            return record[fieldOrFields]
        else:
            res = {}
            for f in fieldOrFields:
                res[f] = record[f]
            return res

    from templatetags.get_by_key import getHashable

    for record in tableData:
        prog = getOneOrSeveralFields(record, rowField)
        wd = getOneOrSeveralFields(record, colField)
        if prog not in this['rows']:
            this['rows'].append(prog)
            if sortRowsFunc:
                this['rows'] = sortRowsFunc(this['rows'])
        if wd not in this['columns']:
            this['columns'].append(wd)
            if sortColsFunc:
                this['columns'] = sortColsFunc(this['columns'])
        if getHashable(prog) not in this['values']:
            this['values'][getHashable(prog)] = {}
        this['values'][getHashable(prog)][getHashable(wd)] = record[valField]
    this['isEmpty'] = not this['rows'] or not this['columns']

    # Теперь проходим по всем строкам и столбцам и если по ним нет данных - то создаем пустые словари
    # Если этого не сделать, то при попытке получить из такой строки get_by_key значение в HTML - вылезет ошибка
    # что у None нет get_item метода.
    if rowsValues:
        for r in rowsValues:
            if r not in this['values']:
                this['values'][r] = {}

    # Итого в строке
    this['rowsTotalHeader'] = u''
    if rowsTotalHeader:
        this['rowsTotalHeader'] = rowsTotalHeader
    this['rowsTotalValues'] = None
    if rowsTotalFunc:
        this['rowsTotalValues'] = {}
        for prog in this['rows']:
            if prog in this['values']:
                this['rowsTotalValues'][prog] = rowsTotalFunc(this['values'][prog])

    # Итого под столбцом
    this['colsTotalHeader'] = u''
    if colsTotalHeader:
        this['colsTotalHeader'] = colsTotalHeader
    this['colsTotalValues'] = None
    if colsTotalFunc:
        this['colsTotalValues'] = {}
        for col in this['columns']:
            colValues = []

            # Сначала формируем список, в котором столько элементов сколько строк,
            # каждый элемент - это значение из этого столбца и этой строки или None если его нет
            for r in this['rows']:
                cellValue = None
                if (getHashable(r) in this['values']) and (getHashable(col) in this['values'][getHashable(r)]):
                    cellValue = this['values'][getHashable(r)][getHashable(col)]
                colValues.append(cellValue)

            # Суммируем значения
            this['colsTotalValues'][col] = colsTotalFunc(colValues)

    return this

# Источник http://stackoverflow.com/questions/4130922/how-to-increment-datetime-by-custom-months-in-python-without-using-library
# Добавляет заданное количство месяцев к дате.
def addMonths0(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12 )
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)


def addMonths1(sourcedatetime, months):
    new_dtm = addMonths0(sourcedatetime, months)
    return plogic.convertDateToDateTime(new_dtm)


# Добавляет заданное количство недель к дате-время.
def addWeeks(sourcedatetime, weeks):
    return sourcedatetime + datetime.timedelta(days=7*weeks)


# Возвращает число дней в квартале, к которому относится переданная дата.
# Суммирует число дней каждогоесяца, из которых состоит квартал.
def getDaysInQuart(dt):
    q = getQuartNumber(dt)
    m1, m2, m3 = getMonthsForQuart(q)
    m1ld = addMonths0(dt.replace(day=1, month=m1), 1) - datetime.timedelta(days=1)
    m2ld = addMonths0(dt.replace(day=1, month=m1), 1) - datetime.timedelta(days=1)
    m3ld = addMonths0(dt.replace(day=1, month=m1), 1) - datetime.timedelta(days=1)
    m1dc = m1ld.day
    m2dc = m2ld.day
    m3dc = m3ld.day
    return m1dc + m2dc + m3dc


# квартал вида IV - 2015 из даты
def formatQuartStr(dt):
    return u"{0} - {1}".format([u"I", u"II", u"III", u"IV", ][getQuartNumber(dt)-1], dt.year)

# год вида 2015 из даты
def formatYearStr(dt):
    return unicode(dt.year)

# возвращает номер квартала для даты. Т.е. возвращает одно из чисел: 1 2 3 4
def getQuartNumber(dt):
    return divmod(dt.month-1, 3)[0]+1


# возвращает номерм есяцев для квартала - 1 2 3 для 1 квартала, 10 11 12 для 4-го.
def getMonthsForQuart(q):
    return 3*(q-1) + 1, 3*(q-1) + 2, 3*(q-1) + 3,


def getQuartFirstDate(dt):
    qn = getQuartNumber(dt)
    m1, m2, m3 = getMonthsForQuart(qn)
    return dt.replace(day=1, month=m1)


def getYearFirstDate(dt):
    return dt.replace(day=1, month=1)


# Страница анализа, при ее открытии - в контекст добавляются переменные для показа таблицы
@uu_login_required
def ajax_lk_ana(request):

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

        # Печатаем число
        startDateStr = unicode(startDate.day)
        if startDate.month != endDate.month:
            startDateStr += u" " + utils.formatMonth(startDate.month)
        endDateStr = unicode(endDate.day) + u" " + utils.formatMonth(endDate.month);
        return startDateStr + u"–" + endDateStr;

    def formatDayAndMonth(date):
        return unicode(date.day) + u" " + utils.formatMonth(date.month)

    def formatDayOfWeek(date):
        return [u'Пн', u'Вт', u'Ср', u'Чт', u'Пт', u'Сб', u'Вс'][date.weekday()]

    def getCatOrGroupList(categoryList, groups):
        if groups:
            grList = []
            for c in categoryList:
                if c.name.find(' - ') >= 0:
                    i = c.name.index(' - ')
                    gr = u'[' + c.name[0:i] + ']'
                else:
                    gr = u'[Нет группы]'
                if gr not in grList:
                    grList.append(gr)
            return grList
        else:
            return [cat.name for cat in categoryList]

    def filterUchetByCategoryOrGroup(uchet, categoryList, catOrGroup, groups):
        if groups:
            catFilterList = []
            for c in categoryList:
                if c.name.find(' - ') >= 0:
                    i = c.name.index(' - ')
                    gr = u'[' + c.name[0:i] + ']'
                else:
                    gr = u'[Нет группы]'
                if gr == catOrGroup:
                    catFilterList.append(c.name)
            return uchet.filter(category__name__in = catFilterList)
        else:
            return uchet.filter(category__name__in = [catOrGroup, ])


    def getFromDictDictOrEmpty(dicti, key1, key2, empty_val, periodCode):

        # получая на вход дату и период (день, неделя, месяц, квартал) - на их основе вычисляет id периода)
        # примеры
        #     "Неделя 14 2016" (урл - w2016-14)
        #     или
        #     "24 апр Вс 2016" (d2016.12.01)
        #     или
        #     "Февраль 2016" (2013-02)
        #     или
        #     "I - 2016" (q2013-1)
        period_id = plogic.convertPeriodCodeAndStartDateToPeriodId(periodCode, key2)

        if key1 not in dicti:
            return {
                'lka_cell_val': empty_val,
                'lka_cell_nval_str': '0',
                'lka_cell_period': period_id,
            }
        elem1 = dicti[key1]
        if key2 not in elem1:
            return {
                'lka_cell_val': empty_val,
                'lka_cell_nval_str': '0',
                'lka_cell_period': period_id,
            }
        return {
            'lka_cell_val': my_uu.utils.formatMoneyValue(elem1[key2]),
            'lka_cell_nval_str': str(elem1[key2]),
            'lka_cell_period': period_id,
            }


    def getValFormattedOrZero(dictionary, key):
        if key in dictionary:
            return my_uu.utils.formatMoneyValue(dictionary[key])
        else:
            return my_uu.utils.formatMoneyValue(0)

    # Цвет задается в виде названия CSS класса, варианты:
    # * pvm_budget_color_green
    # * pvm_budget_color_yellow
    # * pvm_budget_color_red
    def alaGetColorForCategory(prev_period_summ, this_period_summ, budget):
        if this_period_summ < -budget:
            return 'pvm_budget_color_red'
        if prev_period_summ < -budget:
            return 'pvm_budget_color_yellow'
        return 'pvm_budget_color_green'


    def alaGetCategoryFactForPeriod(start_period_func, inc_period_func):

        # Делаем запрос, который нам посчитает бюджет за прошлую неделю и за эту по каждой из категорий
        now = pvl_datetime_format.funcs.getNow()
        cur_week_start_dtm = start_period_func(now)
        prev_week_start_dtm = inc_period_func(cur_week_start_dtm, -1)
        next_week_start_dtm = inc_period_func(cur_week_start_dtm, 1)
        cat_weeks_fact1 = dict(

            # Тут важно без фильтра по типу "Расход", т.к. например комиссия банков - я туда вношу и расходы и доходы
            # и бюджет сумма за месяц - больше 0 получается. Если только по расходам, то меньше.
            my_uu.models.Uchet.objects.filter(
                user = request.user,
                date__gte = prev_week_start_dtm.date(),
                date__lt = cur_week_start_dtm.date(),
            ).values_list('category_id').annotate(
                Sum('sum')
            )
        )
        cat_weeks_fact2 = dict(
            my_uu.models.Uchet.objects.filter(
                user = request.user,
                date__gte = cur_week_start_dtm.date(),
                date__lt = next_week_start_dtm.date(),
            ).values_list('category_id').annotate(
                Sum('sum')
            )
        )
        return cat_weeks_fact1, cat_weeks_fact2


    # Возвращает словарь, где по ID категории - возвращается другой словарь с двумя полями - цвет столбца 1 и 2
    # Цвет задается в виде названия CSS класса, варианты:
    # * pvm_budget_color_green
    # * pvm_budget_color_yellow
    # * pvm_budget_color_red
    def alaGetColorsForCategoryBudgets(request, categoryModelListFiltered2):

        # Делаем запрос, который нам посчитает бюджет за прошлую неделю и за эту по каждой из категорий
        cat_days_fact1, cat_days_fact2 = alaGetCategoryFactForPeriod(
            lambda dt: dt,
            lambda dt, dc: dt + datetime.timedelta(days=dc),
        )
        cat_weeks_fact1, cat_weeks_fact2 = alaGetCategoryFactForPeriod(
            plogic.getFirstMomentOfWeek1,
            addWeeks,
        )
        cat_months_fact1, cat_months_fact2 = alaGetCategoryFactForPeriod(
            plogic.getFirstMomentOfMonth1,
            addMonths1,
        )
        cat_quart_fact1, cat_quart_fact2 = alaGetCategoryFactForPeriod(
            getQuartFirstDate,
            lambda dt, inc: plogic.convertDateToDateTime(addMonths0(dt, 3 * inc)),
        )
        cat_year_fact1, cat_year_fact2 = alaGetCategoryFactForPeriod(
            getYearFirstDate,
            lambda dt, inc: plogic.convertDateToDateTime(dt.replace(year = dt.year + inc)),
        )

        # Сначала формируем список по категориям, и для каждой категории - вносим:
        # * бюджет за день этот и прошлый
        # * бюджет за неделю этот и прошлый
        # * бюджет за месяц этот и прошлый
        # * бюджет за квартал этот и прошлый
        # * бюджет за год этот и прошлый
        # чтобы потом на основе этого списка данных и периодичности бюджета - определить,
        # каким цветом подсвечивать категорию.
        this_and_prev_budget_sums = {}
        for c in categoryModelListFiltered2:

            this_and_prev_budget_sums[c.id] = {

                'tap_day_prev': cat_days_fact1.get(c.id, 0),
                'tap_day_this': cat_days_fact2.get(c.id, 0),

                'tap_week_prev': cat_weeks_fact1.get(c.id, 0),
                'tap_week_this': cat_weeks_fact2.get(c.id, 0),

                'tap_month_prev': cat_months_fact1.get(c.id, 0),
                'tap_month_this': cat_months_fact2.get(c.id, 0),

                'tap_quart_prev': cat_quart_fact1.get(c.id, 0),
                'tap_quart_this': cat_quart_fact2.get(c.id, 0),

                'tap_year_prev': cat_year_fact1.get(c.id, 0),
                'tap_year_this': cat_year_fact2.get(c.id, 0),
            }


        res = {}
        for c in categoryModelListFiltered2:

            # Если не задан бюджет - то без подсветки
            if c.lkcm_budget_value is None or c.lkcm_budget_period is None:
                budget_color = ''
                budget_year_color = ''

            # Иначе, если задан, то вычисляем цвет
            else:

                # смотря какой период задан, те значения и сравниваем
                # для определения цвета по категории
                if c.lkcm_budget_period == my_uu.models.LKCM_BUDGET_PERIOD_DAY:
                    s1 = this_and_prev_budget_sums[c.id]['tap_day_prev']
                    s2 = this_and_prev_budget_sums[c.id]['tap_day_this']
                elif c.lkcm_budget_period == my_uu.models.LKCM_BUDGET_PERIOD_WEEK:
                    s1 = this_and_prev_budget_sums[c.id]['tap_week_prev']
                    s2 = this_and_prev_budget_sums[c.id]['tap_week_this']
                elif c.lkcm_budget_period == my_uu.models.LKCM_BUDGET_PERIOD_MONTH:
                    s1 = this_and_prev_budget_sums[c.id]['tap_month_prev']
                    s2 = this_and_prev_budget_sums[c.id]['tap_month_this']
                elif c.lkcm_budget_period == my_uu.models.LKCM_BUDGET_PERIOD_QUART:
                    s1 = this_and_prev_budget_sums[c.id]['tap_quart_prev']
                    s2 = this_and_prev_budget_sums[c.id]['tap_quart_this']
                elif c.lkcm_budget_period == my_uu.models.LKCM_BUDGET_PERIOD_YEAR:
                    s1 = this_and_prev_budget_sums[c.id]['tap_year_prev']
                    s2 = this_and_prev_budget_sums[c.id]['tap_year_this']
                else:
                    raise RuntimeError(u'Неподдерживаемый код периода бюджета категории в alaGetColorsForCategoryBudgets')

                budget_color = alaGetColorForCategory(s1, s2, c.lkcm_budget_value)

                # для определения цвета по году - всегда сравниваем годовые суммы
                budget_year_color = alaGetColorForCategory(100, 200, 50)

            res[c.id] = {

                # Цвет столбца с бюджетом категории
                'bcbci_color': budget_color,

                # Цвет столбца с бюджетом на год
                'bcbci_year_color': budget_year_color,
            }

        return res


    # Получая на вход строку группы, задача этой функции - заполнить по ней сумму.
    # А если дочерние тоже группы, то вызыват рекурсивно, чтобы заполнить сперва в них
    # а потом уже в самой группе.
    def fillSumForGroupOrSubgroup(periods_start_dates, childs_by_id, output_rows_by_cat_id, cat_id, row):

        # Тогда для этой категории - для каждого столбца
        for col_num, col_val in enumerate(periods_start_dates):

            # Вычисляем сумму по дочерним категориям
            childs_sum = decimal.Decimal('0')
            childs_list = set(childs_by_id[cat_id])
            for child_catergory in childs_list:
                cur_cat_id = child_catergory.id
                cur_row = output_rows_by_cat_id[cur_cat_id]

                # Если дочерная группа тоже явялется подгруппой, то по ней рекурсивно считаем
                if cur_cat_id in childs_by_id:
                    fillSumForGroupOrSubgroup(
                        periods_start_dates,
                        childs_by_id,
                        output_rows_by_cat_id,
                        cur_cat_id,
                        cur_row,
                    )

                val_str = cur_row['lka_cell_data'][col_num]['lka_cell_nval_str']
                childs_sum += decimal.Decimal(val_str)

            # Заносим вычисленную сумму в итоговую таблицу
            row['lka_cell_data'][col_num]['lka_cell_nval_str'] = str(childs_sum)
            row['lka_cell_data'][col_num]['lka_cell_val'] = my_uu.utils.formatMoneyValue(childs_sum)


    # Вызывается чтобы в список добавить категорию и все ее подкатегории (и их подкатегории), рекурсивно
    def addCategoryListAndAllSubcategoriesToList(categoryModelListFiltered_tree, childs_by_id, cat_list):
        for c in cat_list:
            categoryModelListFiltered_tree.append(c)
            if c.id in childs_by_id:
                child_cat_list = childs_by_id[c.id]
                addCategoryListAndAllSubcategoriesToList(
                    categoryModelListFiltered_tree,
                    childs_by_id,
                    child_cat_list,
                )

    # format_header_from_val_func = Функция, применяемая к первой дате периода, возвращает словарь first second для оторажения в заголовке
    # period_count = Число периодов для отображения
    # get_first_period_date_func Функция, применяемая к дате, получает первый день требуемого периода
    # dec_period_func = Функция, применяемая к дате, уменьшает ее на один требуемый период
    # is_groups_on = УСТАРЕЛО не поддерживается
    def addPeriodAnaDataToPageData(
        pageData,
        result_suffix,
        format_header_from_val_func,
        period_count,
        get_first_period_date_func,
        dec_period_func,
        inc_period_func,
        end_date_str,
    ):

        for anaType in ['dohod', 'rashod']:

            # Сколь периодов включая теукщий будет в очтете
            q_count = period_count

            # Дата, с которой берутся данные для построения отчета тут будет. Но сначала - дата начала ткущего периода.
            if end_date_str:
                end_date = pvl_datetime_format.funcs.strToDate(end_date_str)
                data_start_date = get_first_period_date_func(end_date)
            else:
                data_start_date = get_first_period_date_func(datetime.date.today())

            # Первые даты всех периодов для которых строится отчет
            # Названия заголовков
            periods_start_dates = []
            periodsHeaders = []
            data_cur_date = data_start_date
            while q_count > 0:
                periodsHeaders.insert(0, format_header_from_val_func(data_cur_date))
                periods_start_dates.insert(0, data_cur_date)
                q_count -= 1
                if q_count > 0:
                    data_cur_date = dec_period_func(data_cur_date)

            # Фильтруем нужные строки данных для отчета - все, начиная с заданной даты
            # Или у которых дата отчета начиная с этой даты.
            type = { 'rashod': my_uu.models.UType.RASHOD, 'dohod': my_uu.models.UType.DOHOD }[anaType]
            uchet_qs = request.user.uchet_set.filter(utype = type)
            uchet_qs = uchet_qs.filter(Q(date__gte = data_cur_date) | Q(myum_date_rep__gte = data_cur_date))

            # Преобразуем к формату словарей
            # Берём дату для отчета если она задана а если нет то дату операции.
            uchet_list = []
            for r in uchet_qs:
                uchet_list.append({
                    'date': r.myum_date_rep if r.myum_date_rep else r.date,
                    'sum': r.sum,
                    'category__scf_name': r.category.scf_name,
                })
            uchet_list = sortByFields(uchet_list, ['date'])

            # Добавляем поле месяца для сортировки и группировки по нему
            for u in uchet_list:
                u['period_value_sort'] = get_first_period_date_func(u['date'])
                del u['date']

            # Группируем по полям
            uchet_list = sortByFields(uchet_list, ['period_value_sort', 'category__scf_name'])
            uchet_list = groupByFields(uchet_list, ['period_value_sort', 'category__scf_name'], {'sum': lambda a,b: a+b})

            # Преобразуем к формату pivotTable
            pivot_table = convertTableDataToPivotDate(
                uchet_list,
                'category__scf_name',
                'period_value_sort',
                'sum',
                colsTotalFunc=lambda ll: sum([l for l in ll if l])
            )

            # Форматируем
            for u in uchet_list:
                u['sum_str'] = my_uu.utils.formatMoneyValue(u['sum'])

            # Теперь надо сформировать список из категорий, в порядке нужном для пользователя,
            # только те, по которые видимы либо по ним есть данные
            # (остальные убираем, т.е. те где нет данных одновременно невидимые).
            # Если несколько категорий при группировке преобразовались в одну, то на выходе дожна быть только одна.
            category_qs = request.user.category_set
            if anaType == 'rashod':
                category_type_qs = category_qs.filter(lkcm_dohod_rashod_type = my_uu.models.LKCM_DOHOD_RASHOD_TYPE_RASHOD)
            elif anaType == 'dohod':
                category_type_qs = category_qs.filter(lkcm_dohod_rashod_type = my_uu.models.LKCM_DOHOD_RASHOD_TYPE_DOHOD)
            else:
                raise RuntimeError('На странице анализа ошибка программирования в функции получепния данных.')

            categoryModelListAll = list(category_type_qs.order_by('position', 'id'))
            categoryNames = set()
            categoryModelListFiltered1 = []
            for c in categoryModelListAll:

                c.name = c.scf_name

                # Если уже добавили, то пропускаем
                if c.name in categoryNames:
                    pass

                # Если нет данных и невдиима - то пропускаем
                if c.name not in pivot_table['rows'] and not c.scf_visible:
                    pass

                # В остальных случаях - добавляем
                else:
                    categoryNames.add(c.scf_name)
                    categoryModelListFiltered1.append(c)

            # Сейчас категории идут в порядке сортировки. А нам надо дочерние поставить под родительскими.
            # Пример
            #     до http://pvoytko.ru/jx/9CAgthZ36g
            #     после http://pvoytko.ru/jx/6d5q3FUQ31
            # Это делаем в 2 прохода
            # Сначала по ID всех дочерникх собираем
            # А потом их добавляем в общее
            childs_by_id = {}
            categoryModelListFiltered_root = []
            for c in categoryModelListFiltered1:
                par_id = c.scf_parent_id
                if par_id:
                    if par_id in childs_by_id:
                        childs_by_id[par_id].append(c)
                    else:
                        childs_by_id[par_id] = [c]
                else:
                    categoryModelListFiltered_root.append(c)
            categoryModelListFiltered_tree = []
            addCategoryListAndAllSubcategoriesToList(
                categoryModelListFiltered_tree,
                childs_by_id,
                categoryModelListFiltered_root,
            )

            # Если стоит фильтр по периодичности бюджета, то применяем его
            # categoryModelListFiltered2 = []
            # if bperiod:
            #     for c in categoryModelListFiltered_tree:
            #         if bperiod == my_uu.models.LKCM_BUDGET_PERIOD_ALL:
            #             categoryModelListFiltered2.append(c)
            #         elif c.lkcm_budget_period == bperiod:
            #             categoryModelListFiltered2.append(c)
            #         elif c.lkcm_budget_period is None and bperiod == my_uu.models.LKCM_BUDGET_PERIOD_NONE:
            #             categoryModelListFiltered2.append(c)
            # else:
            categoryModelListFiltered2 = categoryModelListFiltered_tree

            # Обновленний список категорий - пересчитывем сумму
            # Но перед этим из записей учета удаляем все что не попадают в выбранные категории.
            uchet_list_cur_filter = []
            allowed_categories = [c.name for c in categoryModelListFiltered2]
            for u in uchet_list:
                if u['category__scf_name'] in allowed_categories:
                    uchet_list_cur_filter.append(u)
            pivot_table = convertTableDataToPivotDate(
                uchet_list_cur_filter,
                'category__scf_name',
                'period_value_sort',
                'sum',
                colsTotalFunc=lambda ll: sum([l for l in ll if l]),
            )
            pageData['totalRow'][anaType + '-' + result_suffix] = [
                getValFormattedOrZero(pivot_table['colsTotalValues'], k) for k in periods_start_dates
            ]

            # в эту переменную сохраняем значения для показа в столбце бюджета
            # попутно проверяем что все они имеют один период и он задан и если да - то сумму будем выводить
            budgets_by_category_id = {}
            for c in categoryModelListFiltered2:

                # Если это группа для нее не имеет смысла
                if c.scf_is_group:
                    budget_str = u'--'
                    budget_val = None
                    budget_year_str = u'--'
                    budget_year_val = None

                # Для категории не задан бюджет
                elif c.lkcm_budget_value is None or not c.lkcm_budget_period:
                    budget_str = u'не задано'
                    budget_val = None
                    budget_year_str = u'не задано'
                    budget_year_val = None

                # Все задано
                else:
                    budget_val = c.lkcm_budget_period
                    budget_str = my_uu.plogic.getBudgetStr(c.lkcm_budget_period, c.lkcm_budget_value)
                    budget_year_val, budget_year_str = my_uu.plogic.getBudgetYearStr(
                        c.lkcm_budget_period,
                        c.lkcm_budget_value,
                    )

                budgets_by_category_id[c.id] = {

                    # значене в столбце бюджета по категории
                    'bbci_val': budget_val,
                    'bbci_str': budget_str,

                    # Строковое значене в столбце бюджета за код
                    'bbci_year_val': budget_year_val,
                    'bbci_year_str': budget_year_str,
                }

            # Вычисляем значение для отображения в самом низу итоговое
            budget_sum_val = 0
            budget_year_sum_val = 0
            budget_prev_period = None
            budget_is_all_present = False
            budget_is_same_period = False
            is_first_iter = True
            for c in categoryModelListFiltered2:

                # Если это группа, то ее пропускаем (не обрабатываем)
                # Т.к. иначе итогоовые суммы выводятся как -- даже если все категории (без групп) задан бюджет.
                if c.scf_is_group:
                    continue

                # Первая итерация -
                if is_first_iter:
                    budget_is_all_present = True
                    budget_is_same_period = True
                    budget_prev_period = c.lkcm_budget_period
                    is_first_iter = False

                # Если очередной мес. бюджет период не равен прошлому - то не надо сумму считать
                if budget_prev_period != c.lkcm_budget_period:
                    budget_is_same_period = False

                # Если не задана сумма - то не надо сумму счситать
                if c.lkcm_budget_value is None or c.lkcm_budget_period is None:
                    budget_is_all_present = False

                # Накапливаем бюджетную сумму, если надо считать
                if budget_is_all_present and budget_is_same_period:
                    budget_sum_val += c.lkcm_budget_value

                # Считаем за год, если надо
                if budget_is_all_present:
                    budget_year_sum_val += budgets_by_category_id[c.id]['bbci_year_val']

            # значение для показа в ячейке суммы в бюджете
            if budget_is_all_present and budget_is_same_period:
                pageData['pa_budget_summ'] = my_uu.plogic.getBudgetStr(budget_prev_period, budget_sum_val)
            else:
                pageData['pa_budget_summ'] = u'--'

            if budget_is_all_present:
                pageData['pa_budget_year_summ'] = my_uu.utils.formatMoneyValue(budget_year_sum_val) + u' в год'
                pageData['pa_budget_quart_summ'] = my_uu.utils.formatMoneyValue(budget_year_sum_val / 4) + u' в кварт.'
                pageData['pa_budget_month_summ'] = my_uu.utils.formatMoneyValue(budget_year_sum_val / 12) + u' в мес.'
                pageData['pa_budget_week_summ'] = my_uu.utils.formatMoneyValue(budget_year_sum_val / 53) + u' в нед.'
                pageData['pa_budget_day_summ'] = my_uu.utils.formatMoneyValue(budget_year_sum_val / 366) + u' в день'
            else:
                pageData['pa_budget_year_summ'] = u'--'
                pageData['pa_budget_quart_summ'] = u'--'
                pageData['pa_budget_month_summ'] = u'--'
                pageData['pa_budget_week_summ'] = u'--'
                pageData['pa_budget_day_summ'] = u'--'

            budget_colors_by_category_id = alaGetColorsForCategoryBudgets(request, categoryModelListFiltered2)


            # Преобразуем к выходному формату:
            # periods:
            #     {anaType}-{period}:
            #         first: ssss, second sssss # заголовки таблицы
            #         first: ssss, second sssss
            # totalRow:
            #     {anaType}-{period}:
            #         ssss, # значения итоговой строки, по одному на каждый столбец
            #         ssss,
            #         ssss,
            # dataRows:
            #     {anaType}-{period}:
            #         {category}: ssss # название категории
            #         {data}: [ssss, ssss, ] значения строки, по одному на каждый столбец
            pageData['periods'][anaType + '-' + result_suffix] = periodsHeaders
            pageData['dataRows'][anaType + '-' + result_suffix] = []
            output_list = pageData['dataRows'][anaType + '-' + result_suffix]
            for r in categoryModelListFiltered2:
                output_list.append({
                    'category': r.scf_name,
                    'lka_category_id': r.id,
                    'lka_cell_data': [getFromDictDictOrEmpty(
                        pivot_table['values'], r.scf_name, k, '0 р.', periodCode
                    ) for k in periods_start_dates],

                    # Бюджет по категории за период бюджета
                    'lka_budget_str': budgets_by_category_id[r.id]['bbci_str'],

                    # Бюджет по категории за год
                    'lka_budget_year_str': budgets_by_category_id[r.id]['bbci_year_str'],

                    # Подсветка серым если категория не видима
                    'lka_is_category_visible': r.scf_visible,

                    # Подсветка цветом если это группа
                    'lka_is_ana_group': r.scf_is_group,

                    # ID Родительсткой строки. Это нужно для сворачивания-разворачивания.
                    'lka_parent_id': r.scf_parent_id if r.scf_parent else None,

                    # Флаг должна она быть развернута или свернута
                    'alka_is_collapsed': not r.scf_is_expanded,

                    # Цвет для итогового бюджета
                    'bcbci_color': budget_colors_by_category_id[r.id]['bcbci_color'],
                    'bcbci_year_color': budget_colors_by_category_id[r.id]['bcbci_year_color'],

                    # Отступ
                    'bcbci_indent': my_uu.plogic.getCategoryIndentLevel(r),
                })


            # Тепреь для каждой категории которая является группой (содержит подкатегрии)
            # нам надо посчитать сумму по бюджетам.
            # До http://pvoytko.ru/jx/Bm7AtDFfrt
            # Нам надо чтобы была сумма
            # Сначаа строим словарь, ключ - ID категории, значение - строкад ля отображения
            # при втором проходе - считаем сумму
            # делаем несколкьо повторов, поднимаясь на уровень выше, пока не дойдем до верха
            output_rows_by_cat_id = {}
            for row in output_list:

                cur_cat_id = row['lka_category_id']
                output_rows_by_cat_id[cur_cat_id] = row
            for row in output_list:

                # Если эта категория имеет дочерние
                # и является коневой то для нее вызываем расчет суммы, а он в свою очередь рекурсивоно посчитает
                # расчет суммы для остальных (дочяерних). Поэтому и нужна проверка чтобы вызвать только для корневых.
                cur_cat_id = row['lka_category_id']
                cur_cat_par_id = row['lka_parent_id']
                if cur_cat_id in childs_by_id and not cur_cat_par_id:
                    fillSumForGroupOrSubgroup(
                        periods_start_dates,
                        childs_by_id,
                        output_rows_by_cat_id,
                        cur_cat_id,
                        row,
                    )

            # Если у групповой строки ни одной дочерней категории
            # с данными (т.е. нет данных), и отметка скрыть ее,
            # то она скрывается (без явной отметки юзером - не скрывается)
            # Раньше эта фиьтрация стояля выше по коду, но была ошибка при расчете суммы по группам
            # та функция ожидала что все категории есть, поэтому блок этого кода
            # по исключению пустых групп сместил ниже в конец.
            child_count_by_id = {}
            for c in output_list:
                if c['lka_category_id'] not in child_count_by_id:
                    child_count_by_id[c['lka_category_id']] = 0
                if c['lka_parent_id']:
                    child_count_by_id[c['lka_parent_id']] += 1
            output_list_new = []
            for c in output_list:
                if c['lka_is_ana_group'] and not child_count_by_id[c['lka_category_id']] and not c['lka_is_category_visible']:
                    continue
                output_list_new.append(c)
            pageData['dataRows'][anaType + '-' + result_suffix] = output_list_new

            # можем ли мотать влево и вправо (есть ли еще периоды) и какой аргумент в урл для этого передавать
            pageData['lka_is_can_left'] = True
            pageData['lka_is_can_right'] = True
            data_start_date_1 = dec_period_func(data_start_date)
            data_start_date_2 = inc_period_func(data_start_date)
            pageData['lka_move_left_end_date'] = pvl_datetime_format.funcs.dateToStr(data_start_date_1)
            pageData['lka_move_right_end_date'] = pvl_datetime_format.funcs.dateToStr(data_start_date_2)



    # Данные для показа на странице
    def getAnaPageData(periodCode, is_groups_on, bperiod, end_date_str):

        pageData = {
            'periods': {},
            'dataRows': {},
            'totalRow': {}
        }
        if periodCode == 'day':

            addPeriodAnaDataToPageData(
                pageData,
                'day',
                format_header_from_val_func = lambda dt: { 'first': formatDayAndMonth(dt), 'second': formatDayOfWeek(dt) },
                period_count = 5,
                get_first_period_date_func = lambda dt: dt,
                dec_period_func = lambda dt: dt - datetime.timedelta(days=1),
                inc_period_func = lambda dt: dt + datetime.timedelta(days=1),
                end_date_str = end_date_str,
            )

        elif periodCode == 'week':

            def formatWeekHeader(d):
                return dict( first = u'Неделя ' + str(plogic.getWeekNumberOfYear(d)), second = getDatesForWeek(d) )

            addPeriodAnaDataToPageData(
                pageData,
                'week',
                format_header_from_val_func = formatWeekHeader,
                period_count = 5,
                get_first_period_date_func = plogic.getFirstMomentOfWeek0,
                dec_period_func = lambda dt: addWeeks(dt, -1),
                inc_period_func = lambda dt: addWeeks(dt, 1),
                end_date_str = end_date_str,
            )

        elif periodCode == 'month':

            monthNames = [u'Январь', u'Февраль', u'Март', u'Апрель', u'Май', u'Июнь', u'Июль', u'Август', u'Сентябрь', u'Октябрь', u'Ноябрь', u'Декабрь']

            addPeriodAnaDataToPageData(
                pageData,
                'month',
                format_header_from_val_func = lambda dt: dict(first = monthNames[dt.month-1], second = dt.year),
                period_count = 5,
                get_first_period_date_func = plogic.getFirstMomentOfMonth0,
                dec_period_func = lambda dt: addMonths0(dt, -1),
                inc_period_func = lambda dt: addMonths0(dt, 1),
                end_date_str = end_date_str,
            )

        elif periodCode == 'quart':

            addPeriodAnaDataToPageData(
                pageData,
                'quart',
                format_header_from_val_func = lambda q_start_date: {'first': formatQuartStr(q_start_date), 'second': ''},
                period_count = 5,
                get_first_period_date_func = getQuartFirstDate,
                dec_period_func = lambda dt: addMonths0(dt, -3),
                inc_period_func = lambda dt: addMonths0(dt, 3),
                end_date_str = end_date_str,
            )

        elif periodCode == 'app_year':

            addPeriodAnaDataToPageData(
                pageData,
                'app_year',
                format_header_from_val_func = lambda q_start_date: {'first': formatYearStr(q_start_date), 'second': ''},
                period_count = 5,
                get_first_period_date_func = getYearFirstDate,
                dec_period_func = lambda dt: dt.replace(year = dt.year - 1),
                inc_period_func = lambda dt: dt.replace(year = dt.year + 1),
                end_date_str = end_date_str,
            )

        else:
            raise RuntimeError(u'Ошибка в функции анализа расходов.')

        return pageData


    periodCode, end_date_str = extractAngularPostData(
        request,
        'periodCode',
        'lkax_end_date',
    )

    # Данные для таблицы
    pageData = getAnaPageData(periodCode, False, None, end_date_str)

    return JsonResponse(request, {
        'pageData': pageData,
    })


# Страница импорта
# @uu_login_required
# @uuTrackEventDecor(my_uu.models.EventLog.EVENT_VISIT_IMP)
# def lk_imp(request):
#     return render(request, 'lk_imp.html', { 'request': request })


# Страница экспорта
@uu_login_required
def lk_exp(request):

    # Нажата кнопка выполнения - выполням команду
    user = plogic.getAuthorizedUser(request)
    if request.method == 'POST' and 'ple_do' in request.POST:

        plogic.asyncMakeExportExcel(user.id)

        # показать сообщение пользователю
        django.contrib.messages.add_message(
            request,
            django.contrib.messages.SUCCESS,
            u'Фоновая задача успешно запущена. Нажмите "обновить" ниже для просмотра лога работы.',
        )

    # Определяем есть ли файл для текущего юзера и его дату-время
    file_path, file_dtm_str = plogic.getExportExcelFileForUserAndDateTime(user)

    # Работает ели задача, если да, то кнопка неактивна
    async_task = pvl_async.funcs.pvlGetLastAsyncTaskOrNone(plogic.AT_MYU_EXPORT_EXCEL)
    is_running, _ = pvl_async.funcs.pvlGetAsyncTaskStatus(async_task)

    return render(
        request,
        'page_lk_exp.html',
        {
            'request': request,
            'ple_file_dtm': file_dtm_str,
            'ple_async_task':  async_task,
            'ple_is_running':  is_running,
        })


# Импорт данных через аякс
# @uu_login_required
# @uuTrackEventDecor(my_uu.models.EventLog.EVENT_IMP)
# def lk_imp_ajax(request):
#     importedData = json.loads(request.body)
#
#     def getOrCreateAccount(accName):
#         return request.user.account_set.get_or_create(name = accName)[0]
#
#     def getOrCreateCategory(catName):
#         return request.user.category_set.get_or_create(name = catName)[0]
#
#     for uchet in importedData:
#         request.user.uchet_set.create(
#             date = datetime.datetime.strptime(uchet[0], '%d.%m.%Y'),
#             utype = my_uu.models.UType.objects.get(name__iexact = uchet[1]),
#             sum = uchet[2],
#             account = getOrCreateAccount(uchet[3]),
#             category = getOrCreateCategory(uchet[4]),
#             comment = uchet[5],
#         )
#     return JsonResponseWithStatusOk(importedCount = len(importedData))


# Экспорт данных
@uu_login_required
def lk_exp_csv(request):

    # получяа модель, воврает строку (одну)
    def uchetToPlainText(u):

        # Тип опреации как строка
        typeStr = {
            my_uu.models.UType.RASHOD: u'Расход',
            my_uu.models.UType.DOHOD: u'Доход',
            my_uu.models.UType.PEREVOD: u'Перевод',
        }[u.utype.id]

        # форматируем и возвращаем
        return u"{oid};{dtm};{typ};{smm};руб;{acc};{cat};{com}\n".format(
            oid = u.id,
            dtm = u.date.strftime("%d.%m.%Y"),
            typ = typeStr,
            smm = u.sum,
            acc = u.account.name,
            cat = u.category.scf_name,
            com = u.comment,
        )

    # Операции для экспорта
    # Фильтр по дате используется из pvoytko.ru со страницы автоимпорта из Мой УУ чтобы не слишком долго делался импорт
    exp_operations = request.user.uchet_set.order_by('date').all()
    if 'ec_date_from' in request.GET:
        date_str = request.GET['ec_date_from']
        date_val = pvl_datetime_format.funcs.strToDate(date_str)
        exp_operations = exp_operations.filter(date__gte = date_val)

    # Проходим все операции
    res = u""
    for u in exp_operations:
        res += uchetToPlainText(u)

    plainTextContentType = "text/plain; charset=utf-8"
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
def ajax_lk_save_uchet(request):

    # Делаем проверку, если нужно оплатить, значит не даем сохранять запись.
    # По идее мы должны разрешать изменять, но тогда может возникнуть хак что юзер будет вносить записи
    # за старую дату а потом изменять за новую тем самым обойдет ограничение. Чтобы этого хака не было, да и
    # т.к. так проще реализовать, я запрещаю и редактирование и создание. Т.е. если у пользователя дохера записей
    # более 40, то он не сможет их даже редачить в бесплатном режиме.
    # if request.user.userprofile.errorOnSaveUchet():
    #    raise RuntimeError('Попытка сохранить/отредактировать запись в режиме когда эта возможность ограничена и для снятия огранчения нужно оплатить')
    # Закоментил код 04.08.2016, удаить через квартал.

    rowsForUpdateAndInsert = json.loads(request.POST['rows_json'])

    # Перебираем все полученные строки
    # Если в ней есть serverRecordId, значит эта строка есть уже в БД, ее надо update.
    # Если в полученных данны нет serverRecordId, значит эту строку надо insert
    for r in rowsForUpdateAndInsert:

        # хз иногда во входных данных передавалось свойство Undefined,
        # при редактировании строки, пример http://pvoytko.ru/jx/R2ev1Z2cNk
        # так и не понял откуда оно так что просто его удаляю
        # если этого не делать ниже будет ошибка
        if 'undefined' in r:
            del r['undefined']

        # На основе пришедших данных делаем стркоу для вставки в БД
        import copy
        rowDbData = copy.copy(r)

        # Шаг №1 - заменить названия счетов и категорий на их id в БД
        rowDbData['account'] = my_uu.models.Account.objects.get(name=r['account'], user=request.user)
        rowDbData['category'] = my_uu.models.Category.objects.get(scf_name=r['category'], user=request.user)
        rowDbData['utype'] = my_uu.models.UType.objects.get(name=r['utype'])
        rowDbData['date'] = datetime.datetime.strptime(r['date'], '%d.%m.%Y')
        rowDbData['user'] = request.user

        # С клиента приходят в формате с ",", меняем на "."
        rowDbData['sum'] = r['sum'].replace(',', '.')

        if r['lkud_date_rep']:
            rowDbData['myum_date_rep'] = datetime.datetime.strptime(r['lkud_date_rep'], '%d.%m.%Y')
        else:
            rowDbData['myum_date_rep'] = None
        del rowDbData['lkud_date_rep']

        # Преобразовываем время
        rowDbData['myum_time'] = datetime.datetime.strptime(r['lkud_time'], '%H:%M').time()
        del rowDbData['lkud_time']

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
def ajax_lk_delete_uchet(request):
    rowForDelete = json.loads(request.POST['rowForDelete'])
    rowId = rowForDelete['serverRowId']
    my_uu.models.Uchet.objects.get(id= rowId).delete()
    return JsonResponseWithStatusOk(accountBalanceList = _getAccountBalanceList(request))


class MyUUUIException(BaseException):
    pass


class DeleteAccountWithUchetRecordsException(MyUUUIException):
    def __init__(self, isAccount):
        texts = {
            True: u"Есть операции учета где используется этот счет. Удалить можно только такой счет, с которым не связано ни одной операции учета.",
            False: u"Есть операции учета где используется эта категория. Удалить можно только такую категорию, с которой не связано ни одной операции учета.",
        }
        super(DeleteAccountWithUchetRecordsException, self).__init__(
            texts[isAccount]
        )


class DeleteLastAccountException(MyUUUIException):
    def __init__(self, isAccount):
        texts = {
            True: u"Нельзя удалить последний счет. Должен оставаться хотя бы один счет.",
            False: u"Нельзя удалить последнюю категорию. Должна оставаться хотя бы одна категория.",
        }

        super(DeleteLastAccountException, self).__init__( texts[isAccount] )


def _lk_save_settings_ajax(request, userPropName, modelClass, editEventConstant, addEventConstant, setName, rowGetter):

    newAccountData = json.loads(request.body)

    # Создаем новый или изменяем существующий счет
    if 'id' in newAccountData:
        uuTrackEventDynamic(request.user, editEventConstant)
        a = getattr(request.user, userPropName).get(id = newAccountData['id'])
    else:
        uuTrackEventDynamic(request.user, addEventConstant)
        a = modelClass()
        a.user = request.user

    # Сохраняем все что пришло
    for k in newAccountData.keys():
        setattr(a, k, newAccountData[k])

    try:
        try:
            a.full_clean()
            a.save()

        # Если исключение в поле name, то такой вид исключений обрабатываем переделываем в наш вид
        # который мы умеем обрабатывать.
        except django.core.exceptions.ValidationError, e:

            # Тест что это u'Category с таким User и Name уже существует.'
            if len(e.message_dict.values()) == 1:
                m = e.message_dict.values()[0][0]
                wordSet = [modelClass.__name__, 'User', 'Name']
                if all([word in m for word in wordSet]):
                    raise AccountNameValidationError(u"{0} \"{1}\" уже существует.".format(setName, a.name))

            # Тест что это ошибка "Баланс не равен нулю"
            if len(e.message_dict.values()) == 1:
                m = e.message_dict.values()[0][0]
                if m == u'MUST_BE_ZERO':
                    raise AccountMustBeZeroError(u'Текущий остаток скрываемого счета должен быть равен нулю перед скрытием. Скорректируйте остаток счета одним из способов прежде чем скрывать его и повторите попытку скрыть счет.')

            raise

    # Если исключение при проверке поля Account.name, то показываем текст этой ошибки юзеру.
    except MyUUUIException, e:
        return JsonResponseWithStatusError(e)

    # Ошибок не возникло, все ОК.
    # Получаем данные для возврата в клиент.
    return JsonResponseWithStatusOk(data = rowGetter(a.id))


@uu_login_required
def _lk_delete_settings_ajax(request, isAccount, eventConstant):
    try:

        uuTrackEventDynamic(request.user, eventConstant)
        mgr = request.user.account_set if isAccount else request.user.category_set

        accountData = json.loads(request.body)
        a = mgr.get(id = accountData['id'])

        # Нельзя удалять если есть связанные записи учета
        if a.uchet_set.count() != 0:
            raise DeleteAccountWithUchetRecordsException(isAccount)

        # Нельзя удалять если это последний счет (категория).
        # Так как в этом случае заглючит таблица учета в которой ни одного счета ни одной категории.
        if mgr.count() == 1:
            raise DeleteLastAccountException(isAccount)

        a.delete()

    except MyUUUIException, e:
        return JsonResponseWithStatusError(e)

    # Ошибок не возникло, все ОК.
    return JsonResponseWithStatusOk()


@uu_login_required
def ajax_lk_save_account(request):

    def rowGetter(id):
        rowsA = my_uu.models.Account.objects.annotate(count = Count('uchet'), balance_current = Sum('uchet__sum')).order_by('position', 'id')
        r = rowsA.filter(id = id).values('id', 'name', 'count', 'position', 'visible', 'balance_start', 'balance_current')[0]
        if r['balance_current'] is None:
            r['balance_current'] = 0
        r['balance_current'] += r['balance_start']
        return r

    return _lk_save_settings_ajax(request, 'account_set', my_uu.models.Account, my_uu.models.EventLog.EVENT_EDT_ACC, my_uu.models.EventLog.EVENT_ADD_ACC, u'Счет', rowGetter)

def _lk_save_accounts_or_category_position(request, objMgr, eventConstant):
    uuTrackEventDynamic(request.user, eventConstant)
    accsIds = json.loads(request.body)
    accs = objMgr.filter(id__in = accsIds)
    for a in accs:
        a.position = accsIds.index(a.id) + 1
        a.save()
    return JsonResponseWithStatusOk()

@uu_login_required
def ajax_lk_delete_account(request):
    return _lk_delete_settings_ajax(request, True, my_uu.models.EventLog.EVENT_DEL_ACC)

@uu_login_required
def ajax_lk_save_accounts_order(request):
    return _lk_save_accounts_or_category_position(request, request.user.account_set, my_uu.models.EventLog.EVENT_REORDER_ACCOUNTS)


# Вызвыается при сохранении категории со страницы категорий
@uu_login_required
@annoying.decorators.ajax_request
def ajax_lk_save_category(request):

    js_model, = pvl_backend_ajax.funcs.extractAngularPostData(request, 'lsca_model')
    user = plogic.getAuthorizedUser(request)

    # класс джанго-формы для валидации формы
    class SaveCategoryForm(django.forms.Form):
        lkcm_dohod_rashod_type = django.forms.CharField(
            max_length=255,
        )
        scf_parent = django.forms.ModelChoiceField(
            required=False,
            queryset=my_uu.models.Category.objects.filter(user=user, scf_is_group=True),
        )
        scf_name = django.forms.CharField(
            max_length=255,
        )
        scf_visible = django.forms.CharField(
            max_length=255,
        )
        scf_comment = django.forms.CharField(
            required=False,
            max_length=255,
        )

    class SaveGroupForm(django.forms.Form):
        lkcm_dohod_rashod_type = django.forms.CharField(
            max_length=255,
        )
        scf_parent = django.forms.ModelChoiceField(
            required=False,
            queryset=my_uu.models.Category.objects.filter(user=user, scf_is_group=True),
        )
        scf_name = django.forms.CharField(
            max_length=255,
        )
        scf_visible = django.forms.CharField(
            max_length=255,
        )
        scf_comment = django.forms.CharField(
            required=False,
            max_length=255,
        )

    # Проверка того что пришло с сервера
    is_group = js_model['lkcm_cdc_type'] == 'CDC_TYPE_GROUP'
    if is_group:
        frm = SaveGroupForm(js_model)
    else:
        frm = SaveCategoryForm(js_model)

    # Пришло корректное
    if frm.is_valid():

        # Получаем объект из БД
        is_new = 'id' not in js_model
        if is_new:
            if is_group:
                obj = my_uu.models.Category()
                obj.user = user
                obj.scf_is_group = True
            else:
                obj = my_uu.models.Category()
                obj.user = user
                obj.scf_is_group = False
        else:
            obj = my_uu.models.Category.objects.get(id=js_model['id'], user=user)

        # Заполняем его данными и сохраняем
        for k in js_model.keys():

            # cleaned_data важно использвоать т.к. форма поле "родителя" преобразовывает к модели
            # если же использовать js_model там айдшиник а не модель
            # и тогда при сохранении категории (из фронта приходит ID и при попытке записать его в
            # scf_parent возникает ошибка.
            # т.к. на вход приходят поля которых и нет в форме - их пропускаем иначе ошибка что клоюч не найден.
            if k in frm.cleaned_data:
                setattr(obj, k, frm.cleaned_data[k])

        err = None
        frm_errors = pvl_backend_ajax.funcs.getDjangoFormErrorsAsDict(frm)
        try:

            obj.full_clean()
            obj.save()

        # Если исключение в поле name, то такой вид исключений обрабатываем переделываем в наш вид
        # который мы умеем обрабатывать.
        except django.core.exceptions.ValidationError, e:

            # Тест что это u'Category с таким User и Name уже существует.'
            if len(e.message_dict.values()) == 1:

                # пример текста в этом метсе - http://pvoytko.ru/jx/P2sgMOFGBA
                m = e.message_dict.values()[0][0]
                wordSet = [my_uu.models.Category.__name__, 'User', 'name']
                if all([word in m for word in wordSet]):
                    err = u"{0} \"{1}\" уже существует. Введите другое название (уникальное).".format(u'Категория', obj.scf_name)
                    return my_uu.plogic.getAjaxStatusOkErrorFormError(
                        frm_errors,
                        "lsca_django_form_errors",
                        "scf_name",
                        err
                    )

            # Тест что это ошибка "Баланс не равен нулю"
            elif len(e.message_dict.values()) == 1:
                m = e.message_dict.values()[0][0]
                if m == u'MUST_BE_ZERO':
                    err = u'Текущий остаток скрываемого счета должен быть равен нулю перед скрытием. Скорректируйте остаток счета одним из способов прежде чем скрывать его и повторите попытку скрыть счет.'
                    return my_uu.plogic.getAjaxStatusOkErrorFormError(
                        frm_errors,
                        "lsca_django_form_errors",
                        "scf_name",
                        err
                    )

            else:
                raise

        if err:
            return pvl_backend_ajax.funcs.ajaxStatusOkError(
                lsca_django_form_errors = frm_errors
            )

        # Возвращаем сохраненную категорию (группу)
        return pvl_backend_ajax.funcs.ajaxStatusOkSuccess(
            lscas_category = {}
        )

    # Пришло незаполнены поля
    else:
        return pvl_backend_ajax.funcs.ajaxStatusOkError(
            lsca_django_form_errors = pvl_backend_ajax.funcs.getDjangoFormErrorsAsDict(frm)
        )


# Удаляем категорию или группу
@uu_login_required
@annoying.decorators.ajax_request
def ajax_lk_delete_category(request):

    # класс джанго-формы для валидации формы
    class DeleteCategoryForm(django.forms.Form):
        pass
    frm = DeleteCategoryForm()
    frm_errors = pvl_backend_ajax.funcs.getDjangoFormErrorsAsDict(frm)


    mgr = request.user.category_set
    accountData = json.loads(request.body)['lsca_model']
    a = mgr.get(id = accountData['id'])


    # Нельзя удалять ккатегорию если у нее есть операции
    # Нельзя удалять ккатегорию если она последняя
    # Нельзя удалять группу если у нее есть дети
    # Во всех этих случаях выдаем ошибку уровня формы


    # Нельзя удалять если есть связанные записи учета
    if a.uchet_set.count() != 0:
        err = u"Есть операции учета где используется эта категория. Удалить можно только такую категорию, с которой не связано ни одной операции учета."
        return my_uu.plogic.getAjaxStatusOkErrorFormError(
            frm_errors,
            "aldc_django_form_errors",
            None,
            err
        )

    # Нельзя удалять если это последний счет (категория).
    # Так как в этом случае заглючит таблица учета в которой ни одного счета ни одной категории.
    if mgr.count() == 1:
        err = u"Нельзя удалить последнюю категорию. Должна оставаться хотя бы одна категория."
        return my_uu.plogic.getAjaxStatusOkErrorFormError(
            frm_errors,
            "aldc_django_form_errors",
            None,
            err
        )

    # Нельзя удалять группу если у нее есть дети
    if mgr.filter(scf_parent = a.id).exists():
        err = u"Нельзя удалять группу если у нее есть дочерние категории. Сперва удалите категории."
        return my_uu.plogic.getAjaxStatusOkErrorFormError(
            frm_errors,
            "aldc_django_form_errors",
            None,
            err
        )

    a.delete()

    # Возвращаем OK
    return pvl_backend_ajax.funcs.ajaxStatusOkSuccess()


@uu_login_required
def lk_save_categories_order_ajax(request):
    return _lk_save_accounts_or_category_position(request, request.user.category_set, my_uu.models.EventLog.EVENT_REORDER_CATEGORIES)


# Вызывается чтобы сохранить в БД статус сворачивания по категории
@uu_login_required
@annoying.decorators.ajax_request
def ajax_save_category_expand_status(request):

    cat_id, new_expanded_status = pvl_backend_ajax.funcs.extractAngularPostData(
        request, 'asces_category_id', 'asces_new_expanded_status',
    )
    category_model = my_uu.models.Category.objects.get(id = cat_id)
    category_model.scf_is_expanded = new_expanded_status
    category_model.save()

    return {}


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
    user = django.contrib.auth.models.User.objects.get(id = my_uu.utils.restoreId(int(oUserId)))
    uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_VISIT_FEEDBACK_REQUEST)
    return locals()


# Этот УРЛ для получения ОС отказников (уже отпрвка)
def feedback_request_ajax(request):

    requestBody = json.loads(request.body)

    # Юзера важно брать не из request, а из ID из УРЛа.
    # Так как вход на эту страницу должен быть без авторизации (чтоб из емейла работали ссылки).
    obfuscatedUserId = requestBody['oUserId']
    user = User.objects.get(id = my_uu.utils.restoreId(int(obfuscatedUserId)))

    uuTrackEventDynamic(user, my_uu.models.EventLog.EVENT_SEND_FEEDBACK_REQUEST)

    # Посылаем письмо
    my_uu.utils.sendFeedbackEmail(
        user.id,
        user.email,
        requestBody['text']
    )

    return JsonResponseBuilder().buildHttpJsonResponse()


# Страница оплаты
@uu_login_required
def lk_pay(request):
    return render(request, 'lk_pay.html', {
        'payModeDescription': request.user.userprofile.getPayModeDescription(),
        'payments': request.user.payment_set.all().filter(date_payment__isnull = False).order_by('date_payment')
    })


# Сохранить в БД инфо что платеж поступил на расчетный счет сервиса.
# invId - номер счета
# sumSeller - фактически поступившая сумма (за вычетом комиссии способа оплаты)
# eventConstant - какое событие записать
# zpTypeCode - код способа оплаты в Z-PAYMENT https://z-payment.com/api/get_codeoper.php
def confirmPayment(invId, sumSeller, zpTypeCode, eventConstant):

    # Находим запись платежа, созданную вначале процесса оплаты
    p = my_uu.models.Payment.objects.get(id = invId)

    # Сохраняем событие что платеж поступил
    uuTrackEventDynamic(p.user, eventConstant)

    # Сохраняем дату поступления платежа просто для истории
    p.date_payment = datetime.datetime.now()

    # Сохраняем дату с которой по которую платеж действует.
    # Дата с которой = след. день за днем по который уже оплачено или сегодня если активных оплат нет.
    # Дата по которую = дата с которой + кол-во дней - 1.
    pay_to = p.user.userprofile.getPaidByDate()
    today = datetime.date.today()
    p.date_from = today if (pay_to is None) else pay_to + datetime.timedelta(days=1)
    p.date_to = p.date_from + datetime.timedelta(days = p.days - 1)

    # Сумму, которую получает магазин на расчетный счет в приеме платежей
    p.sum_seller = sumSeller

    # Код способа оплаты
    p.zpayment_type_code = zpTypeCode

    # Запись в БД
    p.save()

    # Письмо мне что юзер оплатил
    import utils
    utils.sendEmailPaymentReceived(p)


# Уведомление об оплате, надо внести платеж юзера в БД, от РОБОКАССЫЫ
def robokassa_result_url(request):
    confirmPayment(request.POST['InvId'], my_uu.models.EventLog.EVENT_ROBOKASSA_PAY_NOTIFY)
    return HttpResponse('OK' + request.POST['InvId'])


# Уведомление об оплате, надо внести платеж юзера в БД, от Z-PAYMENT
def zpayment_result_url(request):
    confirmPayment(
        request.POST['LMI_PAYMENT_NO'],
        request.POST['ZP_SUMMA_SELLER'],
        request.POST['ZP_TYPE_PAY'],
        my_uu.models.EventLog.EVENT_ZPAYMENT_PAY_NOTIFY
    )
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
def do_order_ajax(request):

    periodCode = json.loads(request.body)['period']
    COST_AND_DAYS_DICT = {
        'days30': 30,
        'days60': 60,
        'days90': 90,
        'days120': 120,
    }

    # Цена которую должен заплатить юзер и количество дней юзанья которые он оплачивает
    cost = COST_AND_DAYS_DICT[periodCode]
    days = COST_AND_DAYS_DICT[periodCode]
    payment = my_uu.models.Payment(date_created = datetime.datetime.now(), sum = cost, user = request.user, days = days)
    payment.save()

    # Получаем УРЛ и пост-данные которые надо полать на этот УРЛ в платежный шлюз
    url = getPaymentGatewayInitPayUrl(request.user.email, cost, payment.id)
    return JsonResponseWithStatusOk(url = url)


# Это страница для тестирования
# как выглядит сообщение-запрос ОС у тех кто ушел юзая 1 день.
@uuAdmLoginRequired
@uuRenderWith('adm_test.html')
def adm_test(request):
    if request.POST and request.POST['command'] == 'request':
        return my_uu.utils.sendFeedbackRequest(my_uu.models.User.objects.get(email = 'pvoytko@gmail.com'))

# Это страница со списком выполненных платежей.
@uuAdmLoginRequired
@uuRenderWith('adm_pay.html')
def adm_pay(request):

    pays = my_uu.models.Payment.objects.filter(date_payment__isnull = False).order_by('date_payment')
    return locals()


# Это страница со списком юзеров которые оплатили.
@uuAdmLoginRequired
@uuRenderWith('adm_upay.html')
def adm_upay(request):

    upays = my_uu.models.Payment.objects.filter(date_payment__isnull = False).values(
        'user__id',
        'user__email'
    ).annotate(
        sum = Sum('sum'),
        cnt = Count('id'),
        date_pay_last = Max('date_payment'),
        date_max = Max('date_to')
    ).order_by('date_max')
    return locals()


# Страница оплаты
@uu_login_required
def ajax_lk_save_manual_answer(request):
    boolYes = json.loads(request.body)

    # Сохраняем ответ в БД
    ms = request.user.manualsteps
    dtn = datetime.datetime.now()
    if boolYes:
        ms.datetime_subscribe = dtn
    else:
        ms.datetime_cancel = dtn
    ms.save()

    return JsonResponseWithStatusOk()


# АПИ метод удаления записи
@csrf_exempt
@pvl_http.funcs.getParamsErrorsDecorator
def ajax_remove_uchet_record_api(request):

    import django.contrib.auth.hashers

    # Получаем данные из запроса
    inp_params = pvl_http.funcs.parseJsonRequestBody(request.body)
    rec_id = pvl_http.funcs.getParamValueFromJson(inp_params, 'arura_record_id')
    username = pvl_http.funcs.getParamValueFromJson(inp_params, 'arura_username')
    pswd_raw = pvl_http.funcs.getParamValueFromJson(inp_params, 'arura_password')

    # Проверяем пароль
    user_model = plogic.pmCheckUserAndPassword(username, pswd_raw)

    # Теперь удаляем запись
    uchet_model = my_uu.models.Uchet.objects.get(id = rec_id, user = user_model)
    uchet_model.delete()

    return django.http.HttpResponse("OK")


# АПИ метод добавления записи
@csrf_exempt
@pvl_http.funcs.getParamsErrorsDecorator
@annoying.decorators.ajax_request
def ajax_add_uchet_record_api(request):

    # Получаем данные из запроса
    inp_params = pvl_http.funcs.parseJsonRequestBody(request.body)
    username = pvl_http.funcs.getParamValueFromJson(inp_params, 'aaura_username')
    pswd_raw = pvl_http.funcs.getParamValueFromJson(inp_params, 'aaura_password')
    uchet_date = pvl_http.funcs.getParamValueFromJson(inp_params,     'aaura_date')
    uchet_time = pvl_http.funcs.getParamValueFromJson(inp_params,     'aaura_time')
    uchet_type = pvl_http.funcs.getParamValueFromJson(inp_params,     'aaura_type')
    uchet_summa = pvl_http.funcs.getParamValueFromJson(inp_params,    'aaura_summa')
    uchet_account = pvl_http.funcs.getParamValueFromJson(inp_params,  'aaura_account')
    uchet_category = pvl_http.funcs.getParamValueFromJson(inp_params, 'aaura_category')
    uchet_comment = pvl_http.funcs.getParamValueFromJson(inp_params,  'aaura_comment')

    # Проверка реквизитов
    user_model = plogic.pmCheckUserAndPassword(username, pswd_raw)

    # Был случай что ошибка что акк не найден, проверяем ее, чтобы было проще видеть.
    acc_model = annoying.functions.get_object_or_None(
        my_uu.models.Account,
        name = uchet_account,
        user = user_model,
    )
    cat_model = annoying.functions.get_object_or_None(
        my_uu.models.Category,
        scf_name = uchet_category,
        user = user_model,
    )
    if acc_model is None:
        return django.http.HttpResponseServerError(
            u'У юзера {} не найден счет с названием {}'.format(user_model, uchet_account)
        )
    if cat_model is None:
        return django.http.HttpResponseServerError(
            u'У юзера {} не найдена категория с названием {}'.format(user_model, uchet_category)
        )

    # Добавляем запись в БД
    u = my_uu.models.Uchet.objects.create(
        user = user_model,
        date = pvl_datetime_format.funcs.strToDate(uchet_date),
        myum_time = pvl_datetime_format.funcs.strToTime(uchet_time),
        utype = my_uu.models.UType.objects.get(name = uchet_type),
        sum = uchet_summa,
        account = acc_model,
        category = cat_model,
        comment = uchet_comment,
    )

    # Ответ
    return {
        "aaura_record_id": u.id,
    }


# АПИ метод чтения списка
@csrf_exempt
@pvl_http.funcs.getParamsErrorsDecorator
@annoying.decorators.ajax_request
def api_get_uchet_records(request):

    # Получаем данные из запроса
    inp_params = pvl_http.funcs.parseJsonRequestBody(request.body)
    username = pvl_http.funcs.getParamValueFromJson(inp_params, 'agur_username')
    pswd_raw = pvl_http.funcs.getParamValueFromJson(inp_params, 'agur_password')
    uchet_date1 = pvl_http.funcs.getParamValueFromJson(inp_params,     'agur_date_from')
    uchet_date2 = pvl_http.funcs.getParamValueFromJson(inp_params,     'agur_date_end')

    # Проверка реквизитов
    user_model = plogic.pmCheckUserAndPassword(username, pswd_raw)

    records = []
    for u in my_uu.models.Uchet.objects.filter(
        user = user_model,
        date__gte = pvl_datetime_format.funcs.strToDate(uchet_date1),
        date__lt = pvl_datetime_format.funcs.strToDate(uchet_date2),
    ).order_by('date'):
        records.append({
            'agur_id': u.id,
            'agur_date': pvl_datetime_format.funcs.dateToStr(u.date),
            'agur_type': u.utype.name,
            'agur_sum': decimal.Decimal(u.sum), # Несмотря на это сумма как строка почему-то взовращается
            'agur_category': u.category.scf_name,
            'agur_comment': u.comment,
        })

    # Ответ
    return {
        "agur_records": records,
    }



# АПИ метод изменнеия записи
@csrf_exempt
@pvl_http.funcs.getParamsErrorsDecorator
@annoying.decorators.ajax_request
def api_edit_uchet_records(request):

    # Получаем данные из запроса
    inp_params = pvl_http.funcs.parseJsonRequestBody(request.body)
    username = pvl_http.funcs.getParamValueFromJson(inp_params, 'aeur_username')
    pswd_raw = pvl_http.funcs.getParamValueFromJson(inp_params, 'aeur_password')
    uchet_id = pvl_http.funcs.getParamValueFromJson(inp_params,     'aeur_id')
    uchet_date = pvl_http.funcs.getParamValueFromJson(inp_params,     'aeur_date')
    uchet_time = pvl_http.funcs.getParamValueFromJson(inp_params,     'aeur_time')
    uchet_type = pvl_http.funcs.getParamValueFromJson(inp_params,     'aeur_type')
    uchet_summa = pvl_http.funcs.getParamValueFromJson(inp_params,    'aeur_summa')
    uchet_account = pvl_http.funcs.getParamValueFromJson(inp_params,  'aeur_account')
    uchet_category = pvl_http.funcs.getParamValueFromJson(inp_params, 'aeur_category')
    uchet_comment = pvl_http.funcs.getParamValueFromJson(inp_params,  'aeur_comment')

    # Проверка реквизитов
    user_model = plogic.pmCheckUserAndPassword(username, pswd_raw)

    # Изменяем запись в БД
    u = my_uu.models.Uchet.objects.get(
        id = uchet_id,
        user = user_model,
    )

    if uchet_date:
        u.date = pvl_datetime_format.funcs.strToDate(uchet_date)

    if uchet_time:
        u.myum_time = pvl_datetime_format.funcs.strToTime(uchet_time)

    if uchet_type:
        u.utype = my_uu.models.UType.objects.get(name = uchet_type)

    if uchet_summa:
        u.sum = uchet_summa

    if uchet_account:
        acc_model = annoying.functions.get_object_or_None(
            my_uu.models.Account,
            name = uchet_account,
            user = user_model,
        )
        if acc_model is None:
            return django.http.HttpResponseServerError(
                u'У юзера {} не найден счет с названием {}'.format(user_model, uchet_account)
            )
        u.account = acc_model

    if uchet_category:
        cat_model = annoying.functions.get_object_or_None(
            my_uu.models.Category,
            scf_name = uchet_category,
            user = user_model,
        )
        if cat_model is None:
            return django.http.HttpResponseServerError(
                u'У юзера {} не найдена категория с названием {}'.format(user_model, uchet_category)
            )
        u.category = cat_model

    if uchet_comment:
        u.comment = uchet_comment

    u.save()

    # Ответ
    return {
    }



# Экспорт данных Excel
@uu_login_required
def file_export_excel(request):

    user_model = plogic.getAuthorizedUser(request)
    file_path, file_datetime_str = plogic.getExportExcelFileForUserAndDateTime(user_model)
    if not os.path.exists(file_path):
        raise RuntimeError(u'Ошибка, не должен вызываться этот метод если файла нет.')

    fdtmstr2 = file_datetime_str.replace(':', '_').replace('.', '_').replace(' ', '__')
    file_name_for_user = u"myuu_operations_excel__{}.xlsx".format(fdtmstr2)

    with open(file_path, 'rb') as input_file:
        response = django.http.HttpResponse(
            input_file.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    response['Content-Disposition'] = u"attachment; filename={}".format(file_name_for_user)
    return response



# Общие переменные инфо для HTML шаблонов на всем сайте
# Ш-7551
def contextOuterPagesForSite(request):

    return {

        # Если авторизованы то True
        # то вместо формы входа в шапке - ссылка в ЛК
        'copfs_is_auth_user': plogic.isAuthorizedUser(request),

    }