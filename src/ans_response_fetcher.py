import pickle
from pathlib import Path
from queue import Queue
from threading import Event

import requests
import os
import time
import logging

logger = logging.getLogger()


def read_api_key(file_path='api_key.txt') -> str | None:
    """
    Read the api key from a file named 'api_key.txt'.
    """
    return 'abcdefg'
    # try:
    #     with open(file_path, 'r') as file:
    #         return file.read().strip()
    # except (FileNotFoundError, PermissionError, OSError) as e:
    #     logger.warning(f"An exception was thrown while retrieving the API key: {e}")
    #     return None


def unpack_ids(ids: list[int]) -> tuple[int, int | None, int | None, int | None]:
    """
    Returns a shallow copy of ids with exactly four elements.
    If ids contains less than four elements then the remaining space is filled with Nones.
    """
    if len(ids) < 1 or len(ids) > 4:
        raise ValueError(f"the length of the ids list is outside the allowed range [1,4]. It was {len(ids)}.")

    out = [None, None, None, None]
    for i in range(0, len(ids)):
        out[i] = ids[i]
    return out


def get_error_path(ids: list | tuple):
    """
    Construct the id path the error occurred at
    """
    assignment_id, result_id, submission_id, response_id = unpack_ids(ids)

    path = str(assignment_id)
    if result_id is not None:
        path += f" -> {result_id}"

    if submission_id is not None:
        path += f" -> {submission_id}"

    if response_id is not None:
        path += f" -> {response_id}"

    return path


def print_http_error_message(e: requests.HTTPError | requests.exceptions.HTTPError, url: str, ids: list | tuple):
    """
    Print an error message to the terminal when a HTTP error was raised
    """
    path = get_error_path(ids)

    try:
        msg = e.response.json()['error']
        extra = ""
    except:
        msg = "For some reason (see below)."
        try:
            extra = e.response.json() + '\n'
        except:
            extra = "reason unknown."

    logger.error(f"HTTP Error: {e.response.status_code} -> {msg}.\n"
                 f"    while fetching '{url}'.\n"
                 f"    The path was: '{path}'.\n"
                 f"    {extra}")

    return path


def print_other_error_message(e: Exception, url: str, ids: list | tuple):
    """
    Print an error message to the terminal when some Exception was raised
    """
    path = get_error_path(ids)
    logger.error(f"\n[ERROR] Exception was raised while fetching {url}.\n"
                 f"    {e.with_traceback(None)}\n"
                 f"    The path was: '{path}'.")

    return path


