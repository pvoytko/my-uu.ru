angular.module('myNgApp').directive('uuBalance', function(){
    return {
        restrict: 'E',
        templateUrl: 'uu_balance_directive_template_id',
        replace: true,
        scope: {
            accountList: '=accountList'
        },
        controller: function($scope){
            $scope.formatBalance = function(v) {
                return window.uuFormatCurrency(v);
            };
            $scope.getTotalBalance = function(accountList) {
                tot = 0.00;
                for(var i=0; i<accountList.length; ++i){
                    tot += accountList[i].balance;
                }
                return window.uuFormatCurrency(tot);
            };
        }
    }
});