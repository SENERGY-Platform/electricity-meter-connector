"use strict";

let conf_modal;
let nat;
let dt;
let lld;
let rpkwh;
let astrt;
let tkwh;
let device_id;

window.addEventListener("DOMContentLoaded", function (e) {
    conf_modal = document.getElementById('modal');
    nat = document.getElementById("nat");
    dt = document.getElementById("dt");
    lld = document.getElementById("lld");
    rpkwh = document.getElementById("rpkwh");
    astrt = document.getElementById("astrt");
    tkwh = document.getElementById("tkwh");
    if (device_id) {
        getConf(device_id);
        openWS();
    }
});

function openWS() {
   let ws = new WebSocket("ws://" + window.location.hostname + ":5678/");
    ws.onmessage = function (event) {
        document.getElementById('console').innerHTML += event.data + '<br>';
        document.getElementById('console').scrollTop = document.getElementById('console').scrollHeight
    };
    window.addEventListener('unload', function (event) { ws.close(1000); });
}

function setDevice(device) {
    device_id = device;
}

function httpPost(uri, header, body) {
    if (uri) {
        let request = new XMLHttpRequest();
        request.open("POST", uri);
        if (header) {
           request.setRequestHeader(header[0], header[1]);
        }
        request.timeout = 5000;
        if (body) {
            request.send(body);
        } else {
            request.send();
        }

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
        httpPost(device_id + "/eas");
    } else if (box.checked === false) {
        httpPost(device_id + "/das");
    }
    getConf(device_id);
}

async function getConf(device) {
    let result = await httpGet(device + "/conf").catch(function (e) {
        console.log(e)
    });
    if (result !== 'timeout' && result !== undefined) {
        let conf = JSON.parse(result);
        nat.value = conf.nat;
        dt.value = conf.dt;
        lld.value = conf.lld;
        rpkwh.value = conf.rpkwh;
        tkwh.value = conf.tkwh;
        if (conf.strt === "0"){
            astrt.checked = false;
        } else if (conf.strt === "1") {
            astrt.checked = true;
        }
        return true
    }
    return false
}

function toggleConfModal() {
    if (conf_modal.style.display === "none" || conf_modal.style.display === "") {
        if (getConf(device_id)) {
            conf_modal.style.display = "block";
        }
    } else {
        conf_modal.style.display = "none";
    }
}

function submitConf(device=device_id) {
    //let test = nat.checkValidity() && dt.checkValidity() && lld.checkValidity() && rpkwh.checkValidity() && tkwh.checkValidity();
    //console.log(test);
    let data = JSON.stringify({
        nat: nat.value,
        dt: dt.value,
        lld: lld.value,
        rpkwh: rpkwh.value,
        tkwh: tkwh.value
    });
    httpPost(device + "/conf", ["Content-type", "application/json"], data);
    toggleConfModal();
}
