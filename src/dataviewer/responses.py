import html
import logging
import traceback

from os import makedirs
import pickle
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from flask_executor import Executor

from src.editdistance.algorithms.edit_distance import compute_edit_distances

logger = logging.getLogger(__name__)


class HtmlModes(str, Enum):
    KEEP = "Keep"
    SHOW = "Show"
    STRIP = "Strip"


class ResponsesTo(str, Enum):
    ASSIGNMENT = "Assignment"
    EXERCISE = "Exercise"
    QUESTION = "Question"


_use_diff = False
_show_edbo_phrases = True

_html_mode: str = HtmlModes.STRIP

_user_dir: Path

_response_ids: list[list[int]] = []

_current_response_index: int = 0
_current_eds_info: dict | None = None

_response_tree: dict = {}
_edit_distance_tree: dict = {}
_names_tree: dict = {}
_names_ids_list: list = {}
_num_versions_tree: dict = {}

_result_dir: Path
_response_dir: Path

_executor: Executor | None = None


def reinit():
    """
    Reinitialize datastructures with the same directories
    """
    init(_response_dir, _result_dir, _user_dir, _executor)


def init(response_dir: Path, results_dir: Path, user_dir: Path, ex: Executor):
    """
    (Re)initializes all datastructures

    :param response_dir: the root directory of the responses
    :param results_dir: the root directory of the computed edit distances
    :param user_dir: the root directory of remaining files
    """
    global _user_dir, _response_tree, _edit_distance_tree, _names_tree, _names_ids_list, \
        _result_dir, _response_dir,  _executor, _num_versions_tree

    _user_dir = user_dir
    makedirs(user_dir, exist_ok=True)

    _response_dir = response_dir
    _result_dir = results_dir

    _response_tree, _edit_distance_tree, _names_tree, _names_ids_list, _num_versions_tree = construct_trees(response_dir)

    logger.debug(_response_tree)

    if _response_tree is not None:
        if len(list(_response_tree.keys())) > 0:
            assignment_id = list(_response_tree.keys())[0]
            reset_response_ids(_find_all_response_ids([assignment_id]))
        else:
            try:
                set_active_set([])
            except FileNotFoundError:
                pass
    else:
        raise RuntimeError("Something went wrong: response tree was None!")

    _executor = ex


def construct_trees(response_dir: Path) -> tuple[dict, dict, dict, list]:
    tree = {}
    ed_tree = {}
    versions_tree = {}
    names_ids_list = [{}, {}, {}]
    names_tree = {}

    for file_path in response_dir.glob('./*/*/*/*.pickle'):
        # Extract parts of the path
        as_id, ex_id, q_id, resp_id = file_path.parts[-4:]
        resp_id = int(resp_id.split('.')[0])  # Remove file extension
        as_id = int(as_id)
        ex_id = int(ex_id)
        q_id = int(q_id)

        if as_id not in tree:
            tree[as_id] = {}
            ed_tree[as_id] = {}
            versions_tree[as_id] = {}
            as_name = str(as_id)
            if (response_dir / str(as_id) / 'name.txt').exists():
                with open(response_dir / str(as_id) / 'name.txt', 'r') as file:
                    as_name = file.read()
            names_ids_list[0][as_name] = as_id
            names_tree[as_name] = {}

        if ex_id not in tree[as_id]:
            tree[as_id][ex_id] = {}
            ed_tree[as_id][ex_id] = {}
            versions_tree[as_id][ex_id] = {}
            ex_name = str(ex_id)
            if (response_dir / str(as_id) / str(ex_id) / 'name.txt').exists():
                with open(response_dir / str(as_id) / str(ex_id) / 'name.txt', 'r') as file:
                    ex_name = file.read()
            names_ids_list[1][ex_name] = ex_id
            names_tree[as_name][ex_name] = {}

        if q_id not in tree[as_id][ex_id]:
            tree[as_id][ex_id][q_id] = []
            ed_tree[as_id][ex_id][q_id] = {}
            versions_tree[as_id][ex_id][q_id] = {}
            q_name = str(q_id)
            if (response_dir / str(as_id) / str(ex_id) / str(q_id) / 'name.txt').exists():
                with open(response_dir / str(as_id) / str(ex_id) / str(q_id) / 'name.txt', 'r') as file:
                    q_name = file.read()
            names_ids_list[2][q_name] = q_id
            names_tree[as_name][ex_name][q_name] = {}

        resultdata = _read_file(_result_dir, [as_id, ex_id, q_id, resp_id], ED_DEFAULT)
        ed_tree[as_id][ex_id][q_id][resp_id] = resultdata["max"]
        versions_tree[as_id][ex_id][q_id][resp_id] = len(resultdata["edit_distances"])
        tree[as_id][ex_id][q_id].append(resp_id)

    return tree, ed_tree, names_tree, names_ids_list, versions_tree


