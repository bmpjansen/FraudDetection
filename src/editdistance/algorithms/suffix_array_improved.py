import logging
from pathlib import Path

from . import util, lz77


def make_ranks(substr_rank, rank, n) -> list[int]:
    r = 0
    rank[substr_rank[0][2]] = r

    for i in range(1, n):
        if substr_rank[i][0] != substr_rank[i - 1][0] or \
                substr_rank[i][1] != substr_rank[i - 1][1]:
            r += 1

        rank[substr_rank[i][2]] = r

    return rank


def improved_suffix_array(word: str, n: int):
    # [left, right, index]
    substr_rank: list[list[int]] = []
    rank: list[int] = [-1] * n
    sa: list[int] = []

    for i in range(n):
        substr_rank.append(
            [
                ord(word[i]),
                ord(word[i + 1]) if i + 1 < n else 0,
                i
            ]
        )

    substr_rank.sort(key=(lambda x: (x[0], x[1])))

    l = 2
    while l < n:
        rank = make_ranks(substr_rank, rank, n)

        for i in range(n):
            substr_rank[i][0] = rank[i]
            substr_rank[i][1] = rank[i + l] if i + l < n else 0
            substr_rank[i][2] = i

        substr_rank.sort(key=(lambda x: (x[0], x[1])))

        l *= 2

    for _, _, index in substr_rank:
        sa.append(index)

    return sa


def compute_lcp(word, sa, n):
    rank = [-1] * n
    for i in range(n):
        rank[sa[i]] = i

    lcp = [-1] * n
    lcp[0] = 0
    l = 0

    for i in range(n):
        j = sa[rank[i] - 1]
        m = max(i, j)
        while m + l < n and word[i + l] == word[j + l]:
            l += 1
        lcp[rank[i]] = l
        if l > 0:
            l = l - 1

    return lcp


def compute_suffix_array(pickle_file_path: Path) -> list[list[int]]:
    """
    Compute the lz compression of a list of snapshots.
    :param pickle_file_path: the path to the pickled list or dictionary containing the snapshots
    :return: the Lempel-Ziv compression of the concentrated snapshots with separating characters.
             Example: snapshots = [A, B, C] will be concatenated as A$1B$2C,
             where $1 and $2 are unique separation characters.
    """

    logger = logging.getLogger()
    logger.info(f"Started lz77 (improved) with {pickle_file_path.stem}")

    word, separation_indices = util.get_word_from_file(pickle_file_path)
    n = len(word)

    if n == 0:
        logger.info(f"Completed lz77 with {pickle_file_path.stem}")
        return []

    sa = improved_suffix_array(word, n)
    lcp = compute_lcp(word, sa, n)

    del word

    lpf = lz77.compute_lpf(sa, lcp, n, in_place=True)

    lz = lz77.compute_lz(lpf, n, separation_indices)

    logger.info(f"Completed lz77 with {pickle_file_path.stem}")

    return lz

