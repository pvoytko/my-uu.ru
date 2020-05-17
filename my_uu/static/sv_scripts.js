/* Ш-7544 Скрипты сайта */

// Получая на вход число, возвращает число разделенное проблелом по разрядам.
// 100 000
// 10 000 000
// Источник https://stackoverflow.com/a/41617096/1412586
// Ш-7623
function pvlNumberWithGroups(x) {
    x = String(x).toString();
    var afterPoint = '';
    if (x.indexOf('.') > 0)
        afterPoint = x.substring(x.indexOf('.'), x.length);
    x = Math.floor(x);
    x = x.toString();
    var lastThree = x.substring(x.length-3);
    var otherNumbers = x.substring(0, x.length-3);
    if (otherNumbers != '')
        lastThree = ' ' + lastThree;
    return otherNumbers.replace(/\B(?=(\d{3})+(?!\d))/g, " ") + lastThree + afterPoint;
}

// Как pvlNumberWithGroups (см. комент к ней), только еще доавляет рубли.
function pvlNumberWithRoubles(val){
    return pvlNumberWithGroups(val) + ' руб.'
}

// Ш-7623 преобразовать float к строковому
// 3.000 -> 3
// 3.100 -> 3.1
// 3.1234 -> 3.123
// Для отображения в блоке +- кол-во возле товаров-подтоваров и в корзине.
function formatKolvo(float_val){
    var val_str = float_val.toFixed(3);
    while (val_str[val_str.length-1] == '0'){
        val_str = val_str.substr(0, val_str.length-1);
    }
    if (val_str[val_str.length-1] == '.'){
        val_str = val_str.substr(0, val_str.length-1);
    }
    return val_str;
}