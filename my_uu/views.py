# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
import json
import django.db.utils


# Это нужно чтобы подружить angular и django по теме csrf-protection. Взяо отсюда:
# https://github.com/whitehat2k9/kevinzhang.org/blob/master/posts/django-angularjs-and-csrf-xsrf-protection.md
class AngularCSRFRename(object):
    ANGULAR_HEADER_NAME = 'HTTP_X_XSRF_TOKEN'
    def process_request(self, request):
        if self.ANGULAR_HEADER_NAME in request.META:
            request.META['HTTP_X_CSRFTOKEN'] = request.META[self.ANGULAR_HEADER_NAME]
            del request.META[self.ANGULAR_HEADER_NAME]
        return None


# Главная страница.
# Вызывает шаблон главной страницы.
def main(request):
    if request.method == 'POST' and 'auth_button' in request.POST:
        # return HttpResponse("Auth check")
        pass

    af = AuthenticationForm(data=request.POST)
    return render(request, 'main.html', {'auth_form': af} )


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
    return django.contrib.auth.views.logout(request, next_page = '/static/main_.html')


# Главная страница личного кабиета
@login_required(login_url='/static/main_.html')
def lk(request):
    return render(request, 'lk.html', {'request': request} )