def _update_current_index(new_index: int):
    if not -1 <= new_index < len(_response_ids):
        raise ValueError(f"Invalid response index {new_index}")

    global _current_response_index, _current_eds_info

    _current_response_index = new_index

    if new_index >= 0:
        _current_eds_info = _read_file(_result_dir, get_cur_id(), ED_DEFAULT)
    else:
        _current_eds_info = ED_DEFAULT


def next_response():
    global _current_response_index

    if _current_response_index == -1:
        return

    _update_current_index((_current_response_index + 1) % len(_response_ids))


def previous_response():
    global _current_response_index

    if _current_response_index == -1:
        return

    _update_current_index((_current_response_index - 1) % len(_response_ids))


def specific_response_index(response_index: int):
    if not (0 <= response_index < len(_response_ids) ):
        raise ValueError(f"{response_index} is out of range: [0, {len(_response_ids)-1}]")

    _update_current_index(response_index)


def specific_response_id(rid: int):
    index = -1
    for i in range(len(_response_ids)):
        if rid == _response_ids[i][3]:
            index = i
            break

    if index == -1:
        raise ValueError(f"response id {rid} is not in the active set of responses!")

    specific_response_index(index)


def get_history() -> dict[str, list]:

    content = _read_file(_response_dir, get_cur_id(), RESPONSE_DEFAULT)

    if _should_strip_html():
        if _show_edbo_phrases:
            factorizations = [[]] + _current_eds_info['factorization']
        else:
            factorizations = [None]*len(content)

        for version, factorization in zip(content, factorizations):
            if "changes" in version and "content" in version["changes"] and version["changes"]["content"] is not None:
                version["changes"]["content"] = BeautifulSoup(version["changes"]["content"], 'lxml').get_text()

                if _show_edbo_phrases and len(factorization) > 0:
                    version["changes"]["content"] = _process_phrase_colors(version["changes"]["content"], factorization)

    elif _should_escape_html():
        for version in content:
            if "changes" in version and "content" in version["changes"] and version["changes"]["content"] is not None:
                version["changes"]["content"] = html.escape(version["changes"]["content"])

    timestamps = _process_time(content)
    hist = content

    out = {
        "history": hist,
        "edit_distances": get_current_eds(),
        "timestamps": timestamps,
        "format": "old"
    }

    return out


def _process_phrase_colors(text: str, factorization: list[int]):
    match_color = [' #85c1e9', ' #f9e79f', ' #abebc6']
    i, c = 0, 0
    old_text = text
    new_text = "<p>"
    for length in factorization:
        j = max(length, 1)
        if length == 0:
            color = ' #f1948a'
        else:
            color = match_color[c]
            c = (c + 1) % len(match_color)

        match = old_text[i:i + j]
        new_text += f"<span style='background-color:{color}'>{match}</span>"
        i += j
    return new_text + '</p>'


def _process_time(content: list) -> list:
    timestamps = []
    prev_ts = datetime.strptime(content[0]["timestamp"], "%Y-%m-%dT%H:%M:%S.%f%z")
    for version in content:
        if "timestamp" in version and version["timestamp"] is not None:
            cur_ts = datetime.strptime(version["timestamp"], "%Y-%m-%dT%H:%M:%S.%f%z")
            timestamps.append((cur_ts - prev_ts).total_seconds())
            prev_ts = cur_ts

    return timestamps


def _process_html(string: str):
    if _should_strip_html():
        return BeautifulSoup(string, 'lxml').get_text()

    if _should_escape_html():
        return html.escape(string)

    return string


def _should_strip_html():
    return _html_mode == HtmlModes.STRIP


def _should_escape_html():
    return _html_mode == HtmlModes.SHOW


def get_nr_responses() -> int:
    return len(_response_ids)


def get_num_versions() -> list[int]:
    if _response_ids is None or len(_response_ids) == 0:
    	return [0]
    else:
        num_versions_array = []
    
        for id in _response_ids:
            num_versions_array.append(_num_versions_tree[id[0]][id[1]][id[2]][id[3]])
    
        return num_versions_array

