""" pish - the python idiot shell

 Similar to bash, but without the shell scripting parts.
 Implemented so far:
 * `echo $HOME` will output value of envvars
 * `cd`
 * arbitrary piped commands work ie: `cat foo.txt | sort | uniq`
 * arbitrary `&&` commands work ie: `./configure && make && make install`
 * arbitrary `||` commands work ie: `mount -l || cat /etc/mtab || cat /proc/mounts`
 * STDOUT redirection works ie: `df -h > df.txt` or `ifconfig >> netlog.txt`
"""

# Standard lib imports
import sys
import os
import os.path
import glob
import platform
import time
import re
import tomllib
from typing import Optional


# prompt_toolkit imports
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import set_title
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from pygments.lexers.shell import BashLexer

# Local imports
import runners
import history


# Set up globals
VERSION = '0.0.5'
DEFAULT_PROMPT = f"[{os.getlogin()}@{platform.node()}]$ "
HOME = os.path.expanduser("~")
CONFFILE = HOME + "/.pishrc"
USRPROMT = False

# Dirty hack to appease pylint
assert time

# Parse config file, and set vars
data={}
if os.path.exists(CONFFILE):
    with open(CONFFILE, "rb") as f:
        data = tomllib.load(f)

# History-related settings
if 'histfile' in data:
    HISTFILE = data['histfile']
else:
    HISTFILE = HOME + "/.pish_history"
if 'histsize' in data:
    HISTSIZE = data['histsize']
else:
    HISTSIZE = 500

# Retrieve prompt from config file
if 'prompt' in data:
    USRPROMT= True
    PROMPT = f"{' '.join(data['prompt'].split())}"
else:
    PROMPT = DEFAULT_PROMPT
# Retrive prompt style from config file
if 'style' in data:
    style = Style.from_dict(data['style'])
else:
    style = Style.from_dict({'': '#dddddd'})

# Used for tab completion
def _get_files() -> list:
    files = glob.glob('*')
    files.sort()
    return files


def _get_prompt(p: str) -> Optional[list[tuple]|str]:
    """ Returns a prompt to the prompt session """
    if USRPROMT:
        local_vars: dict[str,str] = {}
        exec('prompt = ' + p, globals(), local_vars)
        return local_vars['prompt']
    return p


def count_lines(fname: str) -> int:
    """ Count and return lines in a file """
    def _make_gen(reader):
        while True:
            b = reader(2 ** 16)
            if not b:
                break
            yield b

    with open(fname, "rb") as fp:
        count = sum(buf.count(b"\n") for buf in _make_gen(fp.raw.read))
    return count


def contains_glob(command):
    """ Simple regex to see if a command is likely to have shell globbing """
    glob_pattern = re.compile(r'[*?\[\]]')
    return bool(glob_pattern.search(command))


def mainloop():
    """ The main loop and command dispatcher """
    print(f"pish version {VERSION} written by Darren Kirby")
    last_exit_status = 0
    h_array = history.load_history_file(HISTFILE, HISTSIZE)
    # Start shell in home directory
    os.chdir(HOME)

    session = PromptSession(lexer=PygmentsLexer(BashLexer))
    # Start infinite loop and run until `quit` command
    # or <ctrl-c> is trapped.
    while True:
        try:
            command = session.prompt(_get_prompt(PROMPT),
                                     enable_history_search=True,
                                     style=style,
                                     completer=WordCompleter(_get_files()),
                                     complete_style=CompleteStyle.READLINE_LIKE,
            )
            # Write the history buffer
            # to file before bailing
            if command in ("quit"):
                history.write_history_file(h_array, HISTFILE)
                sys.exit(0)

            # Write command to history buffer.
            # bash writes the command before running it
            # so we do as well to be consistant.
            # Prefacing a command with a single space
            # will prevent it from being written to history
            if not command.startswith(" "):
                h_array.append(command)
            # ...now strip the space
            command = command.strip()
            # For colour output. Prolly shouldn't be hard-coded here
            # but it's for my own preference. Will likely stay until
            # I implement aliases
            if command.startswith('ls'):
                command = 'ls -G --color' + command[2:]

            # If command is empty we just print a new prompt
            if command == '':
                continue

            # The previous functions are not mutually-exclusive
            # The following are

            if command.startswith('history'):
                last_exit_status, h_array = runners.run_history_command(command,
                                                                        h_array,
                                                                        HISTFILE,
                                                                        HISTSIZE)

            # pipe/AND/OR linked commands
            elif "||" in command:
                last_exit_status = runners.run_or_command(command)
            elif "|" in command:
                last_exit_status = runners.run_pipe_command(command)
            elif "&&" in command:
                last_exit_status = runners.run_and_command(command)

            # Commands with redirected IO
            elif ">>" in command:
                last_exit_status = runners.run_append_command(command)
            elif ">" in command:
                last_exit_status = runners.run_redirect_command(command)

            # echo builtin
            elif command.startswith('echo'):
                last_exit_status = runners.run_echo_command(command, last_exit_status)
            # cd builtin
            elif command.startswith('cd'):
                if len(command.split()[1:]) == 0:
                    os.chdir(HOME)
                else:
                    os.chdir(" ".join(command.split()[1:]))
                last_exit_status = 0
            # Check for shell globbing
            elif contains_glob(command):
                last_exit_status = runners.run_glob_command(command)
            # Regular command
            else:
                last_exit_status = runners.run_command(command)

        except KeyboardInterrupt:
            history.write_history_file(h_array, HISTFILE)
            sys.exit(0)

    return last_exit_status


if __name__ == '__main__':
    set_title(f"pish version {VERSION}")
    exit_status = mainloop()
