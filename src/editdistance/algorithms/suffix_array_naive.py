import logging
from pathlib import Path

from . import util, lz77


def compute_lcp(str1: str, str2: str) -> int:
    """
    Compute the LCP between two strings.

    :param str1: string 1
    :param str2: string 2
    :return: the longest common prefix between str1 and str2.
    """
    i = 0
    for s, t in zip(str1, str2):
        if s != t:
            break
        i += 1

    return i


def naive_suffix_array(w: str, n: int) -> tuple[list[int], list[int]]:
    sa = list(range(n))
    sa.sort(key=lambda k: w[k:])  # Sort indices by the suffix starting at each index

    lcp = [0]

    for i in range(1, n):
        prev_index = sa[i - 1]
        index = sa[i]
        lcp.append( compute_lcp(w[prev_index:], w[index:]) )

    return sa, lcp


def compute_suffix_array(pickle_file_path: Path) -> list[list[int]]:
    """
    Compute the lz compression of a list of snapshots.
    :param pickle_file_path: the path to the pickled list or dictionary containing the snapshots
    :return: the Lempel-Ziv compression of the concentrated snapshots with separating characters.
             Example: snapshots = [A, B, C] will be concatenated as A$1B$2C,
             where $1 and $2 are unique separation characters.
    """

    logger = logging.getLogger()
    logger.info(f"Started lz77 (naive) with {pickle_file_path.stem}")

    word, separation_indices = util.get_word_from_file(pickle_file_path)

    n = len(word)
    sa, lcp = naive_suffix_array(word, n)

    del word

    lpf = lz77.compute_lpf(sa, lcp, n, in_place=True)

    lz = lz77.compute_lz(lpf, n, separation_indices)

    logger.info(f"Completed lz77 with {pickle_file_path.stem}")

    return lz

