""" runners.py - functions that run commands


"""

import sys
import os
import subprocess
import shlex
from string import ascii_letters

from historybuff import HistoryBuff


def _del_alias(alias_list: list, aliases: dict) -> dict:
    try:
        for alias in alias_list:
            del aliases[alias]
    except KeyError:
        print(f"{alias} is not defined")
    return aliases


def _print_alias(aliases: dict) -> None:
    for k, v in aliases.items():
        print(f"alias {k}={v}")


def _add_alias(alias_str: str, aliases: dict) -> dict:
    cmd, alias = alias_str.split('=')
    aliases[cmd] = alias
    return aliases


def run_alias_command(command: str, aliases: dict) -> tuple[int, dict]:
    """ Get, set, and unset shell aliases """
    args = shlex.split(command)

    if len(args) == 1:
        _print_alias(aliases)

    elif args[0] in 'alias':
        if args[1] == '-p':
            _print_alias(aliases)
        else:
            aliases = _add_alias(args[1], aliases)

    else:
        aliases = _del_alias(args[1:], aliases)

    return (0, aliases)


def run_bang_command(command: str, hb: HistoryBuff) -> tuple[int, HistoryBuff]:
    """ Dispatcher for 'bang' history commands """

    if command.count("!!") > 0:
        cmd = command.replace('!!', hb.buff[-2])
    elif command[1] in ascii_letters:
        cmd = hb.search_buffer(command[1:])
    else:
        cmd_to_run = int(command.strip("!").strip())
        cmd = hb.buff[cmd_to_run - 1]

    print(cmd)
    es = run_command(cmd)

    # Replace the `!` command with its expansion in history
    hb.buff[-1] = cmd
    return (es, hb)


def run_history_command(command: str, hb: HistoryBuff) -> tuple[int, HistoryBuff]:
    """ Dispatcher for `history` commands """

    args = command.split()[1:]
    if len(args) == 0:
        hb.print_buff(0)

    elif args[0] == '-c':
        hb.clear()

    elif args[0] == '-w':
        if len(args) == 1:
            hb.write_to_file(hb.histfile)
        else:
            hb.write_to_file(args[1])

    elif args[0] == '-a':
        if len(args) == 1:
            hb.write_to_file(hb.histfile, append=True)
        else:
            hb.write_to_file(args[1], append=True)

    elif args[0] == '-d':
        if len(args) == 1
        if len(args) == 2:
            hb.delete_buffer_entries(int(args[-1]), None)
        else:
            hb.delete_buffer_entries(int(args[1]), int(args[2]))
    elif isinstance(int(args[0]), int):
        hb.print_buff(int(args[0]))
    else:
        print(f"Invalid history command: `{command}`")
        return (1, hb)
    return (0, hb)


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
    try:
        while len(commands) > 0:
            if es == 0:
                cp = subprocess.run(shlex.split(commands.pop(0)), check=False)
                es = cp.returncode
            else:
                return es
        return es
    except Exception as e:                          # pylint: disable=broad-except
        print(f"Failed to execute command: {e}")
        return 1


def run_or_command(command: str) -> int:
    """ Only run commands if previous failed """
    commands = command.split("||")
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

    cmd = shlex.split(command)
    try:
        es = subprocess.run(cmd, check=False)
        return es.returncode
    except Exception:                                          # pylint: disable=broad-except
        print(f"Command: `{cmd[0]}` not found")
        return 127  # `command not found`


def run_glob_command(command: str) -> int:
    """ Run commands with glob expansions """
    print("Found a glob!")
    return run_command(command)
