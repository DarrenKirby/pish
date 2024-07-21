import sys
import os
import subprocess
import shlex

import history


def run_history_command(command: str, h_array: list, fname: str) -> tuple[int, list]:
    """ Dispatcher for `history` commands """
    args = command.split()[1:]
    if len(args) == 0:
        history.print_history(0, h_array)

    elif args[0] == '-c':
        h_array = []
    elif args[0] == '-w':
        history.write_history_file(h_array, fname)
    elif args[0] == '-d':
        if len(args) == 2:
            h_array = history.del_history_entries(int(args[-1]), None, h_array)
        else:
            h_array = history.del_history_entries(int(args[1]), int(args[2]), h_array)
    elif isinstance(int(args[0]), int):
        history.print_history(int(args[0]), h_array)
    else:
        print(f"Invalid history command: `{command}`")
        return 1
    return (0, h_array)


def run_echo_command(command: str, last_exit_status: int) -> int:
    """ Dispatch `echo` command

    If the first arg starts with `$` then return value of variable,
    otherwise, just print the arguments
    """
    args = " ".join(command.split()[1:])
    if len(args) == 0:
        print()
        return 0
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
