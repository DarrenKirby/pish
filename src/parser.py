"""
parser.py - determines command types without executing them.
"""

from enum import Enum
from typing import Tuple

from utils import GlobExpander


class CommandType(Enum):
    """Types of commands that can be executed"""
    QUIT = "quit"
    EMPTY = "empty"
    BANG_HISTORY = "bang_history"
    GLOB = "glob"
    PIPE_LOGICAL = "pipe_logical"
    REDIRECT = "redirect"
    BUILTIN = "builtin"
    REGULAR = "regular"


class CommandParser:
    """Parses commands and determines their type and components"""

    BUILTIN_COMMANDS = {'history', 'echo', 'cd', 'alias', 'unalias'}

    @staticmethod
    def parse_command(command: str, aliases: dict) -> Tuple[CommandType, str]:
        """Parse a command and return its type and processed command"""
        # Handle empty command
        if command == '':
            return CommandType.EMPTY, command

        # Handle quit command
        if command in ("quit",):
            return CommandType.QUIT, command

        # Apply aliases
        processed_command = CommandParser._apply_aliases(command, aliases)

        # Determine command type
        if processed_command.startswith('!') or processed_command.count('!!') > 0:
            return CommandType.BANG_HISTORY, processed_command
        elif GlobExpander.contains_glob(processed_command):
            return CommandType.GLOB, processed_command
        elif "|" in processed_command or "&" in processed_command:
            return CommandType.PIPE_LOGICAL, processed_command
        elif ">" in processed_command:
            return CommandType.REDIRECT, processed_command
        elif processed_command.split()[0] in CommandParser.BUILTIN_COMMANDS:
            return CommandType.BUILTIN, processed_command
        else:
            return CommandType.REGULAR, processed_command

    @staticmethod
    def _apply_aliases(command: str, aliases: dict) -> str:
        """Apply shell aliases to a command"""
        if not aliases:
            return command

        cmd_parts = command.split()
        if cmd_parts and cmd_parts[0] in aliases:
            cmd_parts[0] = aliases[cmd_parts[0]]
            return " ".join(cmd_parts)

        return command
