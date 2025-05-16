import logging
import os

from flask import render_template, send_from_directory, jsonify, request, Blueprint

from src.dataviewer import responses

dv_routes = Blueprint('dv_routes', __name__)
logger = logging.getLogger(__name__)


@dv_routes.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(dv_routes.root_path, 'static'), filename)


@dv_routes.route('/user/<path:filename>')
def user_files(filename):
    return send_from_directory(os.path.join(dv_routes.root_path, 'user'), filename)


@dv_routes.route("/")
def index():
    return render_template("index.html")


def construct_info(max_ed: float = None,
                   rid: list[int] = None,
                   resp_index: int = None,
                   n_responses: int = None,
                   todo_html: str = None):

    if max_ed is None:
        max_ed = responses.get_max_ed()

    if rid is None:
        rid = responses.get_cur_id()

    if resp_index is None:
        resp_index = responses.get_index()

    if n_responses is None:
        n_responses = responses.get_nr_responses()

    if todo_html is None:
        todo_html = responses.get_html()

    num_versions = responses.get_num_versions()

    all_max_edit_distances = responses.get_all_max_edit_distances()

    return jsonify({
        "index": resp_index,
        "n_responses": n_responses,
        "rid": rid,
        "max_ed": int(max_ed),
        "html": todo_html,
        "num_versions": num_versions,
        "all_max_edit_distances": all_max_edit_distances
    })


@dv_routes.route("/api/reload", methods=["GET"])
def reload():
    try:
        responses.reinit()
        return jsonify({
            "status": "success"
        })
    except Exception as e:
        logger.error(e)
        return jsonify({"error": e.args}), 500


@dv_routes.route("/api/info", methods=["GET"])
def get_info():
    return construct_info(), 200


@dv_routes.route("/api/history", methods=["GET"])
def get_history():
    try:
        return responses.get_history(), 200
    except (FileNotFoundError, ValueError) as e:
        logger.error(e)
        return jsonify({"error": e.args}), 500


@dv_routes.route("/api/nextResponse", methods=["GET"])
def next_response():
    responses.next_response()
    return construct_info(), 200


@dv_routes.route("/api/previousResponse", methods=["GET"])
def previous_response():
    responses.previous_response()
    return construct_info(), 200


@dv_routes.route("/api/response/index/<i>", methods=["GET"])
def specific_response_index(i):
    try:
        responses.specific_response_index(int(i))
        return construct_info(), 200
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": e.args}), 500


@dv_routes.route("/api/response/id/<i>", methods=["GET"])
def specific_response_id(i):
    try:
        responses.specific_response_id(int(i))
        return construct_info(), 200
    except ValueError as e:
        logger.error(e)
        return jsonify({"error": e.args}), 500


@dv_routes.route("/api/striphtml", methods=["POST"])
def strip_html():
    data = request.get_json()
    responses.set_html(data["value"])
    return responses.get_history(), 200


@dv_routes.route("/api/id_tree", methods=["GET"])
def get_id_tree():
    return jsonify(responses.get_tree()), 200


@dv_routes.route("/api/names_tree", methods=["GET"])
def get_names_tree():
    return jsonify(responses.get_names_tree()), 200


@dv_routes.route("/api/set_active_set", methods=["POST"])
def set_active_set():
    data = request.get_json()
    try:
        logger.info(f"Setting active set to {data}")
        responses.set_active_set(data)
        return construct_info(), 200
    except (FileNotFoundError, ValueError) as e:
        logger.error(e)
        return jsonify({"error": e.args}), 500


@dv_routes.route("/api/recheck", methods=["GET"])
def recheck():
    out = responses.test_all()
    return jsonify({
        "status": out,
    }), 200

