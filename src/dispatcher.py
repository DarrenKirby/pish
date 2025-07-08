"""
dispatcher.py - routes commands to appropriate handlers.
"""

from typing import Tuple
from parser import CommandType, CommandParser
from runners import CommandRunner
from historybuff import HistoryBuff


class CommandDispatcher:
    """Dispatches commands to appropriate runners based on command type"""

    def __init__(self, runner: CommandRunner, home_dir: str):
        self.runner = runner
        self.home_dir = home_dir

    def dispatch(self, command: str, command_type: CommandType,
                 hb: HistoryBuff, last_exit_status: int,
                 aliases: dict) -> Tuple[int, HistoryBuff, dict]:
        """Dispatch command to appropriate handler"""

        if command_type == CommandType.QUIT:
            return self._handle_quit(hb)
        elif command_type == CommandType.EMPTY:
            return last_exit_status, hb, aliases
        elif command_type == CommandType.BANG_HISTORY:
            last_exit_status, hb = self.runner.run_bang_command(command, hb)
        elif command_type == CommandType.GLOB:
            last_exit_status = self.runner.run_glob_command(command, last_exit_status)
        elif command_type == CommandType.PIPE_LOGICAL:
            last_exit_status = self._dispatch_pipe_logical(command)
        elif command_type == CommandType.REDIRECT:
            last_exit_status = self._dispatch_redirect(command)
        elif command_type == CommandType.BUILTIN:
            last_exit_status, hb, aliases = self._dispatch_builtin(
                command, hb, last_exit_status, aliases)
        elif command_type == CommandType.REGULAR:
            last_exit_status = self.runner.run_command(command)

        return last_exit_status, hb, aliases

    def _handle_quit(self, hb: HistoryBuff) -> Tuple[int, HistoryBuff, dict]:
        """Handle quit command"""
        hb.write_to_file(hb.histfile)
        import sys
        sys.exit(0)

    def _dispatch_pipe_logical(self, command: str) -> int:
        """Dispatcher for pipe and logical condition commands"""
        if "||" in command:
            return self.runner.run_or_command(command)
        elif "|" in command:
            return self.runner.run_pipe_command(command)
        else:  # && command
            return self.runner.run_and_command(command)

    def _dispatch_redirect(self, command: str) -> int:
        """Dispatcher for I/O redirected commands"""
        if ">>" in command:
            return self.runner.run_append_command(command)
        else:
            return self.runner.run_redirect_command(command)

    def _dispatch_builtin(self, command: str, hb: HistoryBuff,
                          last_exit_status: int, aliases: dict) -> Tuple[int, HistoryBuff, dict]:
        """Dispatcher for commands that are shell builtins"""
        cmd_name = command.split()[0]

        if cmd_name == 'history':
            last_exit_status, hb = self.runner.run_history_command(command, hb)
        elif cmd_name == 'echo':
            last_exit_status = self.runner.run_echo_command(command, last_exit_status)
        elif cmd_name in ('alias', 'unalias'):
            last_exit_status, aliases = self.runner.run_alias_command(command, aliases)
        elif cmd_name == 'cd':
            last_exit_status = self.runner.run_cd_command(command, self.home_dir)

        return last_exit_status, hb, aliases
