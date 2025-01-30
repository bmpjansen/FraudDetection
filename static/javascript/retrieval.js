
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

let responseTree;
let aidSelect;
let eidSelect;
let qidSelect;


function getIdTree() {
    simpleFetch("/api/id_tree", processIdTree);
}


function processIdTree(data) {
    responseTree = data;
    aidSelect = document.getElementById("aidSelect");
    eidSelect = document.getElementById("eidSelect");
    qidSelect = document.getElementById("qidSelect");

    populateSelect(aidSelect, Object.keys(responseTree));
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
    let eids = aid === "all" ? Object.values(responseTree).flatMap(Object.keys) :
                                       Object.keys(responseTree[aid] || {});
    populateSelect(eidSelect, eids);
    updateQidOptions();
}

function updateQidOptions() {
    const aid = aidSelect.value;
    const eid = eidSelect.value;
    let qids;

    if (aid === "all") {
        qids = Object.values(responseTree).flatMap(a => Object.values(a).flatMap(Object.keys));
    } else if (eid === "all") {
        qids = Object.values(responseTree[aid] || {}).flatMap(Object.keys);
    } else {
        qids = Object.keys(responseTree[aid]?.[eid] || {});
    }
    populateSelect(qidSelect, qids);
    qidChange()
}

function qidChange() {
    const ids = [aidSelect.value, eidSelect.value, qidSelect.value];
    const out = [];

    for (let i = 0; i < ids.length; i++) {
        if (ids[i] === 'all') {
            break;
        }
        out.push(ids[i]);
    }

    setActiveSet(out);
}


function setActiveSet(ids) {
    console.log(`New active set: [${ids}]`);
    simplePost("/api/set_active_set", processInfo, ids)
}

