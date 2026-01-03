#!/usr/bin/env python3
"""
Check i18n key usage and identify unused keys.
This script:
1. Extracts all i18n keys from the locale files
2. Searches for usage of each key in the codebase
3. Reports which keys are unused
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Set

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Locale files
EN_LOCALE = PROJECT_ROOT / "src/locales/en.ts"
ZH_CN_LOCALE = PROJECT_ROOT / "src/locales/zh-CN.ts"

# Directories to search for usage
SEARCH_DIR = PROJECT_ROOT / "src"


def extract_keys_recursive(obj: dict, prefix: str = "") -> List[str]:
    """
    Recursively extract all leaf keys from a nested dictionary.
    """
    keys = []

    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            # Recursively process nested objects
            keys.extend(extract_keys_recursive(value, full_key))
        elif isinstance(value, list):
            # Handle arrays - add the key itself
            keys.append(full_key)
        else:
            # Leaf node - add the key
            keys.append(full_key)

    return keys


def parse_typescript_object(file_path: Path) -> dict:
    """
    Parse TypeScript object by converting to JSON-like format.
    This is a simplified approach that works for our use case.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove type annotations and comments
    content = re.sub(r"//.*", "", content)  # Remove line comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)  # Remove block comments

    # Extract the object literal
    match = re.search(r"(?:export const \w+ = |= )(\{.*\})", content, re.DOTALL)
    if not match:
        print("ERROR: Could not parse file")
        return {}

    obj_str = match.group(1)

    # Simple transformation to make it JSON-like
    # Replace single quotes with double quotes
    obj_str = re.sub(r"'([^']*)'", r'"\1"', obj_str)

    # Remove 'as const' and 'satisfies Translation'
    obj_str = re.sub(r"\s*as\s+const\s*$", "", obj_str)
    obj_str = re.sub(r"\s*satisfies\s+\w+\s*$", "", obj_str)

    # Handle template literals (keep them as strings)
    obj_str = re.sub(r"`([^`]*)`", r'"\1"', obj_str)

    # Add quotes to unquoted keys
    obj_str = re.sub(r'(\w+):', r'"\1":', obj_str)

    # Remove trailing commas
    obj_str = re.sub(r",(\s*[}\]])", r"\1", obj_str)

    try:
        return json.loads(obj_str)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        # Fallback: manual parsing
        return parse_manually(file_path)


def parse_manually(file_path: Path) -> dict:
    """
    Manual parsing as fallback.
    Build the key tree by tracking nesting levels.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = {}
    stack = [result]
    key_stack = []

    in_export = False
    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("//"):
            continue

        # Start tracking after "export const en ="
        if "export const" in line and "=" in line:
            in_export = True
            continue

        if not in_export:
            continue

        # End of object
        if stripped == "} as const" or stripped == "} as const satisfies Translation":
            break

        # Match key: value or key: {
        match = re.match(r"^(\w+):\s*(.*)$", stripped)
        if not match:
            # Check for closing braces
            if stripped.startswith("}"):
                if stack and len(stack) > 1:
                    stack.pop()
                    if key_stack:
                        key_stack.pop()
            continue

        key = match.group(1)
        rest = match.group(2).strip()

        # Determine if this is a nested object or a leaf value
        if rest.startswith("{"):
            # Nested object
            new_dict = {}
            stack[-1][key] = new_dict
            stack.append(new_dict)
            key_stack.append(key)
        elif rest.startswith("["):
            # Array value - treat as leaf
            stack[-1][key] = []
        else:
            # Leaf value (string, number, etc.)
            # Extract value (remove trailing comma)
            value = re.sub(r",$", "", rest)
            stack[-1][key] = value

    return result


def extract_all_keys(file_path: Path) -> Set[str]:
    """Extract all i18n keys from a locale file."""
    print(f"Extracting i18n keys from {file_path.name}...")

    # Try JSON-like parsing first
    obj = parse_typescript_object(file_path)

    if not obj:
        print("Falling back to manual parsing...")
        obj = parse_manually(file_path)

    if not obj:
        print("ERROR: Could not parse file")
        return set()

    keys = extract_keys_recursive(obj)
    print(f"Found {len(keys)} keys")

    return set(keys)


def search_key_usage(key: str) -> bool:
    """
    Search for usage of a key in the codebase using ripgrep.
    Returns True if the key is used, False otherwise.
    """
    # Escape special regex characters in the key
    escaped_key = re.escape(key)

    # Search for patterns like t('key') or t("key")
    # Use word boundary to avoid partial matches
    patterns = [
        f"t\\(['\\\"]({escaped_key})['\\\"]",
        f"t\\(['\\\"]({escaped_key})\\.",  # Dynamic keys like t('key.subkey')
    ]

    for pattern in patterns:
        try:
            result = subprocess.run(
                ["rg", "-q", pattern, str(SEARCH_DIR)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True
        except FileNotFoundError:
            # ripgrep not available, fall back to simple text search
            try:
                # Just search for the key name literally
                simple_pattern = f't("{key}")'
                result = subprocess.run(
                    ["grep", "-r", "-q", simple_pattern, str(SEARCH_DIR)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return True

                simple_pattern2 = f"t('{key}')"
                result = subprocess.run(
                    ["grep", "-r", "-q", simple_pattern2, str(SEARCH_DIR)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass

    return False


def find_unused_keys(keys: Set[str]) -> Set[str]:
    """Find keys that are not used in the codebase."""
    print("\nSearching for key usage in the codebase...")
    print("This may take a while...\n")

    unused = set()
    used = set()

    total = len(keys)
    for idx, key in enumerate(sorted(keys), 1):
        if idx % 50 == 0 or idx == total:
            print(f"Progress: {idx}/{total} ({idx*100//total}%)")

        if not search_key_usage(key):
            unused.add(key)
        else:
            used.add(key)

    print(f"\nUsed keys: {len(used)}")
    print(f"Unused keys: {len(unused)}")

    return unused


def main():
    print("=" * 60)
    print("i18n Key Usage Checker")
    print("=" * 60)

    # Extract all keys
    all_keys = extract_all_keys(EN_LOCALE)

    if not all_keys:
        print("No keys found!")
        return

    # Sample a few keys to verify parsing
    sample_keys = sorted(all_keys)[:10]
    print("\nSample keys (first 10):")
    for key in sample_keys:
        print(f"  - {key}")

    # Find unused keys
    unused_keys = find_unused_keys(all_keys)

    # Report results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if unused_keys:
        print(f"\nFound {len(unused_keys)} unused keys:\n")
        for key in sorted(unused_keys):
            print(f"  - {key}")

        # Save to file for review
        output_file = PROJECT_ROOT / "unused_i18n_keys.txt"
        with open(output_file, "w") as f:
            f.write("Unused i18n keys:\n")
            f.write("=" * 60 + "\n\n")
            for key in sorted(unused_keys):
                f.write(f"{key}\n")

        print(f"\nResults saved to: {output_file}")
    else:
        print("\nNo unused keys found! All keys are being used.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
