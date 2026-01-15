"""
Coding Scene Detector - Detect coding applications for adaptive filtering

This module identifies coding environments (IDEs, terminals, editors) from
active window information to apply coding-specific optimization thresholds.

When a coding scene is detected, the image filter uses more permissive
thresholds since code editors have minimal visual changes during typing.
"""

import re
from typing import Optional

from core.logger import get_logger

logger = get_logger(__name__)

# Bundle IDs for common coding applications (macOS)
CODING_BUNDLE_IDS = [
    # IDEs and Editors
    "com.microsoft.VSCode",
    "com.microsoft.VSCodeInsiders",
    "com.apple.dt.Xcode",
    "com.jetbrains.",  # All JetBrains IDEs (prefix match)
    "com.sublimetext.",
    "com.sublimehq.Sublime-Text",
    "org.vim.",
    "com.qvacua.VimR",
    "com.neovide.",
    "com.github.atom",
    "dev.zed.Zed",
    "com.cursor.Cursor",
    "ai.cursor.",
    # Terminals
    "com.googlecode.iterm2",
    "com.apple.Terminal",
    "io.alacritty",
    "com.github.wez.wezterm",
    "net.kovidgoyal.kitty",
    "co.zeit.hyper",
    # Other development tools
    "com.postmanlabs.mac",
    "com.insomnia.app",
]

# App names for common coding applications
CODING_APP_NAMES = [
    # IDEs
    "Visual Studio Code",
    "Code",
    "Code - Insiders",
    "Cursor",
    "Zed",
    "Xcode",
    "IntelliJ IDEA",
    "PyCharm",
    "WebStorm",
    "CLion",
    "GoLand",
    "Rider",
    "Android Studio",
    "PhpStorm",
    "RubyMine",
    "DataGrip",
    # Editors
    "Sublime Text",
    "Atom",
    "Vim",
    "NeoVim",
    "Neovide",
    "VimR",
    "Emacs",
    "Nova",
    # Terminals
    "Terminal",
    "iTerm",
    "iTerm2",
    "Alacritty",
    "WezTerm",
    "kitty",
    "Hyper",
    # Other
    "Postman",
    "Insomnia",
]

# Window title patterns that indicate coding activity
CODE_FILE_PATTERNS = [
    # Source code file extensions
    r"\.(py|pyw|pyx|pxd)\b",       # Python
    r"\.(js|mjs|cjs|jsx)\b",       # JavaScript
    r"\.(ts|tsx|mts|cts)\b",       # TypeScript
    r"\.(go|mod|sum)\b",           # Go
    r"\.(rs|rlib)\b",              # Rust
    r"\.(java|kt|kts|scala)\b",    # JVM languages
    r"\.(c|h|cpp|hpp|cc|cxx)\b",   # C/C++
    r"\.(swift|m|mm)\b",           # Apple languages
    r"\.(rb|rake|gemspec)\b",      # Ruby
    r"\.(php|phtml)\b",            # PHP
    r"\.(vue|svelte)\b",           # Frontend frameworks
    r"\.(html|htm|css|scss|sass|less)\b",  # Web
    r"\.(json|yaml|yml|toml|xml)\b",  # Config files
    r"\.(sh|bash|zsh|fish)\b",    # Shell scripts
    r"\.(sql|graphql|gql)\b",     # Query languages
    r"\.(md|mdx|rst|txt)\b",      # Documentation
    # Git and version control
    r"\[Git\]",
    r"- Git$",
    r"COMMIT_EDITMSG",
    r"\.git/",
    # Editor indicators
    r"- vim$",
    r"- nvim$",
    r"- NVIM$",
    r"\(INSERT\)",
    r"\(NORMAL\)",
    r"\(VISUAL\)",
    # Terminal indicators
    r"@.*:.*\$",                   # Shell prompt pattern
    r"bash|zsh|fish|sh\s*$",
]


class CodingSceneDetector:
    """
    Detects if the current active window is a coding environment.

    Uses multiple signals:
    1. Application bundle ID (most reliable on macOS)
    2. Application name
    3. Window title patterns (code file extensions, git, vim modes)
    """

    def __init__(self):
        """Initialize the detector with compiled regex patterns."""
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in CODE_FILE_PATTERNS
        ]
        logger.debug(
            f"CodingSceneDetector initialized with "
            f"{len(CODING_BUNDLE_IDS)} bundle IDs, "
            f"{len(CODING_APP_NAMES)} app names, "
            f"{len(CODE_FILE_PATTERNS)} title patterns"
        )

    def is_coding_scene(
        self,
        app_name: Optional[str] = None,
        bundle_id: Optional[str] = None,
        window_title: Optional[str] = None,
    ) -> bool:
        """
        Determine if the active window is a coding environment.

        Args:
            app_name: Application name (e.g., "Visual Studio Code")
            bundle_id: macOS bundle identifier (e.g., "com.microsoft.VSCode")
            window_title: Window title (e.g., "main.py - project - VSCode")

        Returns:
            True if any signal indicates a coding environment.
        """
        # Check bundle ID (most reliable)
        if bundle_id:
            for pattern in CODING_BUNDLE_IDS:
                if bundle_id.startswith(pattern):
                    logger.debug(f"Coding scene detected via bundle_id: {bundle_id}")
                    return True

        # Check app name
        if app_name:
            # Direct match
            if app_name in CODING_APP_NAMES:
                logger.debug(f"Coding scene detected via app_name: {app_name}")
                return True
            # Case-insensitive partial match for some apps
            app_lower = app_name.lower()
            for coding_app in CODING_APP_NAMES:
                if coding_app.lower() in app_lower:
                    logger.debug(
                        f"Coding scene detected via app_name (partial): {app_name}"
                    )
                    return True

        # Check window title patterns
        if window_title:
            for pattern in self._compiled_patterns:
                if pattern.search(window_title):
                    logger.debug(
                        f"Coding scene detected via window_title pattern: "
                        f"'{window_title}' matched '{pattern.pattern}'"
                    )
                    return True

        return False

    def is_coding_record(self, record_data: Optional[dict]) -> bool:
        """
        Check if a record's active_window indicates coding.

        Args:
            record_data: Record data dict containing active_window info.

        Returns:
            True if the record is from a coding environment.
        """
        if not record_data:
            return False

        active_window = record_data.get("active_window", {})
        if not active_window:
            return False

        return self.is_coding_scene(
            app_name=active_window.get("app_name"),
            bundle_id=active_window.get("app_bundle_id"),
            window_title=active_window.get("window_title"),
        )


# Singleton instance for reuse
_detector: Optional[CodingSceneDetector] = None


def get_coding_detector() -> CodingSceneDetector:
    """Get or create the singleton CodingSceneDetector instance."""
    global _detector
    if _detector is None:
        _detector = CodingSceneDetector()
    return _detector
