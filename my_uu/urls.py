from django.conf.urls import patterns, include, url
from django.conf import settings

urlpatterns = patterns('',
    url(r'^$', 'my_uu.views.main'),
    url(r'^register_user/$', 'my_uu.views.register_user_ajax'),
    url(r'^login_user/$', 'my_uu.views.login_user_ajax'),
    url(r'^logout_user/$', 'my_uu.views.logout_user' ),
    url(r'^lk/$', 'my_uu.views.lk'),
)
