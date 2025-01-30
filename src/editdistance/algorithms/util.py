import pickle
from pathlib import Path

from bs4 import BeautifulSoup


def extract_content(version_history: list[dict], remove_html: bool = True) -> tuple[str, list[int]]:
    word = ''
    separation_indices = []
    separator_generator = chinese_character_generator()

    for version in version_history:
        if ("changes" in version
                and "content" in version["changes"]
                and version["changes"]["content"] is not None):

            content = version["changes"]["content"]
            if remove_html:
                content = BeautifulSoup(content, "lxml").get_text()

            word += (content + next(separator_generator).decode('utf-8'))
            separation_indices.append(len(word) - 1)

    return word, separation_indices


def get_word_from_file(path: Path) -> tuple[str, list[int]]:
    with open(path, "rb") as file:
        return extract_content(pickle.load(file))


def get_phrases(snapshots: list[str], lz: list[list[int]]) -> list[list[str]]:
    """
    Construct a list of phrases from a list of snapshots and their lz compression.

    :param snapshots: The list of snapshots
    :param lz: the lz compression output
    :return: a list of containing the phrases of each snapshot
    """
    out = []
    for ls, snapshot in zip(lz, snapshots):
        cur = []

        for i in range(1, len(ls)):
            cur.append(snapshot[ls[i - 1]: ls[i]])

        out.append(cur)

    return out


def chinese_character_generator():
    """
    Generates Chinese character encoded in 'utf-8' as bytes
    """
    start = 0x4E00
    end = 0x9FFF
    for code_point in range(start, end + 1):
        yield chr(code_point).encode('utf-8')


def is_generated_chinese_character(c):
    """
    Check if the character c is a Chinese character in the range U+4E00 to U+9FFF.

    :param c: A single character (string of length 1)
    :return: True if c is a Chinese character in the generator's range, False otherwise
    """
    if len(c) != 1:
        raise ValueError(f"Input must be a single character. Got: {c}")

    code_point = ord(c)
    return 0x4E00 <= code_point <= 0x9FFF