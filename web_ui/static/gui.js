"use strict";

let main_navigation;
let blocker;
let settings_modal;
let conf_modal;
let cal_modal;
let plot_modal;
let mode_a_conf;
let mode_i_conf;
let loader;
let boundary_wrapper;
let diagram_wrapper;
let graph_wrapper;
let graph_box;
let help_wrapper;
let controls_1;
let controls_2;
let controls_3;
let controls_4;
let controls_5;
let controls_6;
let astrt;
let current_device;
let current_ws;
let ws_console;
let title;
let sett_form;
let conf_form;
let hst_form;
let cal_form;
let disconnected_modal;
let loader_cal;
let loader_plot;

function httpPost(uri, header, body) {
    if (uri) {
        return new Promise(function (resolve, reject) {
            let request = new XMLHttpRequest();
            request.open("POST", uri, true);
            if (header) {
                request.setRequestHeader(header[0], header[1]);
            }
            request.timeout = 25000;
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
            request.open("GET", uri, true);
            if (header) {
                request.setRequestHeader(header);
            }
            request.timeout = 25000;
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
    let err;
    loader.style.display = "block";
    if (method === 'GET') {
        response = await httpGet(uri, header).catch(function (e) {
            err = e;
        });
    }
    if (method === 'POST') {
        response = await httpPost(uri, content_type, body).catch(function (e) {
            err = e;
        });
    }
    loader.style.display = "none";
    return response || err;
}

window.addEventListener("DOMContentLoaded", function (e) {
    main_navigation = document.getElementsByClassName('main-navigation')[0];
    disconnected_modal = document.getElementById('disconnected_modal');
    settings_modal = document.getElementById('settings_modal');
    conf_modal = document.getElementById('conf_modal');
    cal_modal = document.getElementById('cal_modal');
    plot_modal = document.getElementById('plot_modal');
    mode_a_conf = document.getElementById("mode_a");
    mode_i_conf = document.getElementById("mode_i");
    loader = document.getElementById("loader");
    loader_cal = document.getElementById("loader_cal");
    loader_plot = document.getElementById("loader_plot");
    controls_1 = document.getElementById("control_set_1");
    controls_2 = document.getElementById("control_set_2");
    controls_3 = document.getElementById("control_set_3");
    controls_4 = document.getElementById("control_set_4");
    controls_5 = document.getElementById("control_set_5");
    controls_6 = document.getElementById("control_set_6");
    diagram_wrapper = document.getElementsByClassName('diagram_wrapper')[0];
    graph_wrapper = document.getElementsByClassName('graph_wrapper')[0];
    graph_box = document.getElementById("graph");
    help_wrapper = document.getElementsByClassName('help_wrapper')[0];
    boundary_wrapper = document.getElementsByClassName('boundary_wrapper')[0];
    astrt = document.getElementById("astrt");
    title = document.getElementById("title");
    ws_console = document.getElementById('console');
    sett_form = document.getElementById('sett_form');
    conf_form = document.getElementById('conf_form');
    hst_form = document.getElementById('hst_form');
    cal_form = document.getElementById('cal_form');
    blocker = document.getElementsByClassName('blocker')[0];
    blocker.style.display = "block";
    window.addEventListener("click", function (e) {
        if (e.target === settings_modal) {
            toggleSettingsModal();
        }
    });
    loadDevices();
    setInterval(function(){pollDevices();}, 5000);
});

function setDevices(devices) {
    devices = JSON.parse(devices);
    if (current_device && devices.includes(current_device) === false) {
        disconnected_modal.style.display = "block";
    } else {
        disconnected_modal.style.display = "none";
        while (main_navigation.firstChild) {
            main_navigation.removeChild(main_navigation.firstChild);
        }
        for (let device of devices) {
            let btn = document.createElement('button');
            if (device === current_device) {
                btn.className = 'btnactive';
            } else {
                btn.className = 'btn';
            }
            btn.type = 'button';
            btn.id = device;
            btn.onclick = function () {
                loadDevice(device);
            };
            let btn_text = document.createTextNode('Device ' + device);
            btn.appendChild(btn_text);
            main_navigation.appendChild(btn);
        }
    }
}

async function loadDevices() {
    let result = await awaitRequest('GET', 'devices');
    if (result.status === 200) {
        setDevices(result.response);
    }
    return false;
}

function pollDevices() {
    let request = new XMLHttpRequest();
    request.open("GET", 'devices', true);
    request.timeout = 15000;
    request.onreadystatechange = function () {
        if (request.readyState === 4) {
            if (request.status === 200) {
                setDevices(request.response)
            }
        }
    };
    request.send();
}

async function loadDevice(device_id) {
    title.innerHTML = "Ferraris Sensor Gateway";
    astrt.checked = false;
    current_device = undefined;
    if (current_ws !== undefined) {
        current_ws.close(1000);
        current_ws = undefined;
        while (ws_console.firstChild) {
            ws_console.removeChild(ws_console.firstChild);
        }
    }
    let current_btns = main_navigation.getElementsByTagName('button');
    for (let item of current_btns) {
        item.className = 'btn';
    }
    let result = await awaitRequest('GET', 'devices/' + device_id);
    if (result.status === 200) {
        let result2 = await awaitRequest('POST', 'devices/' + device_id + '/co');
        if (result2.status === 200) {
            current_device = device_id;
            let btn = document.getElementById(current_device);
            btn.className = 'btnactive';
            result = JSON.parse(result.response);
            title.innerHTML = result.name;
            if (result.strt === 0){
                astrt.checked = false;
            } else if (result.strt === 1) {
                astrt.checked = true;
            }
            current_ws = openWS();
            blocker.style.display = "none";
            return true;
        }
    }
    location.href=('');
    return false;
}

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
    return ws;
}

async function btnRequest(method, endpoint) {
    awaitRequest(method, 'devices/' + current_device + '/' + endpoint);
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
    let res = await awaitRequest('POST', 'devices/' + current_device + "/as", ["Content-type", "application/json"], data);
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
        let result = await awaitRequest('GET', 'devices/' + current_device);
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
    let response = await awaitRequest('POST', 'devices/' + current_device, ["Content-type", "application/json"], data);
    if (response.status === 200) {
        title.innerHTML = form.name.value;
        toggleSettingsModal();
    } else {
        setSettings(form.prev_sett.value);
    }

}

async function toggleConfModal() {
    if (conf_modal.style.display === "none" || conf_modal.style.display === "") {
        let result = await awaitRequest('GET', 'devices/' + current_device + "/conf");
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
    let response = await awaitRequest('POST', 'devices/' + current_device + "/conf", ["Content-type", "application/json"], data);
    if (response.status === 200) {
        toggleConfModal();
    } else {
        setConf(form.prev_conf.value)
    }

}

async function toggleCalModal(stp=true) {
    if (cal_modal.style.display === "none" || cal_modal.style.display === "") {
        conf_modal.style.display = "none";
        controls_1.style.display = "block";
        cal_modal.style.display = "block";
        let res = await awaitRequest('POST', 'devices/' + current_device + "/fb");
        if (res.status === 200) {
            loader_cal.style.display = "block";
            help_wrapper.innerHTML = "Detecting brightest and darkest points.<br><br>Please wait for at least one full rotation before clicking 'Next'.";
            controls_1.style.display = "block";
        } else {
            help_wrapper.innerHTML = "Unable to start calibration. Device busy?";
        }
    } else {
        controls_1.style.display = "none";
        controls_2.style.display = "none";
        controls_3.style.display = "none";
        diagram_wrapper.style.display = "none";
        controls_4.style.display = "none";
        cal_modal.style.display = "none";
        conf_modal.style.display = "block";
        if (stp) {
            await awaitRequest('POST', 'devices/' + current_device + "/stp");
        }
    }
}

async function togglePlotModal(stp=true) {
    if (plot_modal.style.display === "none" || plot_modal.style.display === "") {
        conf_modal.style.display = "none";
        plot_modal.style.display = "block";
        let old_plot = await awaitRequest('GET', 'devices/' + current_device + "/gp");
        if (old_plot.status === 200) {
            graph_wrapper.style.display = "block";
            let data = JSON.parse(old_plot.response)['res'];
            new Dygraph(
                    graph_box,
                    data,
                    {
                        ylabel: 'Value',
                        xlabel: 'Reading',
                        labels: [ "Reading", "Value" ]
                    }
                );
            help_wrapper.innerHTML = "Look for large dips to determine the correct interval.";
            controls_5.style.display = "block";
        } else {
            loader_plot.style.display = "block";
            let res = await awaitRequest('POST', 'devices/' + current_device + "/pr");
            if (res.status === 200) {
                help_wrapper.innerHTML = "Collecting data.<br><br>Please wait for at least one full rotation before clicking 'Next'.";
                controls_6.style.display = "block";
            } else {
                loader_plot.style.display = "none";
                help_wrapper.innerHTML = "Unable to start calibration. Device busy?";
                controls_5.style.display = "block";
            }
        }
    } else {
        graph_wrapper.style.display = "none";
        controls_5.style.display = "none";
        controls_6.style.display = "none";
        plot_modal.style.display = "none";
        conf_modal.style.display = "block";
        help_wrapper.innerHTML = "";
        if (stp) {
            await awaitRequest('POST', 'devices/' + current_device + "/stp");
        }
    }
}

async function collectReadings() {
    graph_wrapper.style.display = "none";
    controls_5.style.display = "none";
    controls_6.style.display = "none";
    help_wrapper.innerHTML = "";
    loader_plot.style.display = "block";
    let res = await awaitRequest('POST', 'devices/' + current_device + "/pr");
    if (res.status === 200) {
        help_wrapper.innerHTML = "Collecting data.<br><br>Please wait for at least one full rotation before clicking 'Next'.";
        controls_5.style.display = "none";
        controls_6.style.display = "block";
    } else {
        loader_plot.style.display = "none";
        help_wrapper.innerHTML = "Unable to start calibration. Device busy?";
        controls_5.style.display = "block";
    }
}

async function plotReadings() {
    let res = await awaitRequest('POST', 'devices/' + current_device + "/stp");
    if (res.status === 200) {
        loader_plot.style.display = "none";
        controls_6.style.display = "none";
        graph_wrapper.style.display = "block";
        let data = JSON.parse(res.response)['res'];
        new Dygraph(
                graph_box,
                data,
                {
                    ylabel: 'Value',
                    xlabel: 'Reading',
                    labels: [ "Reading", "Value" ]
                }
            );
        help_wrapper.innerHTML = "Look for large dips to determine the correct interval.";
        controls_5.style.display = "block";
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
    element.addEventListener("click", function (e) {
        let bars = diagram_wrapper.querySelectorAll('[class="diagram_element_bar"]');
        for (let item of bars) {
            item.style.background = null;
        }
        let old_inputs = cal_form.querySelectorAll('[type="hidden"]');
        for (let item of old_inputs) {
            cal_form.removeChild(item);
        }
        let lb_field = document.createElement('input');
        lb_field.id = 'lb';
        lb_field.setAttribute('type', 'hidden');
        lb_field.value = lb;
        let rb_field = document.createElement('input');
        rb_field.id = 'rb';
        rb_field.setAttribute('type', 'hidden');
        rb_field.value = rb;
        cal_form.appendChild(lb_field);
        cal_form.appendChild(rb_field);
        bar.style.background = "#db0006";
    });
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

async function getFB() {
    let res = await awaitRequest('POST', 'devices/' + current_device + "/stp");
    if (res.status === 200) {
        loader_cal.style.display = "none";
        controls_1.style.display = "none";
        let points = JSON.parse(res.response)['res'].split(':');
        help_wrapper.innerHTML = "Lowest point: "+ points[0] +"<br><br>Brightest point: "+ points[1] +"<br><br>Please enter the desired number of intervals and press 'Next' to continue calibration.";
        hst_form.lowest.value = points[0];
        hst_form.highest.value = points[1];
        hst_form.intervals.value = 10;
        controls_2.style.display = "block";
    }
}

async function startHST(form) {
    let data = JSON.stringify({
        lb: form.lowest.value,
        rb: form.highest.value,
        res: form.intervals.value
    });
    let response = await awaitRequest('POST', 'devices/' + current_device + "/hst", ["Content-type", "application/json"], data);
    if (response.status === 200) {
        controls_2.style.display = "none";
        loader_cal.style.display = "block";
        help_wrapper.innerHTML = "Detecting intervals.<br><br>Please wait for at least one full rotation before clicking 'Next'.";
        controls_3.style.display = "block";
    } else {
        help_wrapper.innerHTML = "Unable to detect intervals. Device busy?";
    }
}

async function getHST() {
    let res = await awaitRequest('POST', 'devices/' + current_device + "/stp");
    if (res.status === 200) {
        loader_cal.style.display = "none";
        controls_3.style.display = "none";
        controls_4.style.display = "block";
        help_wrapper.innerHTML = "The highest bar residing in the left half of the diagram corresponds to the disk's red mark.<br><br>Please select the appropriate bar and click 'Finish'.";
        buildHistogram(JSON.parse(res.response)['res']);
        diagram_wrapper.style.display = "block";
    }
}

async function finishCal(form) {
    if (conf_form.lb.value && conf_form.rb.value) {
        conf_form.lb.value = form.lb.value;
        conf_form.rb.value = form.rb.value;
        toggleCalModal(false);
    }
}