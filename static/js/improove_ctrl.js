﻿function ImprooveCtrl($scope, $http){

    $scope.clearStatus = function(){
        $scope.isSendToServerNow = false;
        $scope.isSendToServerSuccess = false;
        $scope.isSendToServerError = false;
        $scope.improoveText = "";
        $scope.errorText = "";
    }

    $scope.clearStatus();

    $scope.sendToServer = function(){
        $scope.isSendToServerError = false;
        $scope.isSendToServerNow = true;
        console.log($scope.improoveText);
        httpObj = $http({
            method: 'POST',
            url: '/lk/improove_ajax/',
            data: {'improoveText': $scope.improoveText},
            cache: false,
            timeout: 15000
        });
        httpObj.success(function(data, status) {
            if (data.status != undefined && data.status == 'ok') {
                $scope.isSendToServerNow = false;
                $scope.isSendToServerSuccess = true;
            } else {
                $scope.errorText = 'Сервер вернул неуспешный ответ. ' +  JSON.stringify(data);
                $scope.isSendToServerNow = false;
                $scope.isSendToServerSuccess = false;
                $scope.isSendToServerError = true;
            }
        });
        httpObj.error(function(data, status) {
            $scope.errorText = 'Ошибка связи с сервером по HTTP. Код ошибки: ' + status;
            $scope.isSendToServerNow = false;
            $scope.isSendToServerSuccess = false;
            $scope.isSendToServerError = true;
        });
    }

}