""" pish - the python idiot shell

 Similar to bash, but without the shell scripting parts.
 Implemented so far:
 * `echo $HOME` will output value of envvars
 * `cd`
 * arbitrary piped commands work ie: `cat foo.txt | sort | uniq`
 * arbitrary `&&` commands work ie: `./configure && make && make install`
 * arbitrary `||` commands work ie: `mount-l || cat /etc/mtab || cat /proc/mounts`
 * STDOUT redirection works ie: `df -h > df.txt` or `ifconfig >> netlog.txt`
"""

import subprocess
import shlex
import sys
import os
import platform
import gnureadline

from colours import BLUE, PURPLE, RESET

# To appease pylint
assert gnureadline

# Set up globals
# Version, ps1 prompt
VERSION = 0.4
DEFAULT_PS1 = f"[{os.getlogin()}@{platform.node()}]$ "

# Load prompt from config file
home_dir = os.path.expanduser("~")
config_path = os.path.join(home_dir, ".pishrc")
if os.path.exists(config_path):
    with open(config_path, 'r', encoding="utf-8") as config_file:
        for line in config_file:
            if line.startswith("PS1 ="):
                exec(line)
                break
else:
    PS1 = DEFAULT_PS1


def run_echo_command(command: str, last_exit_status: int) -> int:
    """ Decide if we are echoing environmental variables """
    args = " ".join(command.split()[1:])
    if args[0] == "$":
        if args[1] == "?":
            print(last_exit_status)
        else:
            try:
                print(os.environ[args[1:]])
            except KeyError:
                sys.stdout.write("\n")
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


def run_append_command(command):
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


def run_redirect_command(command):
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

    while True:
        command = input(PS1)
        # Delete extra white space
        command = command.strip()
        # For colour output
        if command.startswith('ls'):
            command = 'ls -G --color' + command[2:]
        # Quit the shell
        if command in ("exit", "quit"):
            sys.exit(0)

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

    return last_exit_status


if __name__ == '__main__':
    exit_status = mainloop()
