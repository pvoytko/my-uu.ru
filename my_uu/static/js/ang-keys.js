angular.module('myNgApp').directive('ngEnter', function () {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if(event.which === 13) {
                scope.$apply(function (){
                    scope.$eval(attrs.ngEnter);
                });
                event.preventDefault();
            }
        });
    };
});


// Директива задает что делать при клике на инсерт
angular.module('myNgApp').directive('ngDocIns', function () {
    return function (scope, element, attrs) {
        $(document).bind("keydown keypress", function (event) {

            // Только сравнения по which недостаточно.
            // Если нажать Ins, то which будет 45 и charCode 0
            // Если нажать "-", то which будет 45 и charCode 45
            if((event.which === 45) && (event.charCode === 0)) {
                scope.$apply(function (){
                    scope.$eval(attrs.ngDocIns);
                });
                event.preventDefault();
            }
        });
    };
});
