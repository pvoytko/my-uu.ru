# -*- coding: utf-8 -*-


import models
import django.contrib.auth.models
import my_uu.models
import pvl_datetime_format.funcs
import datetime
import os.path
import pvl_async.funcs
import io
import xlsxwriter
import datetime
import pvl_backend_ajax.funcs
from django.conf import settings


# получая на вход кверисет записей учета, и ID счета и категории, фильтрует кверисет
# по ним (если они не None) - испольузется для фильтрации записей учета на странице
# учета.
def filterUchetRecordsByPeriodAndAccountAndCategory(uchet_records_qs, period_id, account_id, category_id):
    if account_id:
        uchet_records_qs = uchet_records_qs.filter(account_id = account_id)
    if category_id:
        uchet_records_qs = uchet_records_qs.filter(category_id = category_id)
    if period_id:
        uchet_records_qs = filterUchetByViewPeriod(uchet_records_qs, period_id)
    return uchet_records_qs


# получает ID периода счета и категории из урл вида
# /lk/period/account/category/
# /lk/
# возвращает либо ID, либо None. А для периода всегда ID (last30, last3, 2014-02 и т.п.)
def getAccountIdAndCategoryIdFromUchetPageUrl(request_path):
    request_path
    parts = request_path.split('/')
    if len(parts) == 6:
        account_id = int(parts[3]) if (parts[3] and parts[3] != 'None') else None
        category_id = int(parts[4]) if (parts[4] and parts[4] != 'None') else None
        period_id = parts[2]
        return period_id, account_id, category_id
    if len(parts) == 3:
        return 'last30', None, None
    raise RuntimeError(u'Ошибка программирования. Должно быть или 3 части в пути или 6, раздеелнных "/" (слешем. '
                       u'Получено частей: {0}, путь: "{1}"'.format(len(parts), request_path))


# Фильтрует записи учета согласно выбранному фильтру дат
# Получает кверисет и код периода.
# Примеры кодов периода - см. convertPeriodCodeAndStartDateToPeriodId а так же, last3, last30
def filterUchetByViewPeriod(uchetRecords, period_id):

    import dateutil.relativedelta

    # Последние 3 дня, 30 дней
    if period_id in (models.UserProfile.VIEW_PERIOD_CODE_LAST3, models.UserProfile.VIEW_PERIOD_CODE_LAST30):
        lastIndex = 3 if period_id == models.UserProfile.VIEW_PERIOD_CODE_LAST3 else 30
        lastDates = list(uchetRecords.values_list('date', flat=True).distinct().order_by('-date')[0:lastIndex])

        # Тут важно возвращать не пустой список а пустой квери сет, т.к. к нему применяются ордер бай потом и пр.
        # а если пустой список будем возвращать то эксепшен там получим.
        if len(lastDates) == 0:
            return uchetRecords

        return uchetRecords.filter(date__gte = lastDates[-1])

    # День
    elif period_id.startswith('d'):
        date_parsed = datetime.datetime.strptime(period_id[1:], '%d.%m.%Y').date()
        return uchetRecords.filter(date = date_parsed)

    # Неделя
    elif period_id.startswith('w'):
        year, week = period_id[1:].split('-')
        year, week = int(year), int(week)

        # Сегодня 4 мая 2016
        # Это 18 неделя если использовать функцию getWeekNumberOfYear
        # Если использовать strptime то для 18-й недли возвращет дату 2016-05-02 00:00:00 т.е. 2 мая, то что надо

        # Сейчас задача из номера недели получить дату. Раньше это делалось как тут
        # http://stackoverflow.com/questions/17087314/get-date-from-week-number
        # но это не работало, что для недели 30 23–29 июл возвращалось дата 29 июл - 3 авг
        # Новый алгоритм работает так. Берем 4 число января. По моим предположениям
        # это число гарантированно выпадает на первую неделю (в отличие от 1 января, которое
        # может выпадать и на последнюю неделю прошлого года).
        # И от 4 числа - добавляем 7 * номер недели и затем берем понедельник - получим нужную неделю.
        w1dayN = datetime.datetime(year=year, month=1, day=4)
        wNdayN = w1dayN + datetime.timedelta(days=(week-1)*7)
        d1 = getFirstMomentOfWeek0(wNdayN)
        d2 = getFirstMomentOfNextWeek(wNdayN)
        return uchetRecords.filter(date__gte = d1, date__lt = d2)

    # Месяц
    elif period_id.startswith('m'):
        year, month = period_id[1:].split('-')
        year, month = int(year), int(month)
        d1 = datetime.date(year, month, 1)
        d2 = d1 + dateutil.relativedelta.relativedelta(months=1) - datetime.timedelta(days=1)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)

    # Квартал
    elif period_id.startswith('q'):
        year, quart = period_id[1:].split('-')
        year, quart = int(year), int(quart)
        d1 = datetime.date(year, (quart-1)*3 + 1, 1)
        d2 = datetime.date(year, (quart)*3 + 1, 1) - datetime.timedelta(days=1)
        return uchetRecords.filter(date__gte = d1, date__lte = d2)

    # Год
    elif period_id.startswith('y'):
        year_parsed = int(period_id[1:])
        year_cur_begin = datetime.date(year_parsed, 1, 1)
        year_next_begin = datetime.date(year_parsed+1, 1, 1)
        return uchetRecords.filter(
            date__gte = year_cur_begin,
            date__lt = year_next_begin,
        )

    raise RuntimeError(u'Ошибка. Неподдерживаемый ID периода "{id}"'.format(id = period_id))





