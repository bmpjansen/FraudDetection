import ctypes
import pickle
from os import makedirs
from pathlib import Path
import logging
from threading import Lock

from . import suffix_array_naive, suffix_array_improved, util


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


def compute_edit_distances_batch(algorithm: str, base_path: Path, response_paths: list, result_directory: Path) -> None:
    """
    Compute the edit distance for a batch of responses from the same (assignment_id, result_id).
    All snapshots are sorted by timestamp and processed together, but results are mapped back to individual questions.
    
    :param algorithm: the algorithm to use
    :param base_path: the root path of the data
    :param response_paths: list of dicts with 'base_path' and 'rel_file_path' keys
    :param result_directory: where to store the results
    """
    global n_running_jobs
    
    if not response_paths:
        logger.warning("Empty response_paths list, skipping batch")
        add_to_running_jobs(-1)
        return
    
    logger.info(f"Computing edit distance for batch of {len(response_paths)} responses")
    
    try:
        if algorithm != "improved":
            raise RuntimeError(f"Batch processing only supports 'improved' algorithm, got: {algorithm}")
        
        # Extract and sort all snapshots across all questions
        word, separation_indices, snapshot_metadata = util.extract_all_snapshots_sorted(
            response_paths, base_path, remove_html=True
        )
        
        if len(word) == 0:
            logger.warning("No snapshots found in batch, skipping")
            # Still write empty results for each question
            for response_info in response_paths:
                rel_path = Path(response_info['rel_file_path'])
                write_dir = (result_directory / rel_path.parent).resolve()
                makedirs(write_dir, exist_ok=True)
                with open((write_dir / rel_path.name).resolve(), 'wb') as file:
                    pickle.dump({
                        'factorization': [],
                        'edit_distances': [0],
                        'max': 0
                    }, file)
            add_to_running_jobs(-1)
            return
        
        # Compute LZ factorization
        try:
            factorization = suffix_array_improved.compute_suffix_array_from_word(word, separation_indices)
        except Exception as e:
            print(f"The factorization algorithm produced an error! Exception: {e}")
            raise e
        
        # Map results back to individual questions
        # Group snapshots by question path
        question_snapshots = {}
        for idx, metadata in enumerate(snapshot_metadata):
            question_path = metadata['question_path']
            if question_path not in question_snapshots:
                question_snapshots[question_path] = []
            question_snapshots[question_path].append({
                'global_index': idx,
                'snapshot_index': metadata['snapshot_index'],
                'factorization': factorization[idx] if idx < len(factorization) else []
            })
        
        # Write results for each question
        for response_info in response_paths:
            rel_path_str = Path(response_info['rel_file_path']).as_posix()  # Normalize for comparison
            rel_path = Path(response_info['rel_file_path'])
            
            # Get snapshots for this question
            if rel_path_str not in question_snapshots:
                # No snapshots for this question, write empty result
                question_factorizations = []
                question_edit_distances = [0]
            else:
                # Sort by snapshot_index to maintain original order
                question_snapshots_sorted = sorted(question_snapshots[rel_path_str], 
                                                  key=lambda x: x['snapshot_index'])
                question_factorizations = [s['factorization'] for s in question_snapshots_sorted]
                question_edit_distances = [len(f) for f in question_factorizations]
            
            write_dir = (result_directory / rel_path.parent).resolve()
            makedirs(write_dir, exist_ok=True)
            
            with open((write_dir / rel_path.name).resolve(), 'wb') as file:
                pickle.dump({
                    'factorization': question_factorizations,
                    'edit_distances': question_edit_distances,
                    'max': max(question_edit_distances + [0])
                }, file)
        
        logger.info(f"Completed batch of {len(response_paths)} responses")
        
    except Exception as e:
        print(f"An exception occurred while computing edit distance for batch!\n "
              f"Exception message: {e}")
        import traceback
        traceback.print_exc()
    
    add_to_running_jobs(-1)
    logger.info(f"Number of remaining jobs: {n_running_jobs}")