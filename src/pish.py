""" pish - the python idiot shell

Similar to bash, but without the shell scripting parts.
Implemented so far:
* `echo $HOME` will output value of envvars, `echo $?` is last exit status, `echo ??` is pid of shell.
* arbitrary piped commands work ie: `cat foo.txt | sort | uniq`
* arbitrary `&&` commands work ie: `./configure && make && make install`
* arbitrary `||` commands work ie: `mount-l || cat /etc/mtab || cat /proc/mounts`
* STDOUT redirection works ie: `df -h > df.txt` or `ifconfig >> netlog.txt`
* `histsize` history buffer that is read/written to `histfile`.
* Preface sensitive commands with a space to prevent writing to the history buffer.
* rudimentary tab completion. Only works in PWD so far...
* Customizable prompts, though this is currently crufty.
* `~/.pishrc` configuration file for prompt/prompt style, histfile and histsize.
* Shell globbing: works as expected with `*`, `?`, `[abc]`, `[a-z]`, `{1,2,3}` and `{5..1}`.
"""

import os
import sys
from typing import Any

# prompt_toolkit/pygments imports
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.shortcuts import set_title
from pygments.lexers import BashLexer

# Local imports
from config import PishConfig
from dispatcher import CommandDispatcher
from historybuff import HistoryBuff
from parser import CommandParser
from runners import CommandRunner
from utils import get_files

# Set up constants
VERSION = '0.0.7'


class PishShell:
    """Main shell class that orchestrates all components"""

    def __init__(self):
        self.config = PishConfig()
        self.parser = CommandParser()
        self.runner = CommandRunner()
        self.dispatcher = CommandDispatcher(self.runner, self.config.home)
        self.last_exit_status = 0

        # Initialize history buffer
        self.hb = HistoryBuff(self.config.histsize, self.config.histfile)
        self.hb.load_from_file(self.hb.histfile)

        # Start shell in home directory
        os.chdir(self.config.home)

        # Initialize prompt session
        self.session: Any = PromptSession(
            lexer=PygmentsLexer(BashLexer),
            history=InMemoryHistory(self.hb.buff)
        )

    def run(self) -> None:
        """Main shell loop"""
        print(f"pish version {VERSION}")

        while True:
            try:
                command = self.session.prompt(
                    message=self.config.get_prompt(self.config.prompt),
                    enable_history_search=True,
                    style=self.config.style,
                    completer=WordCompleter(get_files()),
                    complete_style=CompleteStyle.READLINE_LIKE
                )

                # Handle quit command
                if command in ("quit",):
                    self.hb.write_to_file(self.config.histfile)
                    sys.exit(0)

                # Handle history writing
                if not command.startswith(" "):
                    self.hb.append(command)

                # Strip leading space
                command = command.strip()

                # Parse and dispatch command
                command_type, processed_command = self.parser.parse_command(
                    command, self.config.aliases
                )

                self.last_exit_status, self.hb, self.config.aliases = self.dispatcher.dispatch(
                    processed_command, command_type, self.hb,
                    self.last_exit_status, self.config.aliases
                )

            except (KeyboardInterrupt, EOFError):
                self.hb.write_to_file(self.hb.histfile)
                sys.exit(0)


def main():
    """Entry point for the shell"""
    set_title(f"pish version {VERSION}")
    shell = PishShell()
    return shell.run()


if __name__ == '__main__':
    main()
    sys.exit(0)
