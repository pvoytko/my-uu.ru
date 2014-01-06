// Если куки uu_ref нет, то создаем ее и сохраняем в нее HTTP_REFERER
// Который сохраняется в БД при регистрации посетителя.
$(document).ready(function() {
    if($.cookie('uu_ref') === undefined) {
        ref = document.referrer;
        $.cookie('uu_ref', ref, { expires: 365 } );
    }
});
