#!/usr/bin/python3

import argparse
import json
import os
import re

with open("../pyspec.json", "r") as file:
    pyspec = json.load(file)


def grep(root_directory, search_pattern):
    matched_files = []
    regex = re.compile(search_pattern)
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    if any(regex.search(line) for line in file):
                        matched_files.append(file_path)
                        break
            except (UnicodeDecodeError, IOError):
                continue
    return matched_files


def extract_attributes(tag):
    attr_pattern = re.compile(r'(\w+)="(.*?)"')
    return dict(attr_pattern.findall(tag))


def replace_spec_tags(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Define regex to match <spec> tags
    pattern = re.compile(r'(<spec\b.*?>)(.*?)(</spec>)', re.DOTALL)

    def replacer(match):
        # Extract the opening tag, inner content, and closing tag
        opening_tag = match.group(1)
        closing_tag = match.group(3)

        # Extract attributes from the opening tag
        attributes = extract_attributes(opening_tag)
        print(f"spec tag: {attributes}")

        try:
            preset = attributes["preset"]
        except KeyError as e:
            preset = "mainnet"

        try:
            fork = attributes["fork"]
        except KeyError as e:
            raise Exception(f"Missing fork attribute")

        try:
            function = attributes["function"]
        except KeyError as e:
            raise Exception(f"Missing function attribute")

        try:
            fn = pyspec[preset][fork]["functions"][function]
        except KeyError as e:
            raise Exception(f"No such function: {function}")

        # Extract the prefix from the previous line in the raw file
        prefix = content[:match.start()].splitlines()[-1]
        # Format the new function content with the extracted prefix
        new_fn = "\n".join(f"{prefix}{line}" if line.strip() else prefix for line in fn.strip().split("\n"))
        # Unescape and rebuild the <spec> tag with its original attributes
        updated_spec = f"{opening_tag}\n{new_fn}\n{prefix}{closing_tag}"

        return updated_spec

    # Replace all matches in the content
    updated_content = pattern.sub(replacer, content)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.write(updated_content)


if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Process files containing <spec> tags.")
    parser.add_argument(
        "--project-path",
        type=str,
        required=True,
        help="Path to the project directory to search for files containing <spec> tags.",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Normalize the provided project path
    project_dir = os.path.abspath(os.path.expanduser(args.project_path))

    # Check if the directory exists
    if not os.path.isdir(project_dir):
        print(f"Error: The directory '{project_dir}' does not exist.")
        exit(1)

    pattern = r"<spec\b.*?>"
    files = grep(project_dir, pattern)

    for f in files:
        print(f"Processing file: {f}")
        replace_spec_tags(f)