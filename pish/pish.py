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


import sys
import os
import platform
import time

import tomllib
#from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.shell import BashLexer

import runners
import history


# Set up globals
# Version, ps1 prompt
VERSION = '0.0.5'
DEFAULT_PROMPT = f"[{os.getlogin()}@{platform.node()}]$ "
HISTFILE = os.path.expanduser("~") + "/.pish_history"
CONFFILE = os.path.expanduser("~") + "/.pishrc"
USRPROMT = False


# Load prompt from config file
data={}
if os.path.exists(CONFFILE):
    with open(CONFFILE, "rb") as f:
        data = tomllib.load(f)
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


def get_prompt(p: str) -> Optional[list[tuple]|str]:
    """ Returns a prompt to the prompt session """
    if USRPROMT:
        local_vars = {}
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


def mainloop():
    """ The main loop and command dispatcher """
    print(f"pish version {VERSION} written by Darren Kirby")
    last_exit_status = 0
    HISTORY = history.load_history_file(HISTFILE)


    session = PromptSession(lexer=PygmentsLexer(BashLexer))
    # Start infinite loop and run until `quit` command
    # or <ctrl-c> is trapped.
    while True:
        try:
            #command = input(PS1)
            command = session.prompt(get_prompt(PROMPT), style=style)
            # Quit the shell
            if command in ("quit"):
                history.write_history_file(HISTORY, HISTFILE)
                sys.exit(0)
            # Write command to HISTORY
            HISTORY.append(command)
            # Delete extra white space
            command = command.strip()
            # For colour output
            if command.startswith('ls'):
                command = 'ls -G --color' + command[2:]

            if command == '':
                continue

            if command.startswith('history'):
                last_exit_status, HISTORY = runners.run_history_command(command, HISTORY, HISTFILE)
            elif "||" in command:
                last_exit_status = runners.run_or_command(command)
            elif "|" in command:
                last_exit_status = runners.run_pipe_command(command)
            elif "&&" in command:
                last_exit_status = runners.run_and_command(command)
            elif ">>" in command:
                last_exit_status = runners.run_append_command(command)
            elif ">" in command:
                last_exit_status = runners.run_redirect_command(command)

            # 'echo' builtin
            elif command.startswith('echo'):
                last_exit_status = runners.run_echo_command(command, last_exit_status)
            # cd builtin
            elif command.split()[0] == 'cd':
                os.chdir(" ".join(command.split()[1:]))
                last_exit_status = 0
            # Regular command
            else:
                last_exit_status = runners.run_command(command)

        except KeyboardInterrupt:
            history.write_history_file(HISTORY, HISTFILE)
            sys.exit(0)

    return last_exit_status


if __name__ == '__main__':
    exit_status = mainloop()
