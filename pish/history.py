""" history.py - functions that implement history


"""

import os
from collections import deque
from typing import Optional
from typing import Deque

def _delete_nth(d, n):
    """ Remove item from deque by index """
    d.rotate(-n)
    d.popleft()
    d.rotate(n)

def load_history_file(fname: str, size: int) -> Deque:
    """ Loads the history file into a deque object """
    if not os.path.exists(fname):
        return deque([], maxlen=size)
    try:
        with open(fname, "r", encoding="UTF-8") as fp:
            lines = fp.read().splitlines()
            fp.close()
    except IOError as e:
        print(f"Could not read history file {fname}: {e}")
    return deque(lines, maxlen=size)


def write_history_file(h_array: Deque, fname: str) -> None:
    """ Writes the current command to the history file """
    try:
        with open(fname, "w", encoding="UTF-8") as fp:
            for line in h_array:
                fp.write(line + '\n')
        fp.close()
    except IOError as e:
        print(f"Could not write to {fname}: {e}")


def del_history_entries(start: int, end: Optional[int], h_array: Deque, size: int) -> Deque:
    """ Given the `history -d` command, deletes the specified commands
    from the history array """

    if end is None:
        _delete_nth(h_array, start-1)
    else:
        # deque does not support slicing, so convert to list and back
        l = list(h_array)
        del l[start-1:end]
        h_array = deque(l, maxlen=size)

    return h_array


def print_history(lines_to_print: int, h_array: Deque) -> int:
    """Prints a numbered list of commands from history."""

    # Calculate the width needed for the line numbers
    total_lines = len(h_array)
    line_number_width = len(str(total_lines))

    line_count = 1
    if lines_to_print == 0:
        for line in h_array:
            print(f"{line_count:>{line_number_width}}  {line}")
            line_count += 1
    else:
        line_count = (len(h_array) - lines_to_print) + 1
        while lines_to_print > 0:
            print(f"{line_count:>{line_number_width}}  {h_array[len(h_array) - lines_to_print]}")
            lines_to_print -= 1
        #for line in h_array[-lines_to_print:]:
         #   print(f"{line_count:>{line_number_width}}  {line}")
            line_count += 1
    return 0
