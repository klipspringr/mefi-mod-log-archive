#!/usr/bin/env python3
import re
from pathlib import Path
import sys

# One-off script to transform unstructured tags in the front matter of the existing posts to the new taxonomies.

VALID_KINDS = {"Deleted post", "Mod note"}
VALID_SUBSITES = {"mefi", "ask", "metatalk", "fanfare"}
VALID_MODS = {
    "Brandon Blatcher",
    "loup",
    "travelingthyme",
    "goodnewsfortheinsane",
    "frimble",
    "restless_nomad",
    "The Closer",
}


def parse_array(line):
    """Extract array values from a line like 'tags = ["a", "b", "c"]'"""
    match = re.search(r"\[(.*?)\]", line)
    if not match:
        return []
    return [s.strip(' "') for s in match.group(1).split(",")]


def transform_header(content, filepath):
    match = re.match(r"(\+\+\+\n)(.*?)(\n\+\+\+)", content, re.DOTALL)
    if not match:
        raise ValueError(f"No Hugo front matter found in {filepath}")

    header_lines = match.group(2).strip().split("\n")
    new_lines = []
    kinds, subsites, mods = [], [], []
    in_params = False

    for line in header_lines:
        if line.strip().startswith("tags = "):
            tags = parse_array(line)
            for tag in tags:
                if tag in VALID_KINDS:
                    kinds.append(tag)
                elif tag in VALID_SUBSITES:
                    subsites.append(tag)
                elif tag in VALID_MODS:
                    mods.append(tag)
                else:
                    raise ValueError(f"Unexpected tag '{tag}' in {filepath}")
            continue

        if line.strip() == "[params]":
            in_params = True
            new_lines.append(line)
            continue

        if in_params and line.strip().startswith("site = "):
            continue

        new_lines.append(line)

    # Insert new fields before [params]
    params_idx = next(
        (i for i, l in enumerate(new_lines) if l.strip() == "[params]"), len(new_lines)
    )

    insert_lines = []
    if kinds:
        insert_lines.append(f"kinds = {kinds}")
    if subsites:
        insert_lines.append(f"subsites = {subsites}")
    if mods:
        insert_lines.append(f"mods = {mods}")

    new_lines = (
        new_lines[:params_idx]
        + insert_lines
        + ([""] if insert_lines and params_idx < len(new_lines) else [])
        + new_lines[params_idx:]
    )

    new_header = "\n".join(new_lines)
    return f"+++\n{new_header}\n+++" + content[match.end() :]


def main():
    if len(sys.argv) != 2:
        print("Usage: transform_structure.py <directory>")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory")
        sys.exit(1)

    for html_file in directory.glob("*.html"):
        try:
            content = html_file.read_text(encoding="utf-8")
            transformed = transform_header(content, html_file)

            if transformed != content:
                html_file.write_text(transformed, encoding="utf-8")
                print(f"Transformed: {html_file}")
        except ValueError as e:
            print(f"Error: {e}")
            raise


if __name__ == "__main__":
    main()