# Возвращает все UchetRecords для этого юзера
# Используется для получения записей учета для отображения на станице учета.
def getUserUchetRecords(user):
    urecs = models.Uchet.objects.filter(user=user).order_by('date', '-utype', 'id')
    return urecs


# Получая дату, возвращает номер недели.
def getWeekNumberOfYear(date):
    return date.isocalendar()[1]

# Ш-7337
# Получая дату, возвращает начало недели.
def getFirstMomentOfWeek0(dt):
    return dt - datetime.timedelta(days=dt.weekday())

def getFirstMomentOfWeek1(dtm):
    return convertDateToDateTime(
        getFirstMomentOfWeek0(dtm.date())
    )

# Ш-7337
# Получая дату, возвращает начало следующей недели.
def getFirstMomentOfNextWeek(dtm):
    return getFirstMomentOfWeek0(dtm) + datetime.timedelta(days=7)


# получая на вход дату и код периода (quart, week, month, day) - на их основе вычисляет id периода)
# примеры
#     "Неделя 14 2016" (урл - w2016-14)
#     или
#     "24 апр Вс 2016" (d2016.12.01)
#     или
#     "Февраль 2016" (m2013-02)
#     или
#     "I - 2016" (q2013-1)
#     или
#     "2018" (y2018)
def convertPeriodCodeAndStartDateToPeriodId(period_code, start_date):

    import views

    if period_code == u'day':
        return start_date.strftime('d%d.%m.%Y')
    elif period_code == u'week':
        return "w{0}-{1}".format(start_date.strftime('%Y'), getWeekNumberOfYear(start_date))
    elif period_code == u'month':
        return "m{0}-{1:02}".format(start_date.year, start_date.month)
    elif period_code == u'quart':
        return "q{0}-{1}".format(start_date.year, views.getQuartNumber(start_date))
    elif period_code == u'app_year':
        return "y{0}".format(start_date.year)

    raise RuntimeError(u'Неизвестный код периода')


# возвращает true елси пользователь ранее ввел корректные логин и пароль и сейчас авторизован
def isAuthorizedUser(request):
    return request.user.is_authenticated()


# возвращает модель пользователя если он авторизвоан а если нет то кинет ошибку 500
def getAuthorizedUser(request):
    if not isAuthorizedUser(request):
        raise RuntimeError(u'Попытка обратится к объекту авторизованного ползователя, '
                           u'тогда как текущий пользователь не авторизован')
    return request.user


