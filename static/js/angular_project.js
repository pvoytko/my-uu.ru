projectModule = angular.module('project',[]);

// Для Angular меняем две фигурные скобки на скобку и бакс (чтоб с шаблонами джанги различаться)
projectModule.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
});
