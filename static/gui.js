"use strict";

function httpPost(uri) {
    let xhttp = new XMLHttpRequest();
    xhttp.open("POST", uri, true);
    xhttp.send();
}


function httpPostConf(uri, nat, dt, lld, rpkwh, tkwh) {
    let xhttp = new XMLHttpRequest();
    xhttp.open("POST", uri, true);
    xhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xhttp.send("nat=" + nat + "&dt=" + dt + "&lld=" + lld + "&rpkwh=" + rpkwh + "&tkwh=" + tkwh);
}


function httpGetConf(uri) {
    let nat = document.getElementById("nat");
    let dt = document.getElementById("dt");
    let lld = document.getElementById("lld");
    let rpkwh = document.getElementById("rpkwh");
    let astrt = document.getElementById("astrt");
    let tkwh = document.getElementById("tkwh");
    let xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange=function() {
        if (this.readyState == 4 && this.status == 200) {
            let conf = JSON.parse(this.responseText);
            nat.value = conf.nat;
            dt.value = conf.dt;
            lld.value = conf.lld;
            rpkwh.value = conf.rpkwh;
            tkwh.value = conf.tkwh;
            if (conf.strt == 0){
                astrt.checked = false;
            } else if (conf.strt == 1) {
                astrt.checked = true;
            }
        }
    };
    xhttp.open("GET", uri, true);
    xhttp.send();
}


function toggleAstrt(box) {
    if (box.checked == true) {
        httpPost('{{ d_id }}/eas');
    } else if (box.checked == false) {
        httpPost('{{ d_id }}/das');
    }
    httpGetConf('{{ d_id }}/conf');
}


function openWS() {
   let ws = new WebSocket("ws://" + window.location.hostname + ":5678/");
    ws.onmessage = function (event) {
        let content = document.createTextNode(event.data);
        document.getElementById('content').innerHTML += event.data + '<br>';
        document.getElementById('content').scrollTop = document.getElementById('content').scrollHeight
    };
    window.addEventListener('unload', function (event) { ws.close(1000); });
}