# Функция добавляет декоратор на проверку роли при открытии каждой страницы админки (добавить удалить редактировать ...)
# для модели. Если роли нет, вернет Forbidden HTTP ответ. Использование:
#     class MyModelAdmin(admin.ModelAdmin):
#
#     # Проверка перед открытием всех страниц что имеется роль админа
#     get_urls = getDjangoAdminUrlsWithAdminCheck()
def getDjangoAdminUrlsWithAdminCheck():

    def getUrlsWrapper(model_admin):

        from django.conf.urls import url

        def wrap(view):
            from functools import update_wrapper
            @loginRequiredHttp
            @roleRequiredHttp(models.UROLE_ADMIN)
            def wrapper(*args, **kwargs):
                return model_admin.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = model_admin.model._meta.app_label, model_admin.model._meta.model_name

        urlpatterns = [
            url(r'^$', wrap(model_admin.changelist_view), name='%s_%s_changelist' % info),
            url(r'^add/$', wrap(model_admin.add_view), name='%s_%s_add' % info),
            url(r'^(.+)/history/$', wrap(model_admin.history_view), name='%s_%s_history' % info),
            url(r'^(.+)/delete/$', wrap(model_admin.delete_view), name='%s_%s_delete' % info),
            url(r'^(.+)/$', wrap(model_admin.change_view), name='%s_%s_change' % info),
            ]
        return urlpatterns

    return getUrlsWrapper


# Декоратор на проверку что в сессии хранится ID авторизованного юзера
# Для использования во вью которые форируют HTML-страницы, т.к. возвращает HttpResponse
def loginRequiredHttp(f):
    def loginRequiredWrapperFunc(request, *args, **kwargs):
        if isAuthorizedUser(request):
            return f(request, *args, **kwargs)
        else:
            import django.conf
            from django.http import HttpResponseRedirect
        import urllib
        from django.core.urlresolvers import reverse
        redir_url = reverse('admin:login') + '?next=' + urllib.quote(request.path + request.META['QUERY_STRING'])
        return django.http.HttpResponseRedirect(redir_url)
    return loginRequiredWrapperFunc


# Декоратор на проверку что роль нужная, иначе возвращает 503 (для view страниц)
def roleRequiredHttp(*roles):
    def roleRequiredHttpDecor(f):
        def roleRequiredHttpWrapperFunc(request, *args, **kwargs):
            u = getAuthorizedUser(request)
            uRole = getUserRole(u)

            # Юзеру с ролью админ всегда разрешено.
            if uRole in roles or uRole == models.UROLE_ADMIN:
                return f(request, *args, **kwargs)
            else:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Просмотр не разрешен.")
        return roleRequiredHttpWrapperFunc
    return roleRequiredHttpDecor


# Аналогичен loginRequiredHttp только делает raise при отутствии,
# для использования в ajax-вьюхах
def loginRequiredAssert(f):
    import functools
    @functools.wraps(f)
    def loginRequiredWrapperFunc(request, **kwargs):
        if isAuthorizedUser(request):
            return f(request, **kwargs)
        else:
            raise RuntimeError(u"Требуется авторизация")
    return loginRequiredWrapperFunc


# возвращает логин авторизованного пользователя, а если не авторизован, кинет ошибку.
def getAuthorizedUsername(request):
    u = getAuthorizedUser(request)
    return getUserUsername(u)


# возвращает логин авторизованного пользователя, а если не авторизован, кинет ошибку.
def getUserUsername(user):
    return getattr(user, user.USERNAME_FIELD)


# возвращает роль авторизованного пользователя
def getUserRole(user):
    if getUserUsername(user) == 'pvoytko@gmail.com':
        return models.UROLE_ADMIN
    else:
        return models.UROLE_USER


# Получая на вход модель шаблона письма и адрес получателя, эта функция высылает письмо.
# disable_render=True - блокирет подстановку переменных, высылает плейхолденры.
# ИСпользуется в разделе тестовой отправки емейла.
def sendEmailByTemplate(kemailtemplate_model_id, to_address, context, disable_render=False):

    import django.template
    import django.core.mail
    import pvl_send_email.models

    # Рендерим шаблон, получаем HTML тело сообщения
    kemailtemplate_model = pvl_send_email.models.KEmailTemplate.objects.get(id=kemailtemplate_model_id)
    subj = kemailtemplate_model.ket_subject
    htmlContent = replaceUlrsWithLinks(kemailtemplate_model.ket_html)
    if not disable_render:
        htmlContent = django.template.Template(htmlContent).render(django.template.Context(context))

    # Отправляем HTML тело сообщения и текстовую версию тоже.
    # Тут отпрваляется две версии, т.к. иначе сервис http://www.mail-tester.com/web-zbUSCp
    # выдает минус 1 балл. скрин http://pvoytko.ru/jx/5GMrRyngzu
    # html версия добавляется последней, т.к. вэ том случае она предпочтительная, что
    # сказано в по этой ссылке http://stackoverflow.com/a/882770/1412586 скрин http://pvoytko.ru/jx/KmXz2OmyEf
    import html2text
    text_content = html2text.html2text(htmlContent)
    msg = django.core.mail.EmailMultiAlternatives(subj, text_content, 'support2@my-uu.ru', [to_address])
    msg.attach_alternative(htmlContent, "text/html")
    msg.send()


