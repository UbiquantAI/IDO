#!/usr/bin/env python3
"""
Remove unused i18n keys from locale files (improved version).
This version handles multi-line string values correctly.
"""

import re
from pathlib import Path
from typing import Set, List

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Locale files
EN_LOCALE = PROJECT_ROOT / "src/locales/en.ts"
ZH_CN_LOCALE = PROJECT_ROOT / "src/locales/zh-CN.ts"

# Unused keys file
UNUSED_KEYS_FILE = PROJECT_ROOT / "unused_i18n_keys.txt"


def load_unused_keys() -> Set[str]:
    """Load the list of unused keys from the file."""
    print(f"Loading unused keys from {UNUSED_KEYS_FILE.name}...")

    unused_keys = set()

    with open(UNUSED_KEYS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("=") and line != "Unused i18n keys:":
                unused_keys.add(line)

    print(f"Loaded {len(unused_keys)} unused keys")
    return unused_keys


def remove_keys_from_content(content: str, unused_keys: Set[str]) -> tuple[str, int]:
    """
    Remove unused keys from file content.
    Returns (new_content, removed_count)
    """
    # Group unused keys by their parent path for efficient removal
    keys_by_depth = {}
    for key in unused_keys:
        parts = key.split(".")
        depth = len(parts)
        if depth not in keys_by_depth:
            keys_by_depth[depth] = set()
        keys_by_depth[depth].add(key)

    removed_count = 0

    # Remove keys from deepest to shallowest to avoid issues
    for depth in sorted(keys_by_depth.keys(), reverse=True):
        for key in keys_by_depth[depth]:
            # Build regex pattern to match the key and its value
            parts = key.split(".")
            key_name = parts[-1]

            # Pattern to match:
            # - key name
            # - optional whitespace
            # - colon
            # - value (can be string, object, or array)
            # - optional comma
            # Handles multi-line strings and objects

            # For leaf keys (strings):
            # keyName: 'value',
            # or
            # keyName:
            #   'multi-line value',
            pattern_simple = rf"^\s*{re.escape(key_name)}:\s*['\"`].*?['\"`],?\s*$"

            # For nested objects:
            # keyName: {{ ... }},
            # We need to match balanced braces

            # Try simple pattern first (single-line or multi-line string)
            lines = content.split("\n")
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()

                # Check if this line starts with our key
                if re.match(rf"^\s*{re.escape(key_name)}:\s*", line):
                    # Check the current path context to ensure we're removing the right key
                    # For now, we'll use a simpler approach: just match the key name
                    # and check if it's a simple value or nested object

                    rest_of_line = line.split(":", 1)[1].strip()

                    if rest_of_line.startswith("{"):
                        # Nested object - skip until closing brace
                        brace_count = rest_of_line.count("{") - rest_of_line.count("}")
                        i += 1
                        while i < len(lines) and brace_count > 0:
                            brace_count += (
                                lines[i].count("{") - lines[i].count("}")
                            )
                            i += 1
                        removed_count += 1
                        continue
                    elif rest_of_line.startswith("["):
                        # Array - skip until closing bracket
                        bracket_count = rest_of_line.count("[") - rest_of_line.count(
                            "]"
                        )
                        i += 1
                        while i < len(lines) and bracket_count > 0:
                            bracket_count += (
                                lines[i].count("[") - lines[i].count("]")
                            )
                            i += 1
                        removed_count += 1
                        continue
                    else:
                        # Simple value - might be multi-line
                        # Skip this line and check if next line continues the value
                        if not rest_of_line.endswith(",") and not rest_of_line.endswith("'") and not rest_of_line.endswith('"'):
                            # Multi-line string, check next line
                            i += 1
                            if i < len(lines) and lines[i].strip().startswith("'"):
                                i += 1  # Skip the value line too
                        removed_count += 1
                        i += 1
                        continue

                new_lines.append(line)
                i += 1

            content = "\n".join(new_lines)

    return content, removed_count


def clean_empty_objects(content: str) -> str:
    """Clean up empty objects and formatting."""
    # Remove empty objects
    content = re.sub(r"\w+:\s*\{\s*\},?\n", "", content)

    # Remove trailing commas before closing braces
    content = re.sub(r",(\s*\})", r"\1", content)

    # Remove multiple consecutive blank lines
    content = re.sub(r"\n\n\n+", "\n\n", content)

    # Fix spacing issues
    lines = content.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines):
        # Skip empty lines at the start of an object
        if i > 0 and line.strip() == "" and lines[i - 1].strip().endswith("{"):
            continue
        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def remove_keys_manually(file_path: Path, unused_keys: Set[str]) -> int:
    """
    Use Edit tool approach - build map of which lines to keep.
    This is more reliable for complex TypeScript objects.
    """
    print(f"\nProcessing {file_path.name} with manual approach...")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Build a context path as we scan through the file
    current_path = []
    lines_to_keep = []
    skip_until_line = -1
    removed_count = 0

    for line_num, line in enumerate(lines):
        # Skip if we're in a block we're removing
        if line_num <= skip_until_line:
            continue

        stripped = line.strip()

        # Keep structural lines
        if (
            not stripped
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or "import " in line
            or "export " in line
            or "type " in line
            or stripped.startswith("?")
            or stripped.startswith(":")
        ):
            lines_to_keep.append(line)
            continue

        # Try to extract key name
        key_match = re.match(r"^(\s*)(\w+):\s*(.*)$", line)

        if key_match:
            indent = key_match.group(1)
            key_name = key_match.group(2)
            rest = key_match.group(3).strip()

            # Update current path based on indentation
            indent_level = len(indent) // 2
            current_path = current_path[:indent_level]
            full_path = ".".join(current_path + [key_name])

            # Check if this key should be removed
            if full_path in unused_keys:
                print(f"  Removing: {full_path}")
                removed_count += 1

                # Skip this key and its value
                if rest.startswith("{"):
                    # Find the closing brace
                    brace_count = 1
                    for j in range(line_num + 1, len(lines)):
                        brace_count += lines[j].count("{") - lines[j].count("}")
                        if brace_count == 0:
                            skip_until_line = j
                            break
                else:
                    # Simple value - skip just this line
                    # Check if next line is a continuation
                    if line_num + 1 < len(lines):
                        next_line = lines[line_num + 1].strip()
                        if next_line and not next_line.startswith("}") and not re.match(r"^\w+:", next_line):
                            skip_until_line = line_num + 1
                continue

            # This key is kept
            if rest.startswith("{"):
                current_path.append(key_name)

        # Handle closing braces
        if stripped.startswith("}"):
            if current_path:
                current_path.pop()

        lines_to_keep.append(line)

    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines_to_keep)

    return removed_count


