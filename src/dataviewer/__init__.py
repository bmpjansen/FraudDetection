from pathlib import Path

from flask_executor import Executor

from . import routes, responses


def init(response_dir: Path, results_dir: Path, user_dir: Path, ex: Executor):
    responses.init(response_dir, results_dir, user_dir, ex)