# получая текст, форматирует его как HTML (используется при отправке писчем на основе текстового шаблона)
def replaceUlrsWithLinks(text):

    # Замера урлов на ссылки
    # word-break:break-all; для того чтобы длиные ссылки
    # не расширяли страницу а обрезались посредине
    # скобки.
    # Для этого перебор всех урлов.
    # И если урл кончается символов знака препинания его выносим за ссылку.
    import re
    urls_pat = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$~_?\+-=\\\.&\[\]]*)([)]?)", re.MULTILINE|re.UNICODE|re.IGNORECASE)
    new_text = u""
    last_pos = 0
    for url_mo in re.finditer(urls_pat, text):
        url = url_mo.group()
        url_last = u""
        while url.endswith(')') or url.endswith('.') or url.endswith(':'):
            url_last += url[-1]
            url = url[0:-1]
        a_elem = u'<a style="word-break:break-all;" href="{0}" class="underline" target="_blank">{0}</a>{1}'.format(url, url_last)
        new_text += text[last_pos:url_mo.start()] + a_elem
        last_pos = url_mo.end()
    new_text += text[last_pos:]
    text = new_text

    # Вставляем br, переводы строки оставляем, т.к. на них ориентируется следующее рег. выражение.
    # \u2823 - это юникод-символ line separator http://www.fileformat.info/info/unicode/char/2028/index.htm
    # с какого-то момента Скайп стал их присылать (в сообщениях dJON клиента) например 6193:
    # http://pvoytko.ru/dj-admin/pvoytko/clientcontact/6193/?_changelist_filters=p%3D1
    # если их не заменять то строки сливаются.
    text = text.replace("\n", '<br />\n')
    text = text.replace(u"\u2028", u'<br />\n')

    # Заменяем пустрые строки. Например, текст может быть таким:
    # --
    # Пример списка<br />
    #      Пример итема<br />
    #      Пример итема<br />
    # --
    # Если такой текст вставить в DIV в HTML, то пробелы до итемов удалятся и он отобразится так:
    # --
    # Пример списка<br />
    # Пример итема<br />
    # Пример итема<br />
    # --
    # Чтобы сохранить пробелы - заменяем все пробелы в количстве 2 и более таким же кол-вом неразрывных пробелов.
    # А вначале строки заменяем один и более пробел неразрывными.
    # Не заменяем все пробелы т.к. пробелы между словами пусть остаются разрывными, чтобы нормально строки
    # отображались.
    text = re.sub('(\s{2,})', lambda s: '&nbsp;' * len(s.group(1)), text)
    text = re.sub('^(\s{1,})', lambda s: '&nbsp;' * len(s.group(1)), text)

    return text


# Проверяет юзера и пароль, возвращает модель юзера.
# Либо кидет исключение, если не верные.
def pmCheckUserAndPassword(usr, psw):
    user_model = django.contrib.auth.models.User.objects.get(username = usr)
    is_pass_correct = django.contrib.auth.hashers.check_password(psw, user_model.password)
    if not is_pass_correct:
        raise RuntimeError(u'Ошибка проверки пароля')
    return user_model


# Если одно из них None, вернет "--" иначе "4 500 в нед." для примера.
def getBudgetStr(budget_choice_code, budget_value):
    if budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_DAY:
        period = u'в день'
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_WEEK:
        period = u'в нед.'
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_MONTH:
        period = u'в мес.'
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_QUART:
        period = u'в кварт.'
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_YEAR:
        period = u'в год'
    else:
        raise RuntimeError(u'Ошибка в функции анализа расходов.')

    return my_uu.utils.formatMoneyValue(budget_value) + u' ' + period

