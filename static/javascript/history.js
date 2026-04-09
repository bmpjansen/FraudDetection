let history;
let nVersions;
let currentVersion;
let editDistances;
let timestamps;
let historyFormat = "old"
let result_id = undefined

let goToSig = false;

function hasArtificialInitialSnapshot() {
    return Array.isArray(history)
        && history.length > 0
        && history[0] !== null
        && history[0]["is_artificial"] === true;
}

function getEditDistanceIndexForVersion(versionNumber) {
    if (nVersions === 0) {
        return 0;
    }

    const offset = hasArtificialInitialSnapshot() ? 1 : 0;
    return versionNumber - 1 + offset;
}

function findResultIdInHistory(entries) {
    if (!Array.isArray(entries)) {
        return undefined;
    }

    for (const entry of entries) {
        if (entry && entry["result_id"] !== undefined && entry["result_id"] !== null) {
            return entry["result_id"];
        }
    }

    return undefined;
}

function setPredefinedAnswerIndicator() {
    const indicator = document.getElementById("predefined_answer_indicator");
    if (!indicator) {
        return;
    }

    if (hasArtificialInitialSnapshot()) {
        indicator.textContent = "Has predefined answer";
    } else {
        indicator.textContent = "";
    }
}

function toANSHandler() {
    if (result_id === undefined || result_id === null) {
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
    result_id = data["result_id"];
    setPredefinedAnswerIndicator();

    if (result_id === undefined || result_id === null) {
        result_id = findResultIdInHistory(history);
    }

    document.getElementById("toAnsBtn").disabled = result_id === undefined || result_id === null

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
    setPredefinedAnswerIndicator();
}

function goToSignificant() {
    if (!Array.isArray(editDistances) || editDistances.length === 0) {
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

    // Map edit-distance index to shown transition index.
    // Histories with a predefined answer have an artificial first snapshot.
    const offset = hasArtificialInitialSnapshot() ? 1 : 0;
    currentVersion = index - offset + 1

    if (currentVersion < 1) {
        currentVersion = 1;
    }

    if (currentVersion > nVersions) {
        currentVersion = nVersions;
    }

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

    document.getElementById("next-version").disabled = number >= nVersions
    document.getElementById("final-version").disabled = number >= nVersions

    document.getElementById("previous-version").disabled = number <= 1
    document.getElementById("first-version").disabled = number <= 1

    if (!Array.isArray(editDistances) || editDistances.length === 0) {
        document.getElementById("edit_distance").innerHTML = ""
    } else {
        let idx = getEditDistanceIndexForVersion(currentVersion);
        let text = (editDistances[idx] === undefined) ? '-' : editDistances[idx];

        document.getElementById("edit_distance").innerHTML = `<b>Edit Distance:</b> ${text}`
    }

    if (!timestamps) {
        document.getElementById("timestamp").innerHTML = ""
    } else {
        let idx = (nVersions === 0) ? 0 : currentVersion;
        const timeDif = timestamps[idx]

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