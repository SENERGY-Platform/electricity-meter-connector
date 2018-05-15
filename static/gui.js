"use strict";

let conf_modal;
let nat;
let dt;
let lld;
let rpkwh;
let astrt;
let tkwh;
let device_id;
let ws_console;

window.addEventListener("DOMContentLoaded", function (e) {
    conf_modal = document.getElementById('modal');
    nat = document.getElementById("nat");
    dt = document.getElementById("dt");
    lld = document.getElementById("lld");
    rpkwh = document.getElementById("rpkwh");
    astrt = document.getElementById("astrt");
    tkwh = document.getElementById("tkwh");
    ws_console = document.getElementById('console');
    let content = document.getElementsByClassName('content')[0];
    let blocker = document.getElementsByClassName('blocker')[0];
    let subnav = document.getElementsByClassName('sub-navigation')[0];
    let subnav_btns = subnav.getElementsByClassName('btn');
    let checkbox = subnav.getElementsByClassName('container')[0];
    if (device_id) {
        getConf(device_id);
        openWS();
    } else {
        blocker.style.display = "block";
        content.style.background = "#f5f5f5";
        for (let btn of subnav_btns) {
            btn.style.backgroundColor = "#f5f5f5";
            btn.style.color = "#d0d0d0";
            btn.style.boxShadow = "2px 2px 5px 0 rgba(0,0,0,0.15)";
        }
        checkbox.style.backgroundColor = "#f5f5f5";
        checkbox.style.color = "#d0d0d0";
        checkbox.style.boxShadow = "2px 2px 5px 0 rgba(0,0,0,0.15)";
        ws_console.style.borderColor = "#c2c2c2";
    }
    window.addEventListener("click", function (e) {
        if (e.target === conf_modal) {
            toggleConfModal();
        }
    });
});

function openWS() {
   let ws = new WebSocket("ws://" + window.location.hostname + ":5678/");
   ws.addEventListener('message', function (event) {
       let text = document.createTextNode(event.data);
       let br = document.createElement('br');
       ws_console.appendChild(text);
       ws_console.appendChild(br);
       ws_console.scrollTop = ws_console.scrollHeight
   });
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
        console.log(e);
    });
    if (result !== 'timeout' && result !== undefined) {
        let conf = JSON.parse(result);
        nat.value = conf.nat;
        dt.value = conf.dt;
        lld.value = conf.lld;
        rpkwh.value = conf.rpkwh;
        tkwh.value = conf.tkwh;
        if (conf.strt === 0){
            astrt.checked = false;
        } else if (conf.strt === 1) {
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
