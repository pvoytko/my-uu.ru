# -*- coding: utf-8 -*-


# Это нужно чтобы подружить angular и django по теме csrf-protection. Взяо отсюда:
# https://github.com/whitehat2k9/kevinzhang.org/blob/master/posts/django-angularjs-and-csrf-xsrf-protection.md
class AngularCSRFRename(object):
    ANGULAR_HEADER_NAME = 'HTTP_X_XSRF_TOKEN'
    def process_request(self, request):
        if self.ANGULAR_HEADER_NAME in request.META:
            request.META['HTTP_X_CSRFTOKEN'] = request.META[self.ANGULAR_HEADER_NAME]
            del request.META[self.ANGULAR_HEADER_NAME]
        return None


