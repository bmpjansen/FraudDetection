import logging
import os
import pickle
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread, Lock

from flask_executor import Executor
from numpy import max

from .algorithms.edit_distance import compute_edit_distances, add_to_running_jobs


# author: Valentijn van den Berg


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
    while True:
        try:
            new_job = job_queue.get(block=False)
        except Empty:
            if stop_event.is_set():
                break

            time.sleep(10)
            continue

        logger.debug(f"Got new job: {new_job['rel_file_path']}")

        # Submit the task to Flask-Executor
        add_to_running_jobs(1)
        executor.submit(compute_edit_distances, 'improved', new_job['base_path'], new_job['rel_file_path'], result_directory)


