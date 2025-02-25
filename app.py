import argparse
import os
import sys
from datetime import datetime
from multiprocessing import Event, Queue
from pathlib import Path
import logging

from flask import Flask, jsonify, request
from flask_executor import Executor

import src.dataviewer.routes
from src import dataviewer
from src.ans_response_fetcher import AnsResponseFetcher

from src.editdistance import main as ed_manager

name = __name__
app = Flask(name)
executor = Executor(app)
app.register_blueprint(src.dataviewer.routes.dv_routes)

port = 5000
BASE_DIR = Path(__file__).resolve().parent


@app.route("/api/start_retrieval", methods=["POST"])
def start_retrieval():
    data = request.get_json()
    logger.info("Starting retrieval")

    stop_event = Event()
    job_queue = Queue()

    def retriever_task():
        response_fetcher = AnsResponseFetcher(data["API_KEY"], DELAY, LIMIT)
        response_fetcher.run(BASE_URL, data['ids'], BASE_DIR, responses_dir, None, job_queue)
        logger.info("Retrieval finished")
        stop_event.set()

    def computation_task():
        ed_manager.start(executor, result_dir, stop_event, job_queue, name)
        logger.info("All computation jobs started")

    executor.submit(retriever_task)
    executor.submit(computation_task)

    return jsonify({
        "status": "retrieval started",
    }), 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="Unified Response Viewer")
    parser.add_argument("-p", "--port", required=False, default=5000, type=int, help="The port to use.")
    parser.add_argument("-s", "--server", required=False,
                        default="https://ans.app/api/v2", help="The api server to use.")
    parser.add_argument("-d", "--delay", required=False, default=0.2, type=float,
                        help="The delay between api calls.")
    parser.add_argument("-pl", "--pagelimit", required=False, default=20, type=int,
                        help="The page size limit to use when using the ANS api.")
    parser.add_argument("--debug", required=False, default=False, action="store_true",
                        help="Will log more verbosely. For debug purposes.")

    args = parser.parse_args()

    # validate arguments
    port = args.port
    if port < 0:
        print(f"Invalid port: {port}.")
        exit(1)

    DELAY = args.delay
    if DELAY < 0:
        print(f"Delay should >= 0. Was: {DELAY}.")
        exit(1)

    LIMIT = args.pagelimit
    if not 0 < LIMIT <= 100:
        print(f"Invalid limit: {LIMIT}. Should be between 0 (excluded) and 100 (included).")
        exit(1)

    DEBUG = args.debug
    BASE_URL = args.server

    # setting up logger
    log_dir = BASE_DIR / 'logs'
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger()
    logging.basicConfig(filename=log_dir / f"{datetime.now().strftime('%Y%m%dT%H%M%S')}.log",
                        level=logging.DEBUG if DEBUG else logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    # setting directories
    responses_dir = (BASE_DIR / 'Data' / 'responses').resolve()
    result_dir = (BASE_DIR / 'Data' / 'results').resolve()
    user_dir = (BASE_DIR / 'Data' / 'user').resolve()

    logger.info(f"Starting Unified Response Viewer on port {port}, "
                f"with debug mode {'ON' if DEBUG else 'OFF'}."
                f"Delay of {DELAY} seconds."
                f"Page size limit is {LIMIT}."
                f"Server url is {BASE_URL}"
                )

    # initialize and start app
    dataviewer.init(responses_dir, result_dir, user_dir)

    try:
        app.run(debug=DEBUG, port=port)
    except KeyboardInterrupt:
        logger.info('Shutting down Unified Response Viewer.')