# Если одно из них None, вернет "--" иначе "4 500 в год" т.е приводит к году
def getBudgetYearStr(budget_choice_code, budget_value):

    if budget_value is None:
        return u'--'

    if budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_DAY:
        budget_value = budget_value * 366
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_WEEK:
        budget_value = budget_value * 53
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_MONTH:
        budget_value = budget_value * 12
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_QUART:
        budget_value = budget_value * 4
    elif budget_choice_code == my_uu.models.LKCM_BUDGET_PERIOD_YEAR:
        budget_value = budget_value
    else:
        raise RuntimeError(u'Ошибка в функции анализа расходов.')

    return budget_value, my_uu.utils.formatMoneyValue(budget_value) + u' в год'


# Получая дату, возвращает начало месяца.
def getFirstMomentOfMonth0(dt):
    return dt.replace(day=1)


# Получая дату-время, возвращает начало месяца.
def getFirstMomentOfMonth1(dtm):
    return convertDateToDateTime(getFirstMomentOfMonth0(dtm.date()))


def convertDateToDateTime(sourcedate):
    return datetime.datetime.combine(sourcedate, datetime.time(0, 0))



# получая на вход структуру формата как для CharField choices и отображаемое значение (вторая колнка)
# возвращает значение из первой колнки (то что хранится в БД).
# если не найдено - кинет исключение.
# Ш-7275
def convertChoicesDisplayValueToDbValue(choices, display_value):
    for db_val, dis_val in choices:
        if display_value == dis_val:
            return db_val
    raise RuntimeError(u'Попытка преобразовать неподдерживаемое значвение "' + display_value + '"')


# Аналогично convertChoicesDisplayValueToDbValue, только в обратном направлении.
# Ш-7275
def convertChoicesDbValueToDisplayValue(choices, db_value):
    for db_val, dis_val in choices:
        if db_value == db_val:
            return dis_val
    raise RuntimeError(u'Попытка преобразовать неподдерживаемое значвение "' + db_value + '"')


# Дата-время изменения фалйа.
# источник - https://stackoverflow.com/a/237093/1412586
# Ш-7647
def getFileModificationDatetime(file_path):
    tmstamp = os.path.getmtime(file_path)
    return datetime.datetime.fromtimestamp(tmstamp)


def pvlWriteRowInExcel(worksheet_curr, row_data, row_num):
    """
    Функция для записи строки в файл Эксель
    :param worksheet_curr: книга в файле excel для записи данных
    :param row_data: данные для строки - список
    :param row_num: номер строки для записи
    """
    for col_num, value in enumerate(row_data, start=0):

        # Получаем значение из словаря
        val = value['pvr_val']
        if 'pvr_type' in value and value['pvr_type'] == 'PVR_TYPE_NUMBER':
            worksheet_curr.write_number(row_num, col_num, val)
        else:
            worksheet_curr.write(row_num, col_num, val)


def fleGetValueTrueOrMinuses(val, functor=unicode):
    if not val:
        return u'--'
    else:
        return functor(val)

def fleGetPvrValueNumberOrMinuses(val):
    return {
        'pvr_val': val,
        'pvr_type': 'PVR_TYPE_NUMBER',
    } if val is not None else {
        'pvr_val': u'--',
    }


# Типы асинхронных задач в проекте
AT_MYU_EXPORT_EXCEL = "AT_MYU_EXPORT_EXCEL"


