"use strict";

let settings_modal;
let conf_modal;
let mode_a_conf;
let mode_i_conf;
let mode_toggle;
let lb;
let rb;
let nat;
let lld;
let dt;
let ndt;
let rpkwh;
let astrt;
let tkwh;
let device_id;
let device_mode;
let name;
let ws_console;
let title;

async function loadInitalData(device_id) {
    let result = await httpGet(device_id + "/sett").catch(function (e) {
        return false;
    });
    if (result) {
        setSettings(result);
    }
    let result_2 = await httpGet(device_id + "/conf").catch(function (e) {
        return false;
    });
    if (result_2) {
        setConf(result_2);
    }
}

window.addEventListener("DOMContentLoaded", function (e) {
    settings_modal = document.getElementById('settings_modal');
    conf_modal = document.getElementById('conf_modal');
    mode_a_conf = document.getElementById("mode_a");
    mode_i_conf = document.getElementById("mode_i");
    mode_toggle = document.getElementById("mode_toggle");
    lb = document.getElementById("lb");
    rb = document.getElementById("rb");
    nat = document.getElementById("nat");
    lld = document.getElementById("lld");
    dt = document.getElementById("dt");
    ndt = document.getElementById("ndt");
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
        loadInitalData(device_id);
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
        return new Promise(function (resolve, reject) {
            let request = new XMLHttpRequest();
            request.open("POST", uri);
            if (header) {
               request.setRequestHeader(header[0], header[1]);
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
            if (body) {
                request.send(body);
            } else {
                request.send();
            }
        })
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

async function toggleAstrt(box) {
    if (box.checked === true) {
        await httpPost(device_id + "/eas").catch(function (e) {
            console.log(e);
        });
    } else if (box.checked === false) {
        await httpPost(device_id + "/das").catch(function (e) {
            console.log(e);
        });
    }
    let result = await httpGet(device_id + "/sett").catch(function (e) {
        return false;
    });
    if (result) {
        setSettings(result);
    }
}

async function setConf(result) {
    let conf = JSON.parse(result);
    nat.value = conf.conf_a;
    lld.value = conf.conf_b;
    lb.value = conf.conf_a;
    rb.value = conf.conf_b;
    dt.value = conf.dt;
    ndt.value = conf.ndt;
}

async function setSettings(result) {
    let conf = JSON.parse(result);
    device_mode = conf.mode;
    tkwh.value = conf.tkwh;
    rpkwh.value = conf.rpkwh;
    name.value = conf.name;
    title.innerHTML = conf.name;
    if (conf.strt === 0){
        astrt.checked = false;
    } else if (conf.strt === 1) {
        astrt.checked = true;
    }
    if (device_mode === "I"){
        mode_toggle.checked = false;
        mode_i_conf.style.display = "block";
        mode_a_conf.style.display = "none";
    } else if (device_mode === "A") {
        mode_toggle.checked = true;
        mode_a_conf.style.display = "block";
        mode_i_conf.style.display = "none";
    }
}

async function toggleSettingsModal() {
    if (settings_modal.style.display === "none" || settings_modal.style.display === "") {
        let result = await httpGet(device_id + "/sett").catch(function (e) {
            return false;
        });
        if (result) {
            setSettings(result);
            settings_modal.style.display = "block";
        }
    } else {
        settings_modal.style.display = "none";
    }
}

async function toggleConfModal() {
    if (conf_modal.style.display === "none" || conf_modal.style.display === "") {
        let result = await httpGet(device_id + "/conf").catch(function (e) {
            return false;
        });
        if (result) {
            setConf(result);
            conf_modal.style.display = "block";
            settings_modal.style.display = "none";
        }
    } else {
        conf_modal.style.display = "none";
        settings_modal.style.display = "block";
    }
}

async function submitConf(device=device_id) {
    //let test = nat.checkValidity() && dt.checkValidity() && lld.checkValidity() && rpkwh.checkValidity() && tkwh.checkValidity();
    //console.log(test);
    let conf_a;
    let conf_b;
    if (device_mode === "I"){
        conf_a = lb.value;
        conf_b = rb.value;
    } else if (device_mode === "A") {
        conf_a = nat.value;
        conf_b = lld.value;
    }
    let data = JSON.stringify({
        conf_a: conf_a,
        conf_b: conf_b,
        dt: dt.value,
        ndt: ndt.value
    });
    await httpPost(device + "/conf", ["Content-type", "application/json"], data).catch(function (e) {
        console.log(e);
    });
    toggleConfModal();
}

async function submitSettings(device=device_id) {
    //let test = nat.checkValidity() && dt.checkValidity() && lld.checkValidity() && rpkwh.checkValidity() && tkwh.checkValidity();
    //console.log(test);
    let mode;
    if (mode_toggle.checked === false) {
        mode = "I";
    } else {
        mode = "A";
    }
    let data = JSON.stringify({
        tkwh: tkwh.value,
        name: name.value,
        mode: mode,
        rpkwh: rpkwh.value
    });
    await httpPost(device + "/sett", ["Content-type", "application/json"], data).catch(function (e) {
        console.log(e);
    });
    let result = await httpGet(device + "/sett").catch(function (e) {
        return false;
    });
    if (result) {
        setSettings(result);
    }
    toggleSettingsModal();
}