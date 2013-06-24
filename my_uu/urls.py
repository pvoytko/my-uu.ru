from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'my_uu.views.main'),
    url(r'^register_user/$', 'my_uu.views.register_user_ajax'),
    url(r'^login_user/$', 'my_uu.views.login_user_ajax'),
    url(r'^logout_user/$', 'my_uu.views.logout_user' ),
    url(r'^lk/$', 'my_uu.views.lk_main'),
    url(r'^begin/$', 'my_uu.views.begin'),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()