def get_all_max_edit_distances() -> list[int]:
    if _response_ids is None or len(_response_ids) == 0:
    	return [0]
    else:
        max_edit_distances_array = []
    
        for id in _response_ids:
            max_edit_distances_array.append(_edit_distance_tree[id[0]][id[1]][id[2]][id[3]])
    
        return max_edit_distances_array

def get_index():
    return _current_response_index


def set_html(val: str):
    """
    Set the html mode
    :param val: the new mode
    """
    global _html_mode
    _html_mode = val


def get_html() -> str:
    return _html_mode


def get_cur_id() -> list[int]:
    if _response_ids is None or len(_response_ids) == 0:
        return []
    return _response_ids[_current_response_index]


def set_active_set(ids: list[int|str]):
    global _response_ids

    if len(ids) == 0:
        new_response_ids = _get_all_leaves(_response_tree, [])
    else:
        ids = [int(i) for i in ids]
        new_response_ids = _find_all_response_ids(ids)

    # sort ids on their edit distance
    new_response_ids.sort(reverse=True,
                          key=lambda ids_list: _edit_distance_tree[ids_list[0]][ids_list[1]][ids_list[2]][ids_list[3]])

    reset_response_ids( new_response_ids )


def _find_all_response_ids(ids: list[int], tree: dict | list = None, index: int = 0) -> list[list[int]]:
    logger.info(f"Finding all responses for {ids}, current value of index is {index}.")

    if ids is None:
        return []

    if tree is None:
        tree = _response_tree

    # if index is outside the ids list, we want to get all leaves from that point
    if index == len(ids):
        return _get_all_leaves(tree, ids)

    # otherwise, walk one node down
    if ids[index] not in tree:
        traceback.print_exc()
        raise ValueError(f"Could not find id: {ids[index]}! Stopped finding all responses. Queried to find all response ids for {ids}")

    else:
        return _find_all_response_ids(ids, tree[ids[index]], index + 1)


def _get_all_leaves(tree: dict[int, dict | list] | list[int], prefix: list[int]) -> list[list[int]]:
    """
    Get all leaves in the tree

    :param tree: the relevant tree
    :param prefix: prefix of ids
    :return: a list of ids
    """
    if isinstance(tree, list):
        return [(prefix + [x]) for x in tree]

    elif isinstance(tree, dict):
        out = []
        for k, v in tree.items():
            out += _get_all_leaves(v, prefix + [k])

        return out

    else:
        raise TypeError(f"Unsupported type: {type(tree)}")


def reset_response_ids(new_ids: list[list[int]]):
    global _response_ids
    _response_ids = new_ids

    print('resetting response ids to a list of size ' + str(len(_response_ids)))

    if len(_response_ids) > 0:
        _update_current_index(0)
    else:
        _update_current_index(-1)


def get_current_eds() -> list[int]:
    if _current_eds_info is None:
        return []
    return _current_eds_info["edit_distances"]


def get_max_ed() -> int:
    if _current_eds_info is None:
        return 0
    return _current_eds_info["max"]


def get_tree() -> dict:
    return _response_tree


def get_names_tree() -> list:
    return [_names_tree, _names_ids_list]


ED_DEFAULT = {
                'factorization': [],
                'edit_distances': [0],
                'max': 0
             }

RESPONSE_DEFAULT = [
                        {
                            "timestamp": "2025-01-01T00:00:00.000+02:00",
                            "changes": {
                                            "content": None
                                        }
                        }
                    ]


def _read_file(root: Path, ids: list[int], default=None) -> dict | list:
    if len(ids) != 4:
        ValueError(f"ids was of unexpected length. Was {len(ids)}, expected 4.")

    path = root
    for i in ids:
        path = path / str(i)

    path = path.with_suffix(".pickle")

    if not path.exists():
        return default

    with open(path, 'rb') as file:
        return pickle.load(file)


def compute_ed(rel_path: Path):
    if _executor is None:
        logger.warning("No executor found. Skipping. "
                       "If this message is given at startup, then it can safely be ignored.")
        return

    _executor.submit(compute_edit_distances, 'improved', _response_dir, rel_path, _result_dir)


def test_all():
    responses = _get_all_leaves(_response_tree, [])

    found_all = True

    for ids in responses:
        path = _result_dir
        for i in ids:
            path = path / str(i)

        path = path.with_suffix(".pickle")

        if not path.exists():
            found_all = False
            compute_ed(path.relative_to(_result_dir))

    return found_all
