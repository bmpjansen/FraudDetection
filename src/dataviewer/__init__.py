from pathlib import Path

from . import routes, responses


def init(response_dir: Path, results_dir: Path, user_dir: Path):
    responses.init(response_dir, results_dir, user_dir)