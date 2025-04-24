
let toRetrieveList = []

function initAssigmentInput() {

    const inputDiv = document.getElementById('assignment_ids_input_div');
    inputDiv.innerHTML = '';

    for (let i = 0; i < toRetrieveList.length; i++) {

        inputDiv.innerHTML += getAidInput(i, toRetrieveList[i]);

    }

    inputDiv.innerHTML += getAidInput(toRetrieveList.length, null);

}

function updateList(index, newVal) {

    if (newVal === '') {
        newVal = null;
    } else {
        newVal = Number(newVal);
    }

    if (index < 0) {
        console.warn("Was given an index smaller than 0! index was " + index);
        return;
    }

    while (index >= toRetrieveList.length) {
        toRetrieveList.push(null);
    }

    toRetrieveList[index] = newVal;
    console.log("updated! " + toRetrieveList.length);
    initAssigmentInput();
}

function getAidInput(index, content) {
    if (!content) {
        content = ''
    }

    return `<input type=\'number\' id=\'assignment_id_${index}\' onblur=\'updateList(${index}, this.value)\' min=\'0\' value=\'${content}\'>`
}


function retrieve() {
    if (toRetrieveList.length < 1) {
        alert("Please provide at least one assignment id. ")
        return;
    }

    const ids = []
    for (let i = 0; i < toRetrieveList.length; i++) {
        const id = toRetrieveList[i];
        if (id) {
            ids.push(id);
        }
    }

    const api_key = document.getElementById("API_KEY").value

    simplePost("/api/start_retrieval",
        (data) => {},
        {
            'API_KEY': api_key,
            'ids': ids
        })
}

// let responseTree;
let namesTree;
let nameIdList;
let aidSelect;
let eidSelect;
let qidSelect;


function getIdTree() {
    simpleFetch("/api/names_tree", processNamesTree)
}


function processNamesTree(data) {
    console.log(data)
    namesTree = data[0];
    nameIdList = data[1];

    aidSelect = document.getElementById("aidSelect");
    eidSelect = document.getElementById("eidSelect");
    qidSelect = document.getElementById("qidSelect");

    populateSelect(aidSelect, Object.keys(namesTree));
    updateEidOptions();
}


function populateSelect(select, options) {
    select.innerHTML = "";
    select.appendChild(new Option("All", "all"));
    options.forEach(option => select.appendChild(new Option(option, option)));
    select.value = 'all';
}

function updateEidOptions() {
    const aid = aidSelect.value;
    let eids = aid === "all" ? Object.values(namesTree).flatMap(Object.keys) :
                                       Object.keys(namesTree[aid] || {});
    populateSelect(eidSelect, eids);
    updateQidOptions();
}

function updateQidOptions() {
    const aid = aidSelect.value;
    const eid = eidSelect.value;
    let qids;

    eidSelect.disabled = false
    qidSelect.disabled = false

    if (aid === "all") {
        qids = Object.values(namesTree).flatMap(a => Object.values(a).flatMap(Object.keys));
        eidSelect.value = "all"
        eidSelect.disabled = true
        qidSelect.value = "all"
        qidSelect.disabled = true
    } else if (eid === "all") {
        qids = Object.values(namesTree[aid] || {}).flatMap(Object.keys);
        qidSelect.value = "all"
        qidSelect.disabled = true
    } else {
        qids = Object.keys(namesTree[aid]?.[eid] || {});
    }
    populateSelect(qidSelect, qids);
    qidChange()
}

function qidChange() {
    const names = [aidSelect.value, eidSelect.value, qidSelect.value];
    const out = [];

    for (let i = 0; i < names.length; i++) {
        if (names[i] === 'all') {
            break;
        }
        out.push(nameIdList[i][names[i]]);
    }

    setActiveSet(out);
}


function setActiveSet(ids) {
    console.log(`New active set: [${ids}]`);
    simplePost("/api/set_active_set", processInfo, ids)
}

function recheck() {
    simpleFetch("/api/recheck", processRecheck, ids)
    document.getElementById("recheckBtn").disabled = true;
}

function processRecheck(data) {
    document.getElementById("recheck_div").innerHTML = data.status ? "All responses have been processed" : "Some responses have not been processed. They are being computed now!";
    if (data.status) {
        document.getElementById("recheckBtn").disabled = false;
    }
}

