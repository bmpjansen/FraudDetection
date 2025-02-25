import logging
import os
import pickle
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread, Lock

from flask_executor import Executor
from numpy import max

from .algorithms.edit_distance import compute_edit_distances


# author: Valentijn van den Berg

# _lock = Lock()
# _n_running_jobs = 0
# _writer_stop_event = Event()
#
#
# def writing_loop(result_directory: Path, queue: Queue, logger_name: str):
#     """
#     Will wait for items in queue and write them to result_directory as pickle files.
#
#     :param result_directory: the result directory.
#     :param queue: the queue to take items from.
#     :param logger_name: the name of the logger.
#     """
#     global _n_running_jobs
#
#     os.makedirs(result_directory, exist_ok=True)
#     logger = logging.getLogger(logger_name)
#
#     # Loop as long as the stop_event has not been set
#     # or, if it has been set, wait for all running tasks to be finished
#     while True:
#         try:
#             new_job = queue.get(block=False)
#         except Empty:
#             with _lock:
#                 if _writer_stop_event.is_set() and _n_running_jobs <= 0:
#                     break
#
#             time.sleep(10)
#             continue
#
#
#
#         with _lock:
#             _n_running_jobs -= 1
#
#     logger.info("All computation jobs finished")
#
#
# write_thread = None
# write_queue = Queue()


def start(executor: Executor, result_directory: Path, stop_event: Event, job_queue: Queue, logger_name: str):
    """
    Main computation loop

    :param executor: the executor to submit tasks to.
    :param result_directory: where to write the results.
    :param stop_event: event when no new items will be written to the queue.
    :param job_queue: queue to take items from.
    :param logger_name: the name of the logger to use.
    :return:
    """
    if job_queue is None:
        raise ValueError("job_queue cannot be None")

    logger = logging.getLogger(logger_name)
    # global _n_running_jobs

    # Start the writing thread
    # global write_thread
    # if write_thread is None or not write_thread.is_alive():
    #     write_thread = Thread(target=writing_loop, args=(result_directory, write_queue, logger_name), daemon=True)
    #     write_thread.start()

    logger.info(f"Entering computation loop.")

    # Loop as long as the stop_event has not been set
    # or, if it has been set, finish all the remaining items in the queue
    while True :
        try:
            new_job = job_queue.get(block=False)
        except Empty:
            if stop_event.is_set():
                break

            time.sleep(10)
            continue

        logger.debug(f"Got new job: {new_job['rel_file_path']}")

        # Submit the task to Flask-Executor
        executor.submit(compute_edit_distances, 'improved', new_job['base_path'], new_job['rel_file_path'], result_directory)

    #     with _lock:
    #         _n_running_jobs += 1
    #
    # _writer_stop_event.set()

