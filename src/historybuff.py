""" historybuff.py """

import os
from typing import Optional

class HistoryBuff():
    """ HistoryBuff()

        A datatype that implements a shell history buffer, and the methods
        for acting upon it.
    """
    def __init__(self, buffsize: int, histfile: str):
        self.buffsize = buffsize
        self.histfile = histfile
        self.buff = []

    def __len__(self) -> int:
        return len(self.buff)

    def __repr__(self) -> str:
        return f"HistoryBuff(buffsize={self.buffsize})"

    def __str__(self) -> None:
        for line in self.buff:
            print(line)

    def load_from_file(self, fname: str) -> bool:
        """ Loads a history file into the buffer """
        if not os.path.exists(fname):
            print(f"HISTFILE: {fname} not found")
            return False
        try:
            with open(fname, "r", encoding="UTF-8") as fp:
                lines = fp.read().splitlines()
                fp.close()
                # Truncate lines to buffsize
                if len(lines) > self.buffsize:
                    lines = lines[-self.buffsize:]
                for line in lines:
                    self.buff.append(line)
        except IOError as e:
            print(f"Could not read history file {fname}: {e}")
            return False
        return True

    def write_to_file(self, fname: str) -> bool:
        """ Writes the current history buffer to HISTFILE """
        try:
            with open(fname, "w", encoding="UTF-8") as fp:
                for line in self.buff:
                    fp.write(line + '\n')
            fp.close()
            return True
        except IOError as e:
            print(f"Could not write to {fname}: {e}")
            return False

    def append(self, item: str) -> None:
        """ Pop the first item and append the new if
            at capacity, else just append the new """
        if len(self.buff) >= self.buffsize:
            self.buff.pop(0)
        self.buff.append(item)

    def clear(self) -> None:
        self.buff = []

    # def getn(self, n: int, index: int = 0) -> list[Any]:
    #     if (index + n) > len(self.buff):
    #         return self.__getitem__(slice(index,index+n))
    #     return self.buff[index:index+n]

    def print_buff(self, lines_to_print: int) -> None:
        """Prints a numbered list of commands from history."""

        # Calculate the width needed for the line numbers
        total_lines = len(self.buff)
        line_number_width = len(str(total_lines))

        line_count = 1
        if lines_to_print == 0:
            for line in self.buff:
                print(f"{line_count:>{line_number_width}}  {line}")
                line_count += 1
        else:
            line_count = (len(self.buff) - lines_to_print) + 1
            while lines_to_print > 0:
                print(f"{line_count:>{line_number_width}}  {self.buff[len(self.buff) - lines_to_print]}")
                lines_to_print -= 1
                line_count += 1

    def delete_buffer_entries(self, start: int, end: Optional[int]) -> None:
        """ deletes a single, or range of entries from the buffer """
        if end is None:
            del self.buff[start - 1]
        else:
            del self.buff[start-1:end]
    #
    # def __getitem__(self, index) -> Union[list[Any]|Any]:
    #     if isinstance(index, slice):
    #         if not index.step is None:
    #             raise TypeError("RingBuffer objects cannot take steps in slice")
    #         start = index.start
    #         stop = index.stop
    #         if (stop - start) > len(self.buff):
    #             raise ValueError("Index range is larger than buffer size")
    #         l= []
    #         if stop > len(self.buff):
    #             l.extend(self.buff[start:])
    #             l.extend(self.buff[0:stop-len(self.buff)])
    #             return l
    #         return self.buff[start:stop]
    #     return self.buff[index]


