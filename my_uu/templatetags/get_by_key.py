# -*- coding: utf-8 -*-


from django.template.defaulttags import register

# См. тут http://stackoverflow.com/questions/13264511/typeerror-unhashable-type-dict
# Используется при построении pivotTable (convertTableDataToPivotTable функция)
def getHashable(rowValue):
    if isinstance(rowValue, dict):
        return frozenset(rowValue.values())
    else:
        return rowValue

@register.filter
def pivot_get_by_key(dictionary, key):
    return dictionary.get(getHashable(key))

@register.filter
def get_by_key(dictionary, key):
    return dictionary.get(key)
