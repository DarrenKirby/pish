"""
runners.py - contains a clean CommandRunner class with all execution logic.
"""

import sys
import os
import subprocess
import shlex
from string import ascii_letters
from typing import Tuple

from historybuff import HistoryBuff
from utils import GlobExpander


class CommandRunner:
    """Handles execution of different types of commands"""

    def __init__(self):
        pass

    @staticmethod
    def run_pipe_command(command: str) -> int:
        """Run an arbitrary amount of piped commands"""
        global p
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
        except Exception as e:
            print(f"Failed to execute command: {e}")
            return 1

    @staticmethod
    def run_and_command(command: str) -> int:
        """Only run commands if previous were successful"""
        commands = command.split("&&")
        es = 0
        try:
            for cmd in commands:
                if es == 0:
                    cp = subprocess.run(shlex.split(cmd.strip()), check=False)
                    es = cp.returncode
                else:
                    return es
            return es
        except Exception as e:
            print(f"Failed to execute command: {e}")
            return 1

    def run_bang_command(self, command: str, hb: HistoryBuff) -> Tuple[int, HistoryBuff]:
        """Dispatcher for 'bang' history commands"""
        # if command.count("!!") > 0:
        #     cmd = command.replace('!!', hb.buff[-2])
        # elif command[1] in ascii_letters:
        #     cmd = hb.search_buffer(command[1:])
        # else:
        #     cmd_to_run = int(command.strip("!").strip())
        #     cmd = hb.buff[cmd_to_run - 1]
        try:
            if command.count("!!") > 0:
                # Check if we have enough history
                if len(hb.buff) < 2:
                    print(f"bash: {command}: event not found")
                    return 1, hb
                cmd = command.replace('!!', hb.buff[-2])

            elif command[1] in ascii_letters:
                # Search for command starting with given letters
                search_term = command[1:]
                cmd = hb.search_buffer(search_term)
                if not cmd:
                    print(f"bash: {command}: event not found")
                    return 1, hb

            else:
                # Numeric history reference
                try:
                    cmd_num = int(command.strip("!").strip())
                    if cmd_num < 1 or cmd_num > len(hb.buff):
                        print(f"bash: {command}: event not found")
                        return 1, hb
                    cmd = hb.buff[cmd_num - 1]
                except ValueError:
                    print(f"bash: {command}: event not found")
                    return 1, hb

            print(cmd)
            # Built-in commands need to be dispatched to the right runner,
            # or they will not work properly.
            if cmd[:4] == "echo":
                es = self.run_echo_command(cmd, 0)
            elif cmd[:2] == 'cd':
                es = self.run_cd_command(cmd, os.path.expanduser("~"))
            elif cmd[:7] == 'history':
                es = self.run_history_command(cmd, hb)
            else:
                es = self.run_command(cmd)
            # Replace the `!` command with its expansion in history
            hb.buff[-1] = cmd
            return es, hb

        except Exception as e:
            print(f"pish: history expansion failed: {e}")
            return 1, hb

    @staticmethod
    def run_history_command(command: str, hb: HistoryBuff) -> Tuple[int, HistoryBuff]:
        """Dispatcher for `history` commands"""
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
            if len(args) >= 2:
                if len(args) == 2:
                    hb.delete_buffer_entries(int(args[1]), None)
                else:
                    hb.delete_buffer_entries(int(args[1]), int(args[2]))
        elif args[0].isdigit():
            hb.print_buff(int(args[0]))
        else:
            print(f"Invalid history command: `{command}`")
            return 1, hb
        return 0, hb

    @staticmethod
    def run_echo_command(command: str, last_exit_status: int) -> int:
        """Dispatch `echo` command"""
        args = " ".join(command.split()[1:])
        if len(args) == 0:
            print()
            return 0
        if args[0] == "$":
            if args[1] == "?":
                print(last_exit_status)
            elif args[1] == "$":
                print(os.getpid())
            else:
                try:
                    print(os.environ[args[1:]])
                except KeyError:
                    sys.stdout.write("\n")
        else:
            print(args)
        return 0

    @staticmethod
    def run_cd_command(command: str, home_dir: str) -> int:
        """Handle cd builtin command"""
        # Set/reset $OLDPWD, but keep the old value around
        # in case the cd command fails.
        try:
            old_old_pwd = os.environ['OLDPWD']
        except KeyError:
            old_old_pwd = os.getcwd()
        os.environ['OLDPWD'] = os.getcwd()
        parts = shlex.split(command)

        if len(parts) == 1:  # Just 'cd' - go home
            target = os.path.expanduser("~")
        elif len(parts) == 2:  # 'cd path'
            target = parts[1]
            # Handle - for previous directory (would need to track OLDPWD)
            if target == '-':
                target = old_old_pwd
            # Expand tilde
            target = os.path.expanduser(target)
        else:  # Too many arguments
            print("pish: cd: too many arguments")
            return 1

        try:
            os.chdir(target)
            return 0
        except FileNotFoundError:
            print(f"pish: cd: {target}: No such file or directory")
            os.environ['OLDPWD'] = old_old_pwd
            return 1
        except NotADirectoryError:
            print(f"pish: cd: {target}: Not a directory")
            os.environ['OLDPWD'] = old_old_pwd
            return 1
        except PermissionError:
            print(f"pish: cd: {target}: Permission denied")
            os.environ['OLDPWD'] = old_old_pwd
            return 1
        except OSError as e:
            print(f"pish: cd: {target}: {e}")
            os.environ['OLDPWD'] = old_old_pwd
            return 1

    def run_glob_command(self, command: str, last_exit_status: int) -> int:
        """Run commands with glob expansions"""
        try:
            expanded_command = GlobExpander.expand_command(command)
            if expanded_command.startswith('echo'):
                return self.run_echo_command(expanded_command, last_exit_status)
            return self.run_command(expanded_command)
        except Exception as e:
            print(f"Error in glob expansion: {e}")
            return self.run_command(command)

    def run_alias_command(self, command: str, aliases: dict) -> Tuple[int, dict]:
        """Get, set, and unset shell aliases"""
        args = shlex.split(command)

        if len(args) == 1:
            self._print_alias(aliases)
        elif args[0] == 'alias':
            if len(args) > 1 and args[1] == '-p':
                self._print_alias(aliases)
            elif len(args) > 1:
                aliases = self._add_alias(args[1], aliases)
        else:  # unalias
            aliases = self._del_alias(args[1:], aliases)

        return 0, aliases

    @staticmethod
    def run_or_command(command: str) -> int:
        """Only run commands if previous failed"""
        commands = command.split("||")
        es = 0
        try:
            for cmd in commands:
                cp = subprocess.run(shlex.split(cmd.strip()), check=False)
                es = cp.returncode
                if es == 0:
                    return es
            return es
        except Exception as e:
            print(f"Failed to execute command: {e}")
            return 1

    @staticmethod
    def run_append_command(command: str) -> int:
        """redirect stdout to a file, append if exists"""
        command, filename = command.split(">>")
        cmd = shlex.split(command.strip())
        filename = filename.strip()

        try:
            with open(filename, "a", encoding="UTF-8") as fp:
                es = subprocess.run(cmd, stdout=fp, check=False)
            return es.returncode
        except Exception as e:
            print(f"Failed to execute command: {e}")
            return 1

    @staticmethod
    def run_redirect_command(command: str) -> int:
        """redirect stdout to a file, clobber if exists"""
        command, filename = command.split(">")
        cmd = shlex.split(command.strip())
        filename = filename.strip()

        try:
            with open(filename, "w", encoding="UTF-8") as fp:
                es = subprocess.run(cmd, stdout=fp, check=False)
            return es.returncode
        except Exception as e:
            print(f"Failed to execute command: {e}")
            return 1

    @staticmethod
    def run_command(command: str) -> int:
        """Run regular commands"""
        cmd = shlex.split(command)
        try:
            es = subprocess.run(cmd, check=False)
            return es.returncode
        except subprocess.CalledProcessError as es:
            print(f"Command: `{cmd[0]}` failed: {es.stderr}")
            return es.returncode

    # Helper methods
    @staticmethod
    def _del_alias(alias_list: list, aliases: dict) -> dict:
        alias = ""
        try:
            for alias in alias_list:
                del aliases[alias]
        except KeyError:
            print(f"{alias} is not defined")
        return aliases

    @staticmethod
    def _print_alias(aliases: dict) -> None:
        for k, v in aliases.items():
            print(f"alias {k}={v}")

    @staticmethod
    def _add_alias(alias_str: str, aliases: dict) -> dict:
        cmd, alias = alias_str.split('=', 1)
        aliases[cmd] = alias
        return aliases
