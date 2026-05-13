import re

class SecurityGuard:
    def __init__(self):
        # A list of common prompt injection / jailbreak patterns
        self.heuristics = [
            r"(?i)\bignore\s+(all\s+)?(previous\s+)?instructions\b",
            r"(?i)\bforget\s+(all\s+)?(previous\s+)?instructions\b",
            r"(?i)\bdisregard\s+(all\s+)?(previous\s+)?instructions\b",
            r"(?i)\bsystem\s+prompt\b",
            r"(?i)\bjailbreak\b",
            r"(?i)\byou\s+are\s+now\b",
            r"(?i)\bact\s+as\b",
            r"(?i)\bdan\b", # Do Anything Now
            r"(?i)\bpretend\s+to\s+be\b",
            r"(?i)\bnew\s+instructions\b",
            r"(?i)\bbypass\b",
            r"(?i)\bbase64\b", # often used to obfuscate injections
            r"(?i)\bhex\b"
        ]
        self.compiled_patterns = [re.compile(p) for p in self.heuristics]

    def check_query(self, query: str) -> bool:
        """
        Returns False if a jailbreak attempt is detected, True if the query is safe.
        """
        for pattern in self.compiled_patterns:
            if pattern.search(query):
                return False
        return True
