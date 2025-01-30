
document.addEventListener('DOMContentLoaded', reload, false);

let ids;
let responseID = -1;
let currentIndex = -1;
let significantEd = 0

function reload() {
    simpleFetch("/api/reload", getInfo)
    initAssigmentInput();
    getIdTree();
}

function processInfo(data) {
    if (data["rid"] !== responseID) {
        resetHistory();
    }
    ids = data["rid"];
    responseID = ids[3];
    currentIndex = data["index"];
    setResponseToCurrent();

    document.getElementById("prev_response_button").disabled = data["index"] === 0
    document.getElementById("next_response_button").disabled = data["index"] === data["n_responses"]-1

    significantEd = data["max_ed"];
    document.getElementById("sum_edit_distance_val").innerHTML = significantEd;

    document.getElementById("html_select").value = data["html"]

    fetchHistory()

    // Scatter plot
    if (data['scatter'] === undefined || data['scatter'] === "unavailable") {
        document.getElementById("scatter_div").innerHTML = ""
    } else {
        document.getElementById("scatter_div").innerHTML = `<img src=${data['scatter']} alt="Scatter plot"> `
    }

    // Box plot
    if (data['box_plot'] === undefined || data['box_plot'] === "unavailable") {
        document.getElementById("box_plot_div").innerHTML = ""
    } else {
        document.getElementById("box_plot_div").innerHTML = `<img src=${data['box_plot']} alt="Box plot"> `
    }

    // table
    if (data["csv"] !== undefined) {
        $('#CSVTable').CSVToTable(data["csv"]);
    }
}

function processSpecificResponse(data) {
    if ("error" in data) {
        console.log("error while setting specific response: " + data["error"])
        setResponseToCurrent()
    } else {
        processInfo(data)
    }
}

function setResponseToCurrent() {
    document.getElementById("indexField").value = currentIndex;
    document.getElementById("responseID-field").value = responseID;
}


// --------------------- SIMPLE FETCH ---------------------

function getInfo() {
    simpleFetch('/api/info', processInfo);
}

function nextResponse() {
    simpleFetch('/api/nextResponse', processInfo);
}

function previousResponse() {
    simpleFetch('/api/previousResponse', processInfo)
}

function specificResponseViaIndex(i) {
    if (i === "") {
        setResponseToCurrent()
    } else {
        simpleFetch("/api/response/index/" + i, processSpecificResponse)
    }
}

function specificResponseViaID(i) {
    if (i === "") {
        setResponseToCurrent()
    } else {
        simpleFetch("/api/response/id/" + i, processSpecificResponse)
    }
}

function simpleFetch(endpoint, processFunc) {
    fetch(endpoint)
        .then(response => response.json())
        .then(data => processFunc(data))
        .catch(error => console.error('Error:', error));
}


// --------------------- SIMPLE POST ---------------------

function stripHTML(select) {
    simplePost("/api/striphtml", processHistory, {
        "value": select.value
    })
}

function simplePost(endpoint, processFunc, dict) {
    fetch(endpoint,
    {
            method: "POST",
            headers: {
              "Content-type": "application/json",
            },
            body: JSON.stringify(dict),
        })
        .then((response) => response.json())
        .then((data) => processFunc(data))
        .catch(error => console.error('Error:', error));
}

