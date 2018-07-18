projectModule = angular.module('myNgApp',[]);

// Для Angular меняем две фигурные скобки на скобку и бакс (чтоб с шаблонами джанги различаться)
angular.module('myNgApp').config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
});


// Ш-7226 Директива pv-tooltip-directive элемента с тултипом при наведении
angular.module('myNgApp').directive('pvTooltipDirective', function($sce) {
    return {
        restrict: "A",
        scope: {
            pvTooltipDirective: '='
        },
        link: function link($scope, element, attrs, controller, transcludeFn) {

            $scope.ptd_is_inited = false;

            //the $watch method also works because the '@' binding already does the interpolation
            //see: http://stackoverflow.com/a/12976630/582917 & http://stackoverflow.com/a/17224886/582917
            //this only works because it's in an isolate scope, therefore myDirective is part of the scope
            $scope.$watch('pvTooltipDirective', function(value){

                // Если передали пустую строку то удаление
                // источник - https://stackoverflow.com/a/13414592
                // Эта фича нужна что ссылка была неактивна и была подсказка
                // а когда стала активна то подсказка уже не нужна.
                if ($scope.ptd_is_inited){
                    element.tooltip('destroy');
                    $scope.ptd_is_inited = false;
                };

                if(value){

                    element.tooltip({
                        placement: "top",
                        title: value,
                        html: true
                    });
                    $(element).removeAttr('title');
                    $scope.ptd_is_inited = true;

                };
            });
        }
    }
});
