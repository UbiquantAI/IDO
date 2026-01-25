#!/usr/bin/env python3
"""
Remove unused i18n keys from locale files.
Reads the unused keys from unused_i18n_keys.txt and removes them from both locale files.
"""

import re
from pathlib import Path
from typing import Set, List, Dict

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


def should_remove_key(full_path: str, unused_keys: Set[str]) -> bool:
    """
    Check if a key should be removed.
    A key should be removed if it's in the unused list AND it's a leaf node
    (i.e., not a parent of other used keys).
    """
    return full_path in unused_keys


def remove_keys_from_file(file_path: Path, unused_keys: Set[str]) -> None:
    """
    Remove unused keys from a locale file.
    This function:
    1. Reads the file line by line
    2. Tracks the current key path
    3. Skips lines that belong to unused keys
    4. Writes the cleaned content back to the file
    """
    print(f"\nProcessing {file_path.name}...")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip_until_depth = None
    current_path = []
    depth = 0
    removed_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Always keep header and footer
        if (
            not stripped
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or "import" in line
            or "export const" in line
            or "export type" in line
            or "type DeepStringify" in line
            or stripped.startswith("?")
            or stripped.startswith(":")
            or stripped.startswith("}")
            and i >= len(lines) - 5
        ):
            new_lines.append(line)
            continue

        # Count braces to track depth
        line_open_braces = line.count("{") - line.count("'{'") - line.count('"{')
        line_close_braces = line.count("}") - line.count("'}'") - line.count('"}'  )

        # Check if we're currently skipping content
        if skip_until_depth is not None:
            # Check if we've returned to the skip depth (closing brace)
            if stripped.startswith("}") and depth <= skip_until_depth:
                skip_until_depth = None
                depth -= line_close_braces
                if current_path:
                    current_path.pop()
            else:
                depth += line_open_braces - line_close_braces
            continue

        # Try to match a key definition
        key_match = re.match(r"^(\w+):\s*(.*)$", stripped)

        if key_match:
            key_name = key_match.group(1)
            rest = key_match.group(2).strip()

            # Build full path
            full_path = ".".join(current_path + [key_name])

            # Check if this key should be removed
            if should_remove_key(full_path, unused_keys):
                print(f"  Removing: {full_path}")
                removed_count += 1

                # If this is a nested object, skip until we close it
                if rest.startswith("{"):
                    skip_until_depth = depth
                    current_path.append(key_name)
                    depth += line_open_braces - line_close_braces
                continue

            # This key is kept - check if it's a nested object
            if rest.startswith("{"):
                current_path.append(key_name)

        # Handle closing braces
        if stripped.startswith("}"):
            if current_path:
                current_path.pop()

        # Update depth
        depth += line_open_braces - line_close_braces

        # Keep this line
        new_lines.append(line)

    # Write back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"  Removed {removed_count} keys from {file_path.name}")


def clean_empty_objects(file_path: Path) -> None:
    """
    Clean up empty objects left after removing keys.
    For example, if we remove all keys from an object, remove the empty object too.
    """
    print(f"\nCleaning empty objects in {file_path.name}...")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove empty objects (key: {})
    # This regex matches: key: {\n  }
    content = re.sub(r"(\w+):\s*\{\s*\},?\n", "", content)
    content = re.sub(r"(\w+):\s*\{\s*\}\n", "", content)

    # Remove trailing commas before closing braces
    content = re.sub(r",(\s*\})", r"\1", content)

    # Remove multiple consecutive blank lines
    content = re.sub(r"\n\n\n+", "\n\n", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  Cleaned empty objects in {file_path.name}")


def main():
    print("=" * 60)
    print("i18n Unused Keys Removal Tool")
    print("=" * 60)

    # Load unused keys
    unused_keys = load_unused_keys()

    if not unused_keys:
        print("\nNo unused keys to remove!")
        return

    # Create backups
    print("\nCreating backups...")
    import shutil

    shutil.copy2(EN_LOCALE, str(EN_LOCALE) + ".backup")
    shutil.copy2(ZH_CN_LOCALE, str(ZH_CN_LOCALE) + ".backup")
    print("  Backups created (.backup files)")

    # Remove keys from both files
    remove_keys_from_file(EN_LOCALE, unused_keys)
    remove_keys_from_file(ZH_CN_LOCALE, unused_keys)

    # Clean up empty objects
    clean_empty_objects(EN_LOCALE)
    clean_empty_objects(ZH_CN_LOCALE)

    print("\n" + "=" * 60)
    print("COMPLETED")
    print("=" * 60)
    print("\nUnused keys have been removed from both locale files.")
    print("Backup files have been created (.backup extension).")
    print("\nNext steps:")
    print("1. Run `pnpm check-i18n` to verify the changes")
    print("2. Test the application to ensure nothing is broken")
    print("3. If everything works, delete the .backup files")
    print("4. If there are issues, restore from .backup files")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
