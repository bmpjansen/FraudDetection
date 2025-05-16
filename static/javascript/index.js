
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

    document.getElementById("prev_response_button").disabled = data["index"] <= 0
    document.getElementById("next_response_button").disabled = data["index"] === data["n_responses"]-1

    significantEd = data["max_ed"];
    document.getElementById("sum_edit_distance_val").innerHTML = significantEd;

    document.getElementById("html_select").value = data["html"]

    fetchHistory()

	// Plot of the number of versions
    if (data['num_versions'] === undefined || data['num_versions'] === "unavailable") {
        document.getElementById("box_plot_div").innerHTML = "Histogram of number of submitted versions unavailable"
	} else {
		document.getElementById("box_plot_div").innerHTML = ""
		renderHistogram(data['num_versions'], "box_plot_div", "#versions for " + document.getElementById("eidSelect").value + " #" + document.getElementById("qidSelect").selectedIndex)
	}

	// Plot of the number of versions
    if (data['all_max_edit_distances'] === undefined || data['all_max_edit_distances'] === "unavailable") {
        document.getElementById("ed_histogram_div").innerHTML = "Histogram of maximum edit distances unavailable"
	} else {
		document.getElementById("ed_histogram_div").innerHTML = ""
		renderHistogram(data['all_max_edit_distances'], "ed_histogram_div", "max. edit distances for " + document.getElementById("eidSelect").value + " #" + document.getElementById("qidSelect").selectedIndex)
	}

    // table
    if (data["csv"] !== undefined) {
        $('#CSVTable').CSVToTable(data["csv"]);
    }
}

function renderHistogram(num_versions, targetElementID, histogramTitle) {
	const data = [{
		x: num_versions,
		type: 'histogram',
		marker: {
			color: 'rgba(100, 150, 250, 0.7)',
			line: {
				color: 'rgba(0, 0, 0, 1)',
				width: 1
			},
		}
	}];

	const layout = {
		title: histogramTitle,
		xaxis: { title: 'Value' },
		yaxis: { title: 'Frequency' },
		bargap: 0.05,
		width: 1200,
		height: 600
	};

	// Write the plot to the 'scatter_div' div element in the HTML template.
	Plotly.newPlot(targetElementID, data, layout);
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

