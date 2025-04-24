let history;
let nVersions;
let currentVersion;
let editDistances;
let timestamps;
let historyFormat = "old"
let result_id = undefined

let goToSig = false;

function toANSHandler() {
    if (result_id === undefined) {
        alert("No result id could be found. Retrieving the assignment again might fix this.")
        return
    }
    window.open(`https://ans.app/results/${result_id}`, '_blank');
}


function fetchHistory() {
    console.log("fetching history...")
    resetHistory()
    history = [
        {
            "changes": {
                "content": "<i>Loading Response...</i>"
            }
        },
        {
            "changes": {
                "content": "<i>Loading Response...</i>"
            }
        }
    ]
    setVersionNumber(1);

    fetch("/api/history")
        .then(response => response.json())
        .then(data => processHistory(data))
        .catch(error => console.error('Error:', error));

    console.log("Fetched history successfully");
}

function processHistory(data) {
    history = data["history"];
    editDistances = data["edit_distances"];
    timestamps = data["timestamps"];
    nVersions = history.length-1
    historyFormat = data["format"]
    result_id = history[0]["result_id"]

    document.getElementById("toAnsBtn").disabled = result_id === undefined

    if ( 1 <= currentVersion && currentVersion <= nVersions ) {
        setVersionNumber(currentVersion)
    } else {
        finalVersion()
    }
}

function resetHistory() {
    currentVersion = -1;
    history = [];
    editDistances = [];
    nVersions = -1;
    timestamps = []
    result_id = undefined
}

function goToSignificant() {
    if (!editDistances) {
        goToSig = true;
        fetchHistory()
        return;
    }

    goToSig = false;
    let index = -1;

    // find an exact match to the significant edit distance
    for (let i = 0; i < editDistances.length; i++) {
        if (editDistances[i] === significantEd) {
            index = i;
            break;
        }
    }

    if (index === -1) {
        console.error("Could not find significant edit distance: " + significantEd + " in " + editDistances)
        return;
    }

    // found set the version and update the text
    currentVersion = index+1
    console.log("Found significant at version " + currentVersion)

    setVersionNumber(currentVersion)
}

function processText(asList) {
    let left = "<div>"
    let right = "<div>"

    for (let pair of asList) {
        const sign = pair[0]
        const text = pair[1]

        if (sign === "+") {
            right += "<span class='text-plus'>" + text + "</span>"
        }
        else if (sign === "-") {
            left += "<span class='text-minus'>" + text + "</span>"
        }
        else if (sign === " ") {
            left += text
            right += text
        }
        else {
            console.error("Unknown sign while processing diff: '" + sign + "'" )
        }

    }
    left += "</div>"
    right += "</div>"

    return [left, right]
}


function setText() {
    if (!history) {
        fetchHistory();
        return;
    }

    if (historyFormat === "old") {
        if (history[currentVersion] === undefined) {
            document.getElementById("left_version_div").innerHTML = "<i>*No previous version exists*</i>";
            document.getElementById("right_version_div").innerHTML = processContent(history[currentVersion-1]["changes"]["content"])
        } else {
            document.getElementById("left_version_div").innerHTML = processContent(history[currentVersion-1]["changes"]["content"])
            document.getElementById("right_version_div").innerHTML = processContent(history[currentVersion]["changes"]["content"])
        }
    } else {
        const pair = processText(history[currentVersion - 1])

        document.getElementById("left_version_div").innerHTML = pair[0];
        document.getElementById("right_version_div").innerHTML = pair[1];
    }


}

/**
 * Make null values explicit
 * @param content the content
 * @returns {*|string} explicit null as string or content
 */
function processContent(content) {
    if (content === null) {
        return "<i>*NULL*</i>"
    }
    return content
}

function nextVersion() {
    if (currentVersion < nVersions) {
        currentVersion++;
        setVersionNumber(currentVersion);
    }
}

function previousVersion() {
    if (currentVersion > 1) {
        currentVersion--;
        setVersionNumber(currentVersion)
    }
}

function firstVersion() {
    currentVersion = 1;
    setVersionNumber(currentVersion)
}

function finalVersion() {
    currentVersion = nVersions
    setVersionNumber(currentVersion)
}

function setVersionNumber(number) {
    if (goToSig) {
        goToSignificant();
        return;
    }

    if (number <= 1) {
        number = 1;
    }
    currentVersion = number
    setText();
    document.getElementById("version").innerHTML = `${number} / ${nVersions}`

    document.getElementById("next-version").disabled = number === nVersions
    document.getElementById("final-version").disabled = number === nVersions

    document.getElementById("previous-version").disabled = number === 0
    document.getElementById("first-version").disabled = number === 0

    if (!editDistances) {
        document.getElementById("edit_distance").innerHTML = ""
    } else {
        let text = (editDistances[currentVersion-1] === undefined) ? '-' : editDistances[currentVersion-1];

        document.getElementById("edit_distance").innerHTML = `<b>Edit Distance:</b> ${text}`
    }

    if (!timestamps) {
        document.getElementById("timestamp").innerHTML = ""
    } else {
        const timeDif = timestamps[currentVersion-1]

        const days = String(Math.floor(timeDif / (60 * 60 * 24))).padStart(2, '0');
        const hours = String(Math.floor((timeDif % (60 * 60 * 24)) / (60 * 60))).padStart(2, '0');
        const minutes = String(Math.floor((timeDif % (60 * 60)) / (60))).padStart(2, '0');
        const seconds = String(Math.floor((timeDif % (60)))).padStart(2, '0');

        let timeText;
        if (days > 0) {
            timeText = `+${days}d ${hours}h ${minutes}m ${seconds}s`
        } else if (hours > 0) {
            timeText = `+${hours}h ${minutes}m ${seconds}s`
        } else if (minutes > 0) {
            timeText = `+${minutes}m ${seconds}s`
        } else {
            timeText = `+${seconds}s`
        }

        if (timeText === "+NaNs") {
            timeText = "-"
        }

        document.getElementById("timestamp").innerHTML = `<b>Time:</b> ${timeText}`
    }
}