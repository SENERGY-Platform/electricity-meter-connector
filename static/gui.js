"use strict";

let settings_modal;
let conf_modal;
let cal_modal;
let mode_a_conf;
let mode_i_conf;
let loader;
let boundary_wrapper;
let diagram_wrapper;
let help_wrapper;
let controls_1;
let controls_2;
let controls_3;
let astrt;
let device_id;
let ws_console;
let title;
let sett_form;
let conf_form;

function setDevice(device) {
    device_id = device;
}

async function loadInitalData(device_id) {
    let result = await awaitRequest('GET', device_id + "/sett").catch(function (e) {
        return false;
    });
    if (result.status === 200) {
        result = JSON.parse(result.response);
        title.innerHTML = result.name;
        if (result.strt === 0){
            astrt.checked = false;
        } else if (result.strt === 1) {
            astrt.checked = true;
        }
        return true;
    } else {
        return false;
    }
}

window.addEventListener("DOMContentLoaded", function (e) {
    settings_modal = document.getElementById('settings_modal');
    conf_modal = document.getElementById('conf_modal');
    cal_modal = document.getElementById('cal_modal');
    mode_a_conf = document.getElementById("mode_a");
    mode_i_conf = document.getElementById("mode_i");
    loader = document.getElementById("loader");
    controls_1 = document.getElementById("control_set_1");
    controls_2 = document.getElementById("control_set_2");
    controls_3 = document.getElementById("control_set_3");
    diagram_wrapper = document.getElementsByClassName('diagram_wrapper')[0];
    help_wrapper = document.getElementsByClassName('help_wrapper')[0];
    boundary_wrapper = document.getElementsByClassName('boundary_wrapper')[0];
    astrt = document.getElementById("astrt");
    title = document.getElementById("title");
    ws_console = document.getElementById('console');
    sett_form = document.getElementById('sett_form');
    conf_form = document.getElementById('conf_form');
    let content = document.getElementsByClassName('content')[0];
    let blocker = document.getElementsByClassName('blocker')[0];
    let subnav = document.getElementsByClassName('sub-navigation')[0];
    let subnav_btns = subnav.getElementsByClassName('btn');
    let checkbox = subnav.getElementsByClassName('container')[0];
    if (device_id && loadInitalData(device_id)) {
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

function httpPost(uri, header, body) {
    if (uri) {
        return new Promise(function (resolve, reject) {
            let request = new XMLHttpRequest();
            request.open("POST", uri);
            if (header) {
                request.setRequestHeader(header[0], header[1]);
            }
            request.timeout = 15000;
            request.onreadystatechange = function () {
                if (request.readyState === 4) {
                    if (request.status === 200) {
                        resolve(request);
                    } else {
                        reject(request);
                    }
                }
            };
            request.ontimeout = function () {
                reject(request);
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
            request.timeout = 15000;
            request.onreadystatechange = function () {
                if (request.readyState === 4) {
                    if (request.status === 200) {
                        resolve(request);
                    } else {
                        reject(request);
                    }
                }
            };
            request.ontimeout = function () {
                reject(request);
            };
            request.send();
        })
    }
}

async function awaitRequest(method, uri, content_type, body, header) {
    let response;
    loader.style.display = "block";
    if (method === 'GET') {
        response = await httpGet(uri, header).catch(function (e) {
            console.log(e);
        });
    }
    if (method === 'POST') {
        response = await httpPost(uri, content_type, body).catch(function (e) {
            console.log(e);
        });
    }
    loader.style.display = "none";
    return response;
}

async function toggleAstrt(box) {
    let data;
    if (box.checked === true) {
        data = JSON.stringify({
            state: 1
        });
    } else if (box.checked === false) {
        data = JSON.stringify({
            state: 0
        });
    }
    let res = await awaitRequest('POST', device_id + "/as", ["Content-type", "application/json"], data).catch(function (e) {
        console.log(e);
    });
    if (res.status === 200) {
        res = JSON.parse(res.response);
        if (res.state === 0){
            astrt.checked = false;
        } else if (res.state === 1) {
            astrt.checked = true;
        }
    } else {
        astrt.checked = false;
    }
}

async function toggleSettingsModal() {
    if (settings_modal.style.display === "none" || settings_modal.style.display === "") {
        let result = await awaitRequest('GET', device_id + "/sett").catch(function (e) {
            return false;
        });
        if (result.status === 200) {
            sett_form.prev_sett.value = result.response;
            setSettings(result.response);
            settings_modal.style.display = "block";
        }
    } else {
        settings_modal.style.display = "none";
    }
}

function setSettings(settings) {
    settings = JSON.parse(settings);
    sett_form.name.value = settings.name;
    sett_form.rpkwh.value = settings.rpkwh;
    sett_form.tkwh.value = settings.tkwh;
}

async function submitSettings(form) {
    let data = JSON.stringify({
        tkwh: form.tkwh.value,
        name: form.name.value,
        rpkwh: form.rpkwh.value
    });
    let response = await awaitRequest('POST', device_id + "/sett", ["Content-type", "application/json"], data);
    if (response.status === 200) {
        toggleSettingsModal();
    } else {
        setSettings(form.prev_sett.value);
    }

}

async function toggleConfModal() {
    if (conf_modal.style.display === "none" || conf_modal.style.display === "") {
        let result = await awaitRequest('GET', device_id + "/conf").catch(function (e) {
            return false;
        });
        if (result.status === 200) {
            conf_form.prev_conf.value = result.response;
            setConf(result.response);
            settings_modal.style.display = "none";
            conf_modal.style.display = "block";
        }
    } else {
        conf_modal.style.display = "none";
        settings_modal.style.display = "block";
    }
}

function toggleMode(box) {
    if (box.checked === true) {
        mode_a_conf.style.display = "block";
        mode_i_conf.style.display = "none";
    } else if (box.checked === false) {
        mode_i_conf.style.display = "block";
        mode_a_conf.style.display = "none";
    }
}

function setConf(conf) {
    conf = JSON.parse(conf);
    conf_form.nat.value = conf.conf.A.conf_a;
    conf_form.lld.value = conf.conf.A.conf_b;
    conf_form.lb.value = conf.conf.I.conf_a;
    conf_form.rb.value = conf.conf.I.conf_b;
    conf_form.dt.value = conf.dt;
    conf_form.ndt.value = conf.ndt;
    if (conf.mode === "I"){
        conf_form.mode_toggle.checked = false;
        mode_i_conf.style.display = "block";
        mode_a_conf.style.display = "none";
    } else if (conf.mode === "A") {
        conf_form.mode_toggle.checked = true;
        mode_a_conf.style.display = "block";
        mode_i_conf.style.display = "none";
    }
}

async function submitConf(form) {
    let conf_a;
    let conf_b;
    let mode;
    if (form.mode_toggle.checked === false) {
        mode = "I";
        conf_a = form.lb.value;
        conf_b = form.rb.value;
    } else {
        mode = "A";
        conf_a = form.nat.value;
        conf_b = form.lld.value;
    }
    let data = JSON.stringify({
        mode: mode,
        conf_a: conf_a,
        conf_b: conf_b,
        dt: form.dt.value,
        ndt: form.ndt.value
    });
    let response = await awaitRequest('POST', device_id + "/conf", ["Content-type", "application/json"], data);
    if (response.status === 200) {
        toggleConfModal();
    } else {
        setConf(form.prev_conf.value)
    }

}

















function toggleCalModal() {
    if (cal_modal.style.display === "none" || cal_modal.style.display === "") {
        conf_modal.style.display = "none";
        help_wrapper.style.display = "block";
        controls_1.style.display = "block";
        cal_modal.style.display = "block";
    } else {
        controls_1.style.display = "none";
        controls_2.style.display = "none";
        controls_3.style.display = "none";
        help_wrapper.style.display = "none";
        diagram_wrapper.style.display = "none";
        boundary_wrapper.style.display = "none";
        cal_modal.style.display = "none";
        conf_modal.style.display = "block";
        httpPost(device_id + '/stp');
    }
}

function buildDiaElement(lb, rb, val, highest, res) {
    let element = document.createElement('div');
    element.className = 'diagram_element';
    element.style.width = Math.floor((680 - 2 * res) / res) + 'px';
    let bar = document.createElement('div');
    bar.className = 'diagram_element_bar';
    let bar_val = document.createTextNode(val);
    if (highest > 265) {
        let ref = highest / 265;
        bar.style.height = Math.floor(val / ref) + 'px';
    } else {
        bar.style.height = val + 'px';
    }
    if (parseInt(bar.style.height, 10) >= 10) {
        bar.appendChild(bar_val);
    }
    let label = document.createElement('div');
    label.className = 'diagram_element_label';
    let text = document.createTextNode(lb + ' - ' + rb);
    label.appendChild(text);
    element.appendChild(bar);
    element.appendChild(label);
    return element;
}


function buildHistogram(data) {
    while (diagram_wrapper.firstChild) {
        diagram_wrapper.removeChild(diagram_wrapper.firstChild);
    }
    let data_array = data.split(';');
    let max = 0;
    for (let item of data_array) {
        if (Number(item.split(':')[2]) > max) {
            max = Number(item.split(':')[2]);
        }
    }
    for (let item of data_array) {
        let element = buildDiaElement(Number(item.split(':')[0]), Number(item.split(':')[1]), Number(item.split(':')[2]), max, data_array.length);
        diagram_wrapper.appendChild(element);
    }
}


async function updateHST() {
    loader.style.display = "block";
    let result = await httpGet(device_id + "/hst").catch(function (e) {
        console.log(e);
    });
    if (result) {
        buildHistogram(result);
    }
    loader.style.display = "none";
}

async function updateBoundaries() {
    loader.style.display = "block";
    let result = await httpGet(device_id + "/fb").catch(function (e) {
        console.log(e);
    });
    if (result) {
        boundary_wrapper.innerHTML = result;
    }
    loader.style.display = "none";
}

async function startCal() {
    httpPost(device_id + "/fb").catch(function (e) {
        console.log(e);
    });
    boundary_wrapper.style.display = "block";
    controls_1.style.display = "none";
    controls_2.style.display = "block";

}

async function startHST() {
    loader.style.display = "block";
    let result = await httpGet(device_id + "/fb").catch(function (e) {
        console.log(e);
    });
    if (result) {
        boundary_wrapper.innerHTML = result;
    }
    loader.style.display = "none";
    httpPost(device_id + '/stp');
    while (diagram_wrapper.firstChild) {
        diagram_wrapper.removeChild(diagram_wrapper.firstChild);
    }
    boundary_wrapper.style.display = "none";
    diagram_wrapper.style.display = "block";
    controls_2.style.display = "none";
    controls_3.style.display = "block";
}

async function finishCal() {
    toggleCalModal()
}