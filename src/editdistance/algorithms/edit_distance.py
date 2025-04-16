import ctypes
import pickle
from os import makedirs
from pathlib import Path
from queue import Queue

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


def compute_edit_distances(algorithm: str, base_path: Path, rel_pickle_file_path: Path, result_directory: Path) -> None:
    """
    Compute the edit distance for a sequence of words.

    :param algorithm: the algorithm to use
    :param base_path: the root path of the data
    :param rel_pickle_file_path: the path to the pickle file relative to 'base_path'
    :param result_directory: where to store the results
    """
    if algorithm not in alg_dict:
        raise RuntimeError(f"Unknown algorithm: {algorithm}")

    factorization = alg_dict[algorithm](base_path / rel_pickle_file_path)

    write_dir = (result_directory / rel_pickle_file_path.parent).resolve()
    makedirs(write_dir, exist_ok=True)

    ed = [len(x) for x in factorization]

    with open((write_dir / rel_pickle_file_path.name).resolve(), 'wb') as file:
        pickle.dump({
            'factorization': factorization,
            'edit_distances': ed,
            'max': max(ed + [0])
        }, file)


