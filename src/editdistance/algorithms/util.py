import pickle
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

from bs4 import BeautifulSoup


def extract_content(version_history: list[dict], remove_html: bool = True) -> tuple[str, list[int], list[bool]]:
    word = ''
    separation_indices = []
    artificial_flags = []
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
            artificial_flags.append(version.get("is_artificial", False))

    return word, separation_indices, artificial_flags


def get_word_from_file(path: Path) -> tuple[str, list[int], list[bool]]:
    with open(path, "rb") as file:
        return extract_content(pickle.load(file))


def extract_snapshot_with_metadata(version: dict, remove_html: bool = True) -> tuple[str, str | None, bool]:
    """
    Extract content from a single snapshot version.
    
    :param version: A single version dict from version history
    :param remove_html: Whether to remove HTML tags
    :return: Tuple of (content, timestamp, is_artificial)
    """
    if ("changes" in version
            and "content" in version["changes"]
            and version["changes"]["content"] is not None):

        content = version["changes"]["content"]
        if remove_html:
            content = BeautifulSoup(content, "lxml").get_text()
        
        timestamp = version.get("timestamp") if "timestamp" in version else None
        is_artificial = version.get("is_artificial", False)
        return content, timestamp, is_artificial
    
    return "", None, False


def extract_all_snapshots_sorted(response_paths: List[Dict], base_path: Path, remove_html: bool = True) -> Tuple[str, List[int], List[Dict]]:
    """
    Extract all snapshots from multiple response files, sort by timestamp, and track metadata.
    
    :param response_paths: List of dicts with 'base_path' and 'rel_file_path' keys
    :param base_path: Base path for resolving relative paths
    :param remove_html: Whether to remove HTML tags
    :return: Tuple of (concatenated_word, separation_indices, snapshot_metadata)
             where snapshot_metadata is a list of dicts with keys: 'question_path', 'snapshot_index', 'timestamp', 'is_artificial'
    """
    all_snapshots = []
    
    # Load all snapshots with metadata
    for response_info in response_paths:
        rel_path_obj = Path(response_info['rel_file_path'])
        rel_path_str = rel_path_obj.as_posix()  # Normalize to string for consistent comparison
        full_path = base_path / rel_path_obj
        
        try:
            with open(full_path, "rb") as file:
                version_history = pickle.load(file)
            
            # Extract each snapshot with its metadata
            for snapshot_idx, version in enumerate(version_history):
                content, timestamp, is_artificial = extract_snapshot_with_metadata(version, remove_html)
                if content:  # Only add non-empty snapshots
                    all_snapshots.append({
                        'content': content,
                        'timestamp': timestamp,
                        'is_artificial': is_artificial,
                        'question_path': rel_path_str,  # Store as normalized string
                        'snapshot_index': snapshot_idx,
                        'version': version  # Keep original for reference
                    })
        except Exception as e:
            print(f"Error loading file {full_path}: {e}")
            continue
    
    # Sort by timestamp
    def get_timestamp_key(snapshot):
        ts = snapshot['timestamp']
        if ts is None:
            return datetime.max  # Put snapshots without timestamps at the end, should not happen
        try:
            # Use fromisoformat for ISO 8601 format (standard ANS API format)
            # Handles formats like: 2025-01-01T12:00:00.000000+00:00 or 2025-01-01T12:00:00+00:00
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # If parsing fails, put at the end 
            print(f"Timestamp parsing failed for {ts}.")
            return datetime.max
    
    all_snapshots.sort(key=get_timestamp_key)
    
    # Concatenate sorted snapshots
    word = ''
    separation_indices = []
    separator_generator = chinese_character_generator()
    snapshot_metadata = []
    
    for snapshot in all_snapshots:
        content = snapshot['content']
        word += (content + next(separator_generator).decode('utf-8'))
        separation_indices.append(len(word) - 1)
        snapshot_metadata.append({
            'question_path': snapshot['question_path'],
            'snapshot_index': snapshot['snapshot_index'],
            'timestamp': snapshot['timestamp'],
            'is_artificial': snapshot['is_artificial']
        })
    
    return word, separation_indices, snapshot_metadata


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