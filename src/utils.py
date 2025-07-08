"""
utils.py - contains utility functions like glob expansion.
"""

import glob
import re
import shlex
from typing import List


class GlobExpander:
    """Handles shell globbing and brace expansion"""

    @staticmethod
    def contains_glob(command: str) -> bool:
        """Check if a command contains shell globbing patterns"""
        # Remove quoted strings to avoid false positives
        temp_command = command
        temp_command = re.sub(r'"[^"]*"', '', temp_command)
        temp_command = re.sub(r"'[^']*'", '', temp_command)
        temp_command = re.sub(r'\\.', '', temp_command)

        # Check for glob patterns
        glob_pattern = re.compile(r'[*?]|\[[^\]]*\]|\{[^}]*\}')
        return bool(glob_pattern.search(temp_command))

    @staticmethod
    def expand_command(command: str) -> str:
        """Expand glob patterns in a command"""
        try:
            parts = shlex.split(command)
            expanded_parts = []

            for part in parts:
                if any(c in part for c in ['*', '?', '[', ']', '{', '}']):
                    if '{' in part and '}' in part:
                        expanded_braces = GlobExpander._expand_braces(part)
                        for brace_expanded in expanded_braces:
                            matches = glob.glob(brace_expanded)
                            if matches:
                                expanded_parts.extend(sorted(matches))
                            else:
                                expanded_parts.append(brace_expanded)
                    else:
                        matches = glob.glob(part)
                        if matches:
                            expanded_parts.extend(sorted(matches))
                        else:
                            expanded_parts.append(part)
                else:
                    expanded_parts.append(part)

            # Properly quote parts with spaces
            quoted_parts = []
            for part in expanded_parts:
                if ' ' in part or '\t' in part:
                    quoted_parts.append(shlex.quote(part))
                else:
                    quoted_parts.append(part)

            return ' '.join(quoted_parts)

        except Exception:
            return command

    @staticmethod
    def _expand_braces(pattern: str) -> List[str]:
        """Expand brace patterns like {a,b,c} or {1..5}"""
        results = []
        start = pattern.find('{')
        end = pattern.find('}', start)

        if start == -1 or end == -1:
            return [pattern]

        prefix = pattern[:start]
        suffix = pattern[end + 1:]
        content = pattern[start + 1:end]

        if '..' in content:
            parts = content.split('..')
            if len(parts) == 2:
                try:
                    start_num = int(parts[0])
                    end_num = int(parts[1])
                    if start_num <= end_num:
                        for i in range(start_num, end_num + 1):
                            results.append(f"{prefix}{i}{suffix}")
                    else:
                        for i in range(start_num, end_num - 1, -1):
                            results.append(f"{prefix}{i}{suffix}")
                except ValueError:
                    if len(parts[0]) == 1 and len(parts[1]) == 1:
                        start_char = ord(parts[0])
                        end_char = ord(parts[1])
                        if start_char <= end_char:
                            for i in range(start_char, end_char + 1):
                                results.append(f"{prefix}{chr(i)}{suffix}")
                        else:
                            for i in range(start_char, end_char - 1, -1):
                                results.append(f"{prefix}{chr(i)}{suffix}")
                    else:
                        results.append(pattern)
        else:
            for item in content.split(','):
                results.append(f"{prefix}{item.strip()}{suffix}")

        expanded_results = []
        for result in results:
            if '{' in result and '}' in result:
                expanded_results.extend(GlobExpander._expand_braces(result))
            else:
                expanded_results.append(result)

        return expanded_results if expanded_results else [pattern]


def get_files() -> List[str]:
    """Get files in current directory for tab completion"""
    files = glob.glob('*')
    files.sort()
    return files
