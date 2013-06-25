# -*- coding: utf-8 -*-
from django.core.mail.message import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
import json
import django.db.utils


# Главная страница.
# Вызывает шаблон главной страницы.
def main(request):

    # Если юзер уже прошел аутентификацию посылаем его в ЛК
    if request.user.id is not None:
        return HttpResponseRedirect(reverse('my_uu.views.lk_uch'))

    if request.method == 'POST' and 'auth_button' in request.POST:
        # return HttpResponse("Auth check")
        pass

    af = AuthenticationForm(data=request.POST)
    return render(request, 'main.html', {'auth_form': af} )


# Отправка письма
# Код взят из https://docs.djangoproject.com/en/dev/topics/email/
def sendHtmlEmailFromSupport(toEmail, subj, emailTemplateName, emailTemplateContextDict):

    # Рендерим шаблон, получаем HTML тело сообщения
    from django.template.loader import get_template
    from django.template import Context
    htmly = get_template(emailTemplateName)
    c = Context(emailTemplateContextDict)
    htmlContent = htmly.render(c)

    # Отправляем HTML тело сообщения (BCC=pvoytko@gmail.com)
    msg = EmailMessage(subj, htmlContent, "support@my-uu.ru", [toEmail], ['pvoytko@gmail.com'])
    msg.content_subtype = "html"
    msg.send()


# Отправляет Email что регистрация завершена.
def sendEmailRegistrationPerformed(toEmail, userEmail, userPassword):
    sendHtmlEmailFromSupport(
        toEmail,
        u'[my-uu.ru] Регистрация в сервисе Мой Удобный Учет',
        'email_registration_performed.html',
        {
            'userEmail': userEmail,
            'userPassword': userPassword
        }
    )


# Регистрация юзера по переданным email и паролю.
# Вернет body содержащий:
#     ok - зареген успешно
#     exists - уже существует
def register_user_ajax(request):
    data = json.loads(request.body)

    # Создаем юзера. Если эксепшен так как уже существует, то возвращаем код.
    try:
        u = User.objects.create_user(data['email'], data['email'], data['password'])
        u.save()
    except django.db.utils.IntegrityError as e:
        if 'auth_user_username_key' in str(e):
            return HttpResponse('register_exists')
        raise

    # Регистрация прошла успешно - высылаем email
    sendEmailRegistrationPerformed(data['email'], data['email'], data['password'])

    # И теперь тут же логиним
    user = _authenticateByEmailAndPassword(**data)
    login(request, user)

    return HttpResponse('ok')


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
    user = _authenticateByEmailAndPassword(**data)
    if user is not None:
        login(request, user)
        return HttpResponse('ok')
    else:
        return HttpResponse('auth_email_password_incorrect')
    
    
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

# Главная страница личного кабиета
@uu_login_required
def lk_uch(request):
    return render(request, 'lk_uch.html', {'request': request} )


# Главная страница личного кабиета
@uu_login_required
def lk_set(request):
    return render(request, 'lk_set.html', {'request': request} )


# Главная страница личного кабиета
@uu_login_required
def lk_ana(request):
    return render(request, 'lk_ana.html', {'request': request} )
