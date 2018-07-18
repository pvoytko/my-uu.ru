angular.module('myNgApp').directive('uuBalance', function(){
    return {
        restrict: 'E',
        template:
            '<div style="margin-bottom: 25px;" class="clearfix">' +
                '<div style="font-weight: bold; margin: 3px 0; color: rgb(39, 100, 133);">' +
                    'Денег на счетах, для сверки <div style="float: right;">Всего: {$ getTotalBalance(accountList) $}</div>' +
                '</div>' +
                '<div class="balance__account_block" ng-repeat="a in accountList">' +
                    '<div class="balance__cell balance__account_name"><div>{$ a.name $}</div></div>' +
                    '<div class="balance__cell balance__account_sum"><div>{$ formatBalance(a.balance) $}</div></div>' +
                '</div>' +
            '</div>',
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