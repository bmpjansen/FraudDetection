import ctypes
import pickle
from os import makedirs
from pathlib import Path
import logging
from threading import Lock

from . import suffix_array_naive, suffix_array_improved


# author: Valentijn van den Berg


def run_c_code(dll_name: str, first_string: str, second_string: str) -> int:
    base_dir = Path(__file__).resolve().parent.parent.parent

    if not dll_name.endswith(".dll"):
        dll_name += ".dll"

    full_path = base_dir / "libs" / dll_name

    # Load the shared library
    run_lib = ctypes.CDLL(str(full_path))
    run_func = getattr(run_lib, 'run')

    # Define the argument and return types
    run_lib.run.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    run_lib.run.restype = ctypes.c_int

    result = run_lib.run(first_string.encode('utf-8'), second_string.encode('utf-8'))

    return result


def lz77_naive_algorithm(pickle_file_path: Path) -> list[list[int]]:
    return suffix_array_naive.compute_suffix_array(pickle_file_path)


def lz77_improved_algorithm(pickle_file_path: Path) -> list[list[int]]:
    return suffix_array_improved.compute_suffix_array(pickle_file_path)


# Whether to use the python implementations or not
USE_PYTHON = True

alg_dict = {
    "naive": lz77_naive_algorithm,
    "improved": lz77_improved_algorithm
}


n_running_jobs = 0
lock = Lock()
logger = logging.getLogger()


def add_to_running_jobs(amount: int = 1):
    try:
        global n_running_jobs
        with lock:
            n_running_jobs += amount
    except RuntimeError as e:
        print(f"Error while adding to/removing from running_jobs! Exception: {e}")


def compute_edit_distances(algorithm: str, base_path: Path, rel_pickle_file_path: Path, result_directory: Path) -> None:
    """
    Compute the edit distance for a sequence of words.

    :param algorithm: the algorithm to use
    :param base_path: the root path of the data
    :param rel_pickle_file_path: the path to the pickle file relative to 'base_path'
    :param result_directory: where to store the results
    """
    global n_running_jobs

    logger.info(f"Computing edit distance for response {rel_pickle_file_path.stem}")

    try:
        if algorithm not in alg_dict:
            raise RuntimeError(f"Unknown algorithm: {algorithm}")

        try:
            factorization = alg_dict[algorithm](base_path / rel_pickle_file_path)
        
        except Exception as e:
            print(f"The factorization algorithm produced an error! The input file was determined via {base_path} and {rel_pickle_file_path}")
            raise e

        write_dir = (result_directory / rel_pickle_file_path.parent).resolve()
        makedirs(write_dir, exist_ok=True)

        try:
            ed = [len(x) for x in factorization]
           
        except Exception as e:
            ed = [0]
            print(f"An exception occurred when trying to list the factorization counts! Fall-back to [0]. Exception: {e}")

        with open((write_dir / rel_pickle_file_path.name).resolve(), 'wb') as file:
            pickle.dump({
                'factorization': factorization,
                'edit_distances': ed,
                'max': max(ed + [0])
            }, file)

    except Exception as e:
        print(f"An exception occurred while computing the edit distance for response {rel_pickle_file_path}!\n "
              f"Exception message: {e}")

    add_to_running_jobs(-1)

    logger.info(f"Completed response {rel_pickle_file_path.stem}. Number of remaining jobs: {n_running_jobs}")