def main():
    print("=" * 60)
    print("i18n Unused Keys Removal Tool (v2)")
    print("=" * 60)

    # Load unused keys
    unused_keys = load_unused_keys()

    if not unused_keys:
        print("\nNo unused keys to remove!")
        return

    # Create backups (if not already exist)
    print("\nChecking backups...")
    import shutil

    if not EN_LOCALE.with_suffix(".ts.backup").exists():
        shutil.copy2(EN_LOCALE, str(EN_LOCALE) + ".backup")
        shutil.copy2(ZH_CN_LOCALE, str(ZH_CN_LOCALE) + ".backup")
        print("  Backups created (.backup files)")
    else:
        print("  Using existing backups")

    # Remove keys from both files
    en_removed = remove_keys_manually(EN_LOCALE, unused_keys)
    print(f"  Removed {en_removed} keys from en.ts")

    zh_removed = remove_keys_manually(ZH_CN_LOCALE, unused_keys)
    print(f"  Removed {zh_removed} keys from zh-CN.ts")

    # Clean up formatting
    print("\nCleaning up formatting...")
    for file_path in [EN_LOCALE, ZH_CN_LOCALE]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = clean_empty_objects(content)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    print("\n" + "=" * 60)
    print("COMPLETED")
    print("=" * 60)
    print("\nUnused keys have been removed from both locale files.")
    print("Backup files are available (.backup extension).")
    print("\nNext steps:")
    print("1. Run `pnpm check-i18n` to verify the changes")
    print("2. Test the application to ensure nothing is broken")
    print("3. If everything works, delete the .backup files")
    print("4. If there are issues, restore from .backup files")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