@pvl_async.funcs.pvlThreadApplyAsync2(AT_MYU_EXPORT_EXCEL)
def asyncMakeExportExcel(async_task, user_model_id):

    pvl_async.funcs.pvlWriteAsyncTaskLog(async_task, u'Начало формирования...')

    # создание кники в памяти
    user_model = models.User.objects.get(id=user_model_id)
    output = io.BytesIO()
    workbook = xlsxwriter.workbook.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # Форматирование заголовков таблицы
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': 'silver',
    })
    header_format.set_text_wrap()
    worksheet.set_row(0, 30, header_format)

    # Запись в файл заголовков
    header = (
        {'pvr_val': u'ID операции' },
        {'pvr_val': u'Дата-время операции' },
        {'pvr_val': u'Тип операции' },
        {'pvr_val': u'Счет' },
        {'pvr_val': u'Сумма' },
        {'pvr_val': u'Категория' },
        {'pvr_val': u'Комментарий' },
    )
    pvlWriteRowInExcel(worksheet_curr=worksheet, row_data=header, row_num=0)

    # Ширина колонокю
    worksheet.set_column(0, 1, 10) # id
    worksheet.set_column(1, 3, 20) # дата-время тип
    worksheet.set_column(3, 4, 30) # счет
    worksheet.set_column(4, 5, 10) # сумма
    worksheet.set_column(5, 6, 30) # категория
    worksheet.set_column(6, 7, 60) # коммент

    # Перебор заказов и формирование
    orders_qs_all = models.Uchet.objects.filter(user = user_model).order_by('id')
    nrow = 1
    tcount = orders_qs_all.count()
    for z in orders_qs_all:

        created_dtm = datetime.datetime.combine(z.date, z.myum_time)
        row_data = [

            # 'ID опертации',
            fleGetPvrValueNumberOrMinuses(z.id),

            # 'Дата-время операции',
            {'pvr_val': pvl_datetime_format.funcs.dateTimeToStr(created_dtm) },

            # 'Тип операции',
            {'pvr_val': unicode(z.utype.name) },

            # 'Счет',
            {'pvr_val': unicode(z.account.name) },

            # 'Сумма'
            fleGetPvrValueNumberOrMinuses(z.sum),

            # 'Категория',
            {'pvr_val': unicode(z.category.scf_name) },

            # 'Комментарий',
            {'pvr_val': fleGetValueTrueOrMinuses(z.comment) },
        ]

        pvlWriteRowInExcel(worksheet_curr=worksheet, row_data=row_data, row_num=nrow)
        if divmod(nrow, 100)[1] == 0:
            pvl_async.funcs.pvlWriteAsyncTaskLog(
                async_task,
                u'Записано {} строк из {}'.format(nrow, tcount),
            )

        nrow += 1


    # Запись сформированных данных
    workbook.close()
    output.seek(0)

    # Запись в файл
    pvl_async.funcs.pvlWriteAsyncTaskLog(async_task, u'Запись файла...')
    fname = getExportExcelFileForUserPathOnly(user_model)
    with open(fname, u'wb') as f:
        f.write(output.read())

    pvl_async.funcs.pvlWriteAsyncTaskLog(async_task, u'Файл успешно сформирован и запиисан.')

# Имя файла в котором на диске хранится данные для экспорта по юзеру
def getExportExcelFileForUserPathOnly(user_model):
    fname = u'{}.xls'.format(user_model.id)
    res = os.path.join(settings.MEDIA_ROOT, 'lk_exp_files', fname)
    return res


# Имя файла в котором на диске хранится данные для экспорта по юзеру
def getExportExcelFileForUserAndDateTime(user_model):
    file_path = getExportExcelFileForUserPathOnly(user_model)
    file_dtm_str = None
    if os.path.exists(file_path):
        file_dtm_val = getFileModificationDatetime(file_path)
        file_dtm_str = pvl_datetime_format.funcs.dateTimeToStr(file_dtm_val)
    return file_path, file_dtm_str


# Упрощает возврат кода ошибки
def getAjaxStatusOkErrorFormError(form_errors, res_name, field_name, error_text):
    if field_name:
        form_errors['field_errors'][field_name] = [error_text]
    else:
        form_errors['non_field_errors'] = [error_text]

    return pvl_backend_ajax.funcs.ajaxStatusOkError(
        **{res_name: form_errors}
    )


# Используется на странице категорий и анализа
# Для корневой вернет 0 для следуюего уровня 1 и т.п.
def getCategoryIndentLevel(c):
    lev = 0
    cur_par = c
    while True:
        cur_par = cur_par.scf_parent
        if not cur_par:
            return lev
        lev += 1

        if lev >= 20:
            raise RuntimeError("Вложенность более чем 20 не поддерживается, наверное циклическая ошибка.")


# Возвращает список списков из 2 элементов: код месяца (YYYY-MM) и русскоязычное "январь 2014"
# Это для поля view_period_code
def getUchetMonthSet(user_model):
    months = user_model.uchet_set.dates('date', 'month')
    def verboseMonth(d):
        months = [
            u'январь', u'февраль', u'март', u'апрель', u'май', u'июнь',
            u'июль', u'август', u'сентябрь', u'октябрь', u'ноябрь', u'декабрь'
            ]
        return months[d.month-1] + " " + str(d.year)
    return [["m{0}-{1:02}".format(m.year, m.month), verboseMonth(m)] for m in months]

