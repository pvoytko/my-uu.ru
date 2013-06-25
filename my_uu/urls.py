# -*- coding: utf-8 -*-

from django.conf.urls import patterns, include, url

urlpatterns = patterns('',

    # Главная сервиса
    url(r'^$', 'my_uu.views.main'),

    # Регистрация логин и выход
    url(r'^register_user/$', 'my_uu.views.register_user_ajax'),
    url(r'^login_user/$', 'my_uu.views.login_user_ajax'),
    url(r'^logout_user/$', 'my_uu.views.logout_user' ),
    url(r'^begin/$', 'my_uu.views.begin'),

    # Личный кабинет
    url(r'^lk/$', 'my_uu.views.lk_uch'),
    url(r'^lk/ana/$', 'my_uu.views.lk_ana'),
    url(r'^lk/set/$', 'my_uu.views.lk_set'),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()