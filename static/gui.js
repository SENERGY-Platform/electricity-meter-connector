"use strict";

let conf_modal;
let settings_modal;
let nat;
let dt;
let ndt;
let lld;
let rpkwh;
let astrt;
let tkwh;
let device_id;
let name;
let ws_console;
let title;

window.addEventListener("DOMContentLoaded", function (e) {
    settings_modal = document.getElementById('modal');
    conf_modal = document.getElementsByClassName('modal-content2')[0];
    nat = document.getElementById("nat");
    dt = document.getElementById("dt");
    ndt = document.getElementById("ndt");
    lld = document.getElementById("lld");
    rpkwh = document.getElementById("rpkwh");
    astrt = document.getElementById("astrt");
    tkwh = document.getElementById("tkwh");
    name = document.getElementById("name");
    title = document.getElementById("title");
    ws_console = document.getElementById('console');
    let content = document.getElementsByClassName('content')[0];
    let blocker = document.getElementsByClassName('blocker')[0];
    let subnav = document.getElementsByClassName('sub-navigation')[0];
    let subnav_btns = subnav.getElementsByClassName('btn');
    let checkbox = subnav.getElementsByClassName('container')[0];
    if (device_id) {
        getConf(device_id);
        getSettings(device_id);
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
        if (e.target === settings_modal) {
            toggleSettingsModal();
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
    getSettings(device_id);
}

async function getConf(device) {
    let result = await httpGet(device + "/conf").catch(function (e) {
        console.log(e);
    });
    if (result !== 'timeout' && result !== undefined) {
        let conf = JSON.parse(result);
        nat.value = conf.nat;
        dt.value = conf.dt;
        ndt.value = conf.ndt;
        lld.value = conf.lld;
        rpkwh.value = conf.rpkwh;
        return true
    }
    return false
}

async function getSettings(device) {
    let result = await httpGet(device + "/sett").catch(function (e) {
        console.log(e);
    });
    if (result !== 'timeout' && result !== undefined) {
        let conf = JSON.parse(result);
        tkwh.value = conf.tkwh;
        name.value = conf.name;
        title.innerHTML = conf.name;
        if (conf.strt === 0){
            astrt.checked = false;
        } else if (conf.strt === 1) {
            astrt.checked = true;
        }
        return true
    }
    return false
}

function toggleSettingsModal() {
    if (settings_modal.style.display === "none" || settings_modal.style.display === "") {
        if (getSettings(device_id)) {
            settings_modal.style.display = "block";
        }
    } else {
        settings_modal.style.display = "none";
    }
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
        ndt: ndt.value,
        lld: lld.value,
        rpkwh: rpkwh.value
    });
    httpPost(device + "/conf", ["Content-type", "application/json"], data);
    toggleConfModal();
}

function submitSettings(device=device_id) {
    //let test = nat.checkValidity() && dt.checkValidity() && lld.checkValidity() && rpkwh.checkValidity() && tkwh.checkValidity();
    //console.log(test);
    let data = JSON.stringify({
        tkwh: tkwh.value,
        name: name.value
    });
    httpPost(device + "/sett", ["Content-type", "application/json"], data);
    toggleSettingsModal();
    title.innerHTML = name.value + ` (${device_id})`;
}