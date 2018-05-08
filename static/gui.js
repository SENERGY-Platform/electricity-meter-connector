"use strict";

let conf_modal;
let nat;
let dt;
let lld;
let rpkwh;
let astrt;
let tkwh;

window.addEventListener("DOMContentLoaded", function (e) {
    conf_modal = document.getElementById('modal');
    nat = document.getElementById("nat");
    dt = document.getElementById("dt");
    lld = document.getElementById("lld");
    rpkwh = document.getElementById("rpkwh");
    astrt = document.getElementById("astrt");
    tkwh = document.getElementById("tkwh");
});


function httpPost(uri, header, body) {
    if (uri && header && body) {
        let request = new XMLHttpRequest();
        request.open("POST", uri);
        request.setRequestHeader(header[0], header[1]);
        request.timeout = 5000;
        request.send(body);
    }
}


function httpGet(uri, header) {
    if (uri) {
        return new Promise(function (resolve, reject) {
            let request = new XMLHttpRequest();
            request.open("GET", uri);
            if (header) {
                request.setRequestHeader(header);
            }
            request.timeout = 5000;
            request.onreadystatechange = function () {
                if (request.readyState === 4) {
                    if (request.status === 200) {
                        resolve(request.response);
                    } else {
                        reject(request.status);
                    }
                }
            };
            request.ontimeout = function () {
                reject('timeout');
            };
            request.send();
        })
    }
}


function toggleAstrt(box) {
    if (box.checked === true) {
        //httpPost('{{ d_id }}/eas');
    } else if (box.checked === false) {
        //httpPost('{{ d_id }}/das');
    }
}

async function toggleConfModal(uri) {
    if (conf_modal.style.display === "none" || conf_modal.style.display === "") {
        let result = await httpGet(uri).catch(function (e) {
            console.log(e)
        });
        if (result !== 'timeout' && result !== undefined) {
            let conf = JSON.parse(result);
            nat.value = conf.nat;
            dt.value = conf.dt;
            lld.value = conf.lld;
            rpkwh.value = conf.rpkwh;
            tkwh.value = conf.tkwh;
            conf_modal.style.display = "block";
        }
    } else {
        conf_modal.style.display = "none";
    }
}

function submitConf(device) {
    let data = JSON.stringify({
        nat: nat.value,
        dt: dt.value,
        lld: lld.value,
        rpkwh: rpkwh.value,
        tkwh: tkwh.value
    });
    console.log(data);
    httpPost(device + "/conf", ["Content-type", "application/json"], data);
    toggleConfModal();
}


/*
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


function openWS() {
   let ws = new WebSocket("ws://" + window.location.hostname + ":5678/");
    ws.onmessage = function (event) {
        let content = document.createTextNode(event.data);
        document.getElementById('content').innerHTML += event.data + '<br>';
        document.getElementById('content').scrollTop = document.getElementById('content').scrollHeight
    };
    window.addEventListener('unload', function (event) { ws.close(1000); });
}
*/
