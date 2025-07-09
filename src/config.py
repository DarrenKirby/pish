"""
config.py - handles all configuration management.
"""
import os
import platform
import tomllib
import time
from typing import Dict, Any
from prompt_toolkit.styles import Style


class PishConfig:
    """Configuration management for pish shell"""

    def __init__(self):
        self.home = os.path.expanduser("~")
        self.conffile = os.path.join(self.home, ".pishrc")
        self.default_prompt = f"[{os.getlogin()}@{platform.node()}]$ "

        # Default values
        self.histfile = os.path.join(self.home, ".pish_history")
        self.histsize = 500
        self.prompt = self.default_prompt
        self.style = Style.from_dict({'': '#dddddd'})
        self.aliases = {}
        self.use_custom_prompt = False

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from .pishrc file"""
        if not os.path.exists(self.conffile):
            return

        try:
            with open(self.conffile, "rb") as f:
                data = tomllib.load(f)

            # History settings
            if 'histfile' in data:
                self.histfile = data['histfile']
            if 'histsize' in data:
                self.histsize = data['histsize']

            # Prompt settings
            if 'prompt' in data:
                self.use_custom_prompt = True
                self.prompt = f"{' '.join(data['prompt'].split())}"

            # Style settings
            if 'style' in data:
                self.style = Style.from_dict(data['style'])

            # Aliases
            if 'alias' in data:
                self.aliases = data['alias']

        except IOError as e:
            print(f"Warning: Error loading config file {self.conffile}: {e}")

    def get_prompt(self, prompt_str: str) -> Any:
        """Returns a prompt to the prompt session"""
        if self.use_custom_prompt:
            local_vars: Dict[str, str] = {}
            # pylint: disable-next=exec-used
            exec('prompt = ' + prompt_str, globals(), local_vars)
            return local_vars['prompt']
        return prompt_str
