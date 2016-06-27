# -*- coding: utf-8 -*-
import os

virtual_env = '/var/www/pvoy_myuu_venv'
activate_this = os.path.join(virtual_env, 'bin/activate_this.py')
with open(activate_this) as f:
    code = compile(f.read(), activate_this, 'exec')
    exec(code, dict(__file__=activate_this))


# Этот файл используется для запуска uwsgi для части сайта написанной на джанго znakdj
os.environ['DJANGO_SETTINGS_MODULE'] = 'my_uu.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