class AnsResponseFetcher:
    """
    AnsResponseFetcher is used to fetch Responses from ANS.
    The ANS api can be found at https://ans.app/api/docs/index.html.
    """

    def __init__(self, api_key: str, delay: float = 0.2, limit: int = 20):
        """
        Constructor.
        :param api_key: your API key for the ANS api
        :param delay: the delay in seconds between each request
        :param limit: the page limit used by the ANS api
        """
        self.last_request_time = 0
        self.LIMIT = limit
        self.DELAY = delay
        self.prefices = ["assignment", "results", "submissions", "response"]
        self.request_header = {
            'Authorization': f"Bearer {api_key}"
        }

    def _write(self, directory: Path, content: dict | list, ids: list, encoding: str = 'utf-8') -> tuple[Path, Path]:
        """
        Write 'content' to a file located in 'directory'.

        :param directory: the directory the file is located in
        :param content: the content that will be written to file
        :param ids: the path of ids that let to this point (assignment, result, submission, response)
        :param encoding: the string encoding to use. Default = utf-8

        :return: the path of the written file
        """
        file_name = f"{ids[-1]}"

        os.makedirs(directory, exist_ok=True)
        pickle_full_path = directory / f"{file_name}.pickle"

        # Get the current content of the file if it exists and append the new content
        if pickle_full_path.exists():
            with open(pickle_full_path, 'rb') as file:
                previous: list | dict = pickle.load(file)

            if isinstance(previous, list) and isinstance(content, list):
                previous.extend(content)
                content = previous

            elif isinstance(previous, dict) and isinstance(content, dict):
                for key, value in content.items():
                    if key in previous:
                        previous[key] += value
                    else:
                        previous[key] = value

                content = previous

            else:
                raise ValueError(f"Mismatched or unexpected types of previous ({type(previous)}) "
                                 f"and new content ({type(content)}) while writing output."
                                 f"Make sure both have the same type and are of type dict or type list.")

        # write to the pickle file
        with open(pickle_full_path, 'wb') as file:
            pickle.dump(content, file, protocol=pickle.HIGHEST_PROTOCOL)

        base_path = directory.parent.parent.parent
        return base_path, pickle_full_path.relative_to(base_path)

    def _wait_if_required(self):
        """
        Sleep til 'self.DELAY' time has passed since 'self.last_request_time'
        """
        time_diff = time.time() - self.last_request_time
        if time_diff < self.DELAY:
            time_to_sleep = self.DELAY - time_diff
            logger.debug(f"Sleeping for {time_to_sleep} seconds...")
            time.sleep(time_to_sleep)

    def _fetch_and_write(self, url: str, path: str | Path, header: dict, ids: list, has_pages: bool = False,
                         get_ids: bool = True, interested_in: str = None,
                         job_queue: Queue = None, should_queue: bool = False, should_write: bool = False,
                         stop_event: Event = None) \
            -> tuple[bool, list | str, int, int]:
        """
        Send an HTTP(S) request to 'url' with 'header' and saves the result at 'path'

        :param url: the endpoint to fetch.
        :param path: the directory where the result will be written.
        :param header: the header to send with the request.
        :param ids: the ordered list of ids that lead to this point (assignment, result, submission, response).
        :param has_pages: whether this endpoint uses pagination.
        :param get_ids: whether a list of ids should be constructed and outputted from the received object.
        :param interested_in: used as a key before obtaining the list of ids to output.
        :param should_queue: whether to put the output in the job_queue
        :param should_write: whether to write the output to the file
        :param stop_event: the event to stop sending the request

        :return: Tuple (successful, ids, exercise_id, question_id), where
                 | *successful*: whether the fetching and writing was successful.
                 | *ids*: list of ids obtained from the fetched json.
                 | *exercise_id*: if the received object contained an exercise_id, it will be returned here. Otherwise, returns -1.
                 | *question_id*: if the received object contained a question_id, it will be returned here. Otherwise, returns -1.
        """
        if stop_event is not None and stop_event.is_set():
            return False, [], -1, -1

        try:
            nr_of_pages = 1000000
            cur_page = 1

            return_ids = []

            current_exercise = -1
            current_question = -1

            while cur_page <= nr_of_pages:

                self._wait_if_required()

                # send request
                if has_pages:
                    full_url = f"{url}?limit={self.LIMIT}&page={cur_page}"
                else:
                    full_url = url
                response = requests.get(full_url, headers=header)

                self.last_request_time = time.time()

                # if we receive HTTP 429 (Too many requests), wait before retrying
                if response.status_code == 429:
                    logger.warning("Got back HTTP 429; sleeping for 30 seconds...")
                    time.sleep(30)
                    continue

                response.raise_for_status()

                # update total number of pages
                resp_header = response.headers
                if has_pages:
                    nr_of_pages = int(resp_header["Total-Pages"])
                else:
                    nr_of_pages = 1

                if has_pages and cur_page != int(resp_header["Current-Page"]):
                    raise ValueError(
                        f"The fetched page is different from the one expected! (expected: {cur_page}, "
                        f"instead got: {int(resp_header['Current-Page'])})")

                # get the response
                resp_json = response.json()

                # check for odd responses
                if resp_json is None:
                    logger.warning(f"Got back a None with {url}.")
                    return []
                elif len(resp_json) <= 0:
                    logger.warning(f"Got back an empty json object with {url}.")
                    return []

                # extract the ids that we are interested in
                if get_ids:
                    if interested_in is None:
                        return_ids += [x["id"] for x in resp_json]
                    else:
                        return_ids += [x["id"] for x in resp_json[interested_in]]

                try:
                    current_exercise = resp_json["exercise_id"]
                    current_question = resp_json["question_id"]
                except:
                    pass

                # add result id to json
                if len(ids) > 2:
                    if isinstance(resp_json, list) and len(resp_json) > 0:
                        resp_json[0]["result_id"] = ids[1]

                # write to file
                if should_write or should_queue:
                    base_path, rel_path = self._write(path, resp_json, ids)

                cur_page += 1

            if should_queue:
                if job_queue is None:
                    raise ValueError("Job queue is None.")

                job_queue.put({
                    'base_path': base_path,
                    'rel_file_path': rel_path
                })

                logger.info(f"Added {rel_path} to queue.")

        except (requests.HTTPError, requests.exceptions.HTTPError) as e:
            path = print_http_error_message(e, url, ids)
            return False, path, -1, -1
        except Exception as e:
            path = print_other_error_message(e, url, ids)
            return False, path, -1, -1

        return True, return_ids, current_exercise, current_question

    def _main_loops(self, base_url: str,
                    assignment_ids: list[int] | tuple[int],
                    job_queue: Queue,
                    stop_event: Event = None) -> tuple[int, list[str]]:
        """
        Get all responses that are part of an assignment in 'assignment_ids' from the api at 'base_url'

        :param base_url: the url of the api to query
        :param assignment_ids: list of assignment ids to get
        :param job_queue: the queue to put the responses on after they are retrieved
        :param stop_event: the event to stop getting responses

        :return: Tuple (nr_responses_retrieved, failed), where
                 | *nr_responses_retrieved*: the total of number of responses that were received successfully.
                 | *failed*: a list of strings containing information on the queries that failed.
        """
        nr_responses_retrieved = 0
        failed = []

        if stop_event is None:
            stop_event = Event()

        try:
            # Get the info from the api
            for assignment_id in assignment_ids:
                if stop_event.is_set():
                    break

                logger.info(f"--- Starting retrieval of assignment {assignment_id} ---")

                url = f"{base_url}/assignments/{assignment_id}/results"
                was_successful, result_ids, _, _ = self._fetch_and_write(url, self.assignment_path, self.request_header,
                                                                         [assignment_id], has_pages=True)

                if not was_successful:
                    failed.append(result_ids)
                    continue
                logger.info(f"Retrieved assignment {assignment_id}.")

                for result_id in result_ids:
                    if stop_event.is_set():
                        break

                    url = f"{base_url}/results/{result_id}"
                    was_successful, submission_ids, _, _ = self._fetch_and_write(url, self.result_path,
                                                                                 self.request_header,
                                                                                 [assignment_id, result_id],
                                                                                 interested_in="submissions")

                    if not was_successful:
                        failed.append(submission_ids)
                        continue
                    logger.info(f"   Retrieved result {result_id}.")

                    for submission_id in submission_ids:
                        if stop_event.is_set():
                            break

                        url = f"{base_url}/submissions/{submission_id}"
                        was_successful, response_ids, current_exercise, current_question = (
                            self._fetch_and_write(url,
                                                  self.submission_path,
                                                  self.request_header,
                                                  [
                                                      assignment_id,
                                                      result_id,
                                                      submission_id
                                                  ],
                                                  interested_in="responses")
                        )
                        response_path = self.base_response_path.joinpath(
                            f"{assignment_id}/{current_exercise}/{current_question}")

                        if not was_successful:
                            failed.append(response_ids)
                            continue
                        logger.info(f"      Retrieved submission {submission_id}.")

                        for response_id in response_ids:
                            if stop_event.is_set():
                                break

                            url = f"{base_url}/logs/responses/{response_id}"
                            was_successful, response, _, _ = self._fetch_and_write(url,
                                                                                   response_path,
                                                                                   self.request_header,
                                                                                   [assignment_id, result_id,
                                                                                    submission_id, response_id],
                                                                                   has_pages=False,
                                                                                   get_ids=False,
                                                                                   job_queue=job_queue,
                                                                                   should_queue=True,
                                                                                   should_write=True)

                            if not was_successful:
                                failed.append(response)
                                continue

                            nr_responses_retrieved += 1
                            logger.info(f"         Retrieved response {response_id}.")

                logger.info(f"--- Finished assignment {assignment_id} ---")
        except KeyboardInterrupt:
            logger.info("Interrupted!")

        return nr_responses_retrieved, failed

    def _setup_output_dirs(self,
                           base_out_dir: Path | str,
                           paths: list[Path | str] | tuple[Path | str],
                           mkdirs: bool = True) -> None:
        """
        Sets the output directories in self and creates the directories if they do not exist.

        Parameters
        ------------
        base_out_dir : The root output directory. Default: './out'.
        paths : The relative paths, w.r.t base_out_dir, of the different types of outputs.
                Should be ordered as: [assignments, results, submissions, response].
                Default: ['./other/assignments', './other/results', './other/submissions', '.']
        """

        # set the base output dir
        if base_out_dir is None:
            base_out_dir = Path("./out").resolve()
        elif not isinstance(base_out_dir, Path):
            base_out_dir = Path(base_out_dir).resolve()

        # if no paths list is given, apply the default paths
        if paths is None:
            other_out_dir = base_out_dir.joinpath('other')
            self.assignment_path = other_out_dir.joinpath('assignments').resolve()
            self.result_path = other_out_dir.joinpath('results').resolve()
            self.submission_path = other_out_dir.joinpath('submissions').resolve()
            self.base_response_path = base_out_dir.resolve()

        # otherwise apply the given paths
        else:
            if len(paths) != 4:
                raise ValueError("'paths' list should have length 4. "
                                 "If you wish to use the default paths pass 'None' for the paths parameter.")

            self.assignment_path = base_out_dir.joinpath(paths[0]).resolve()
            self.result_path = base_out_dir.joinpath(paths[1]).resolve()
            self.submission_path = base_out_dir.joinpath(paths[2]).resolve()
            self.base_response_path = base_out_dir.joinpath(paths[3]).resolve()

        if mkdirs:
            # create the directories if they do not exist already
            os.makedirs(self.assignment_path, exist_ok=True)
            os.makedirs(self.result_path, exist_ok=True)
            os.makedirs(self.submission_path, exist_ok=True)
            os.makedirs(self.base_response_path, exist_ok=True)

            if not self.assignment_path.is_dir():
                raise ValueError(f"assignment path is not pointing to a valid directory: {self.assignment_path}")

            if not self.result_path.is_dir():
                raise ValueError(f"result path is not pointing to a valid directory: {self.result_path}")

            if not self.submission_path.is_dir():
                raise ValueError(f"submission path is not pointing to a valid directory: {self.submission_path}")

            if not self.base_response_path.is_dir():
                raise ValueError(f"response path is not pointing to a valid directory: {self.base_response_path}")

        logger.info('##################################################')
        logger.info("---- Output directories ----")
        logger.info(f"Assignments: {self.assignment_path}")
        logger.info(f"Results: {self.result_path}")
        logger.info(f"Submissions: {self.submission_path}")
        logger.info(f"Responses: {self.base_response_path}")
        logger.info('##################################################')

    def run(self,
            base_url: str = "https://ans.app/api/v2",
            assignment_ids: list[int] = None,
            base_dir: Path | str = None,
            base_out_dir: Path | str = "./out",
            paths: list[Path | str] | tuple[Path | str] = None,
            job_queue: Queue = None) -> None:
        """
        Query the 'base_url' endpoints for the all responses of the assignments in 'ids'

        :param base_url: base url of the endpoints to query
        :param assignment_ids: a list of assignment ids to query
        :param base_dir: base directory
        :param base_out_dir: The root output directory. Default: 'base_dir/out'.
        :param paths: The relative paths, w.r.t base_out_dir, of the different types of outputs.
                Should be ordered as: [assignments, results, submissions, responses].
                Default: ['./other/assignments', './other/results', './other/submissions', '.']
        :param job_queue: The job queue to use
        """
        if job_queue is None:
            raise ValueError("Job queue is None.")

        # resolve paths
        base_dir = Path(base_dir).resolve()
        base_out_dir = Path(base_out_dir)
        if not base_out_dir.is_absolute():
            base_out_dir = (base_dir / base_out_dir).resolve()

        nr_responses_retrieved, failed = 0, []
        try:
            # setup directories
            self._setup_output_dirs(base_out_dir, paths, False)

            # fetch the responses
            nr_responses_retrieved, failed = self._main_loops(base_url=base_url,
                                                              assignment_ids=assignment_ids,
                                                              job_queue=job_queue)
        except Exception as e:
            logger.error(e.with_traceback(None))

        # print a summary to the terminal
        logger.info('')
        logger.info(f"Successfully retrieved {nr_responses_retrieved} responses.")
        logger.info(f"Failed {len(failed)} requests")
        for fail in failed:
            logger.info(f"    * {fail}")
        logger.info('')

