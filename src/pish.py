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
from typing import Any


# prompt_toolkit imports
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import set_title
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.history import InMemoryHistory
from pygments.lexers.shell import BashLexer

# Local imports
import runners
#import history
from historybuff import HistoryBuff


# Set up constants
VERSION = '0.0.6'
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

# Load shell aliases
if 'alias' in data:
    ALIASES = data['alias']
else:
    ALIASES = {}

# Used for tab completion
def _get_files() -> list[str]:
    files = glob.glob('*')
    files.sort()
    return files


def _get_prompt(p: str) -> Any:
    """ Returns a prompt to the prompt session """
    if USRPROMT:
        local_vars: dict[str,str] = {}
        exec('prompt = ' + p, globals(), local_vars)
        return local_vars['prompt']
    return p


def contains_glob(command: str) -> bool:
    """ Simple regex to see if a command is likely to have shell globbing """
    glob_pattern = re.compile(r'[*?\[\]]')
    return bool(glob_pattern.search(command))


def mainloop(alias_dict: dict) -> int:
    """ The main loop and command dispatcher """
    print(f"pish version {VERSION} written by Darren Kirby")
    last_exit_status = 0
    # Initialize the history buffer
    hb = HistoryBuff(HISTSIZE, HISTFILE)
    hb.load_from_file(hb.histfile)
    # Start shell in home directory
    os.chdir(HOME)

    session: Any = PromptSession(lexer=PygmentsLexer(BashLexer), history=InMemoryHistory(hb.buff))
    # Start infinite loop and run until `quit` command
    # or <ctrl-c> is trapped.
    while True:
        try:
            command = session.prompt(message=_get_prompt(PROMPT),
                                     enable_history_search=True,
                                     style=style,
                                     completer=WordCompleter(_get_files()),
                                     complete_style=CompleteStyle.READLINE_LIKE)

            # Write the history buffer
            # to file before bailing
            if command in ("quit"):
                hb.write_to_file(HISTFILE)
                sys.exit(0)

            # Write command to history buffer.
            # bash writes the command before running it
            # so we do as well to be consistant.
            # Prefacing a command with a single space will
            # prevent it from being written to the history buffer
            if not command.startswith(" "):
                hb.append(command)
            # ...now strip the space
            command = command.strip()

            # !!!
            # For colour output. Prolly shouldn't be hard-coded here
            # but it's for my own preference. Will likely stay until
            # I implement aliases
            #if command.startswith('ls'):
            #    command = 'ls -G --color' + command[2:]

            # If command is empty we just print a new prompt
            if command == '':
                continue

            # Check if the command is an alias
            if command.split()[0] in alias_dict.keys():
                cmd = command.split()
                cmd[0] = alias_dict[cmd[0]]
                command = " ".join(cmd)

            # The previous functions are not mutually-exclusive
            # The following are:

            # `!` history commands
            if command.startswith('!') or command.count('!!') > 0:
                last_exit_status, hb = runners.run_bang_command(command, hb)

            # Print, set, and unset shell aliases
            elif command.startswith('alias') or command.startswith('unalias'):
                last_exit_status, alias_dict = runners.run_alias_command(command, alias_dict)

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

            # history builtin
            elif command.startswith('history'):
                last_exit_status, hb = runners.run_history_command(command, hb)
            # echo builtin
            elif command.startswith('echo'):
                last_exit_status = runners.run_echo_command(command, last_exit_status)
            # cd builtin
            elif command.startswith('cd'):
                if len(command.split()[1:]) == 0:
                    os.chdir(HOME)
                else:
                    try:
                        os.chdir(" ".join(command.split()[1:]))
                    except (FileNotFoundError, PermissionError, NotADirectoryError) as err:
                        print(err)
                last_exit_status = 0

            # Check for shell globbing
            elif contains_glob(command):
                last_exit_status = runners.run_glob_command(command)
            # Regular command
            else:
                last_exit_status = runners.run_command(command)

        except KeyboardInterrupt:
            hb.write_to_file(hb.histfile)
            sys.exit(0)

    return last_exit_status


if __name__ == '__main__':
    set_title(f"pish version {VERSION}")
    exit_status = mainloop(ALIASES)
