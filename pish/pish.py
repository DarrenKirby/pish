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

import subprocess
import shlex
import sys
import os
import platform
import time

import tomllib
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.shell import BashLexer


# Set up globals
# Version, ps1 prompt
VERSION = 0.4
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


def write_history_file(command: str, fname: str) -> None:
    """ Writes the current command to the history file """
    try:
        with open(fname, "a", encoding="UTF-8") as fp:
            fp.write(command + '\n')
    except IOError as e:
        print(f"Could not write to {fname}: {e}")


def del_history_entries(start: int, end: Optional[int], fname: str) -> int:
    """ Given the `history -d` command, deletes the specified commands
    from the history file """
    try:
        with open(fname, "r", encoding="UTF-8") as fp:
            lines = fp.readlines()
            # Reverse the lines list to read from end of file
            lines = lines[::-1]
            fp.close()
    except IOError as e:
        print(f"Could not read history file {fname}: {e}")
        return 1

    if end is None:
        del lines[start]
    else:
        del lines[start:end+1]

    lines = lines[::-1]
    # Re-write the file
    try:
        with open(fname, "w", encoding="UTF-8") as fp:
            for line in lines:
                fp.write(line)
            fp.close()
    except IOError as e:
        print(f"Could not write history file {fname}: {e}")
        return 1
    return 0


def print_history(lines_to_print: int, fname: str) -> int:
    """ Prints a numbered list of commands from the history file """
    try:
        with open(fname, "r", encoding="UTF-8") as fp:
            lines = fp.readlines()
            # Reverse the lines list to read from end of file
            lines = lines[::-1]
            fp.close()
    except IOError as e:
        print(f"Could not read history file {fname}: {e}")
        return 1

    line_count = 1
    if lines_to_print == 0:
        for line in lines:
            print(f"{line_count} {line.replace('\n','')}")
            line_count += 1
    else:
        for line in lines[0:lines_to_print]:
            print(f"{line_count} {line.replace('\n','')}")
            line_count += 1
    return 0


def run_history_command(command: str, fname: str) -> int:
    """ Dispatcher for `history` commands """
    args = command.split()[1:]
    if len(args) == 0:
        print_history(0, fname)
    elif isinstance(args[0], int):
        print_history(args[0], fname)
    elif args[0] == '-c':
        with open(fname, "w", encoding="UTF-8") as fp:
            fp.close()
    elif args[0] == '-d':
        if len(args) == 2:
            del_history_entries(int(args[-1]), None, fname)
        else:
            del_history_entries(int(args[1]), int(args[2]), fname)
    else:
        print(f"Invalid history command: `{command}`")
        return 1
    return 0


def run_echo_command(command: str, last_exit_status: int) -> int:
    """ Dispatch `echo` command

    If the first arg starts with `$` then return value of variable,
    otherwise, just print the arguments
    """
    args = " ".join(command.split()[1:])
    if args[0] == "$":
        # Last exit status
        if args[1] == "?":
            print(last_exit_status)
        # pid of running shell
        elif args[1] == "$":
            print(os.getpid())
        # Lookup if it is a set envvar
        else:
            try:
                print(os.environ[args[1:]])
            except KeyError:
                sys.stdout.write("\n")
    # Just print the arguments
    else:
        print(args)
    return 0


def run_pipe_command(command: str) -> int:
    """ Run an arbitrary amount of piped commands """
    try:
        commands = command.split("|")
        p1 = subprocess.Popen(shlex.split(commands[0].strip()), stdout=subprocess.PIPE)
        prev = p1
        for cmd in commands[1:]:
            p = subprocess.Popen(shlex.split(cmd.strip()), stdin=prev.stdout,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            prev = p

        out, _err = p.communicate()
        p.wait()
        sys.stdout.write(out.decode())
        return p.returncode

    except Exception as e:                          # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")
        return 1


def run_and_command(command: str) -> int:
    """ Only run commands if previous were successfull """
    commands = command.split("&&")
    es = 0
    cp = None
    try:
        while len(commands) > 0:
            if es == 0:
                cp = subprocess.run(shlex.split(commands.pop(0)), check=False)
            es = cp.returncode
        return es
    except Exception as e:                          # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")
        return 1


def run_or_command(command: str) -> int:
    """ Only run commands if previous failed """
    commands = command.split("||")
    es = 0
    try:
        while len(commands) > 0:
            cp = subprocess.run(shlex.split(commands.pop(0)), check=False)
            es = cp.returncode
            if es == 0:
                return es
        return es

    except Exception as e:                           # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")
        return 1


def run_append_command(command: str) -> int:
    """ redirect stdout to a file, append if exists """
    command, filename = command.split(">>")
    cmd = shlex.split(command.strip())
    filename = filename.strip()

    try:
        with open(filename, "a", encoding="UTF-8") as fp:
            es = subprocess.run(cmd, stdout=fp, check=False)
        fp.close()
    except Exception as e:                           # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")

    return es.returncode


def run_redirect_command(command: str) -> int:
    """ redirect stdout to a file, clobber if exists """
    command, filename = command.split(">")
    cmd = shlex.split(command.strip())
    filename = filename.strip()

    try:
        with open(filename, "w", encoding="UTF-8") as fp:
            es = subprocess.run(cmd, stdout=fp, check=False)
        fp.close()
    except Exception as e:                          # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")

    return es.returncode


def run_command(command: str) -> int:
    """ Run regular commands """

    command = shlex.split(command)
    try:
        es = subprocess.run(command, check=False)
        return es.returncode
    except Exception:                                          # pylint: disable=broad-except
        print(f"Command: `{command[0]}` not found")
        return 127  # `command not found`


def mainloop():
    """ The main loop and command dispatcher """
    print(f"pish version {VERSION} written by Darren Kirby")
    last_exit_status = 0


    session = PromptSession(lexer=PygmentsLexer(BashLexer))
    #session = PromptSession()
    while True:
        try:
            #command = input(PS1)
            command = session.prompt(get_prompt(PROMPT), style=style)
            # Quit the shell
            if command in ("quit"):
                sys.exit(0)
            # Write to HISTFILE
            write_history_file(command, HISTFILE)
            # Delete extra white space
            command = command.strip()
            # For colour output
            if command.startswith('ls'):
                command = 'ls -G --color' + command[2:]

            if command == '':
                continue

            if command.startswith('history'):
                last_exit_status = run_history_command(command, HISTFILE)
            elif "||" in command:
                last_exit_status = run_or_command(command)
            elif "|" in command:
                last_exit_status = run_pipe_command(command)
            elif "&&" in command:
                last_exit_status = run_and_command(command)
            elif ">>" in command:
                last_exit_status = run_append_command(command)
            elif ">" in command:
                last_exit_status = run_redirect_command(command)

            # 'echo' builtin
            elif command.startswith('echo'):
                last_exit_status = run_echo_command(command, last_exit_status)
            # cd builtin
            elif command.split()[0] == 'cd':
                os.chdir(" ".join(command.split()[1:]))
                last_exit_status = 0
            # Regular command
            else:
                last_exit_status = run_command(command)
        except KeyboardInterrupt:
            sys.exit(0)

    return last_exit_status


if __name__ == '__main__':
    exit_status = mainloop()
