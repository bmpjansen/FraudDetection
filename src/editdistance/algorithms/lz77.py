from collections import deque
from copy import deepcopy


def compute_lpf(sa: list[int], lcp: list[int], n: int, in_place: bool = False):
    """
    Compute the longest previous factor from the suffix array and longest common prefix array.

    :param sa: the suffix array
    :param lcp: the longest common prefix array.
    :param n: the length of the word
    :param in_place: whether the sa and lcp array should be modified. If False, copies will be made.
    :return: the longest previous factor array.
    """
    if not in_place:
        sa = deepcopy(sa)
        lcp = deepcopy(lcp)

    sa[n - 1] = -1
    lcp[n - 1] = 0
    lpf = [-1] * n

    stack = deque()
    stack.append(0)

    for i in range(n):
        while len(stack) > 0 and (sa[i] < sa[stack[-1]] or (sa[i] > sa[stack[-1]] and lcp[i] <= lcp[stack[-1]])):
            top = stack[-1]

            if sa[i] < sa[top]:
                lpf[sa[top]] = max(lcp[top], lcp[i])
                lcp[i] = min(lcp[top], lcp[i])
            else:
                lpf[sa[top]] = lcp[top]
            stack.pop()

        if i < n - 1:
            stack.append(i)

    return lpf


def compute_lz(lpf: list[int], n: int, separation_indices: list[int]) -> list[list[int]]:
    """
    Compute the Lempel-Ziv factorization of 'word' with the longest previous factor array.

    :param lpf: the longest previous factor array.
    :param n: the length of word
    :param separation_indices: the indices of the separation characters.
    :return: the lz factorization of the original word.
    """
    lz = [[]]
    prev_index = 0

    while prev_index < n - 1:
        delta = max(1, lpf[prev_index])
        current_index = prev_index + delta

        # if a chinese character is reached, begin a new list
        if delta == 1 and prev_index in separation_indices:
            lz.append([])

        # otherwise add delta to the list
        else:
            lz[-1].append(delta)

        prev_index = current_index

    return lz

