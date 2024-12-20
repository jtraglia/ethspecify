#!/usr/bin/python3

import argparse
import json
import os
import re
import functools


@functools.lru_cache()
def get_pyspec(version):
    with open(f"pyspecs/{version}/pyspec.json", "r") as file:
        return json.load(file)


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
        except KeyError:
            preset = "mainnet"

        try:
            fork = attributes["fork"]
        except KeyError:
            raise Exception(f"Missing fork attribute")

        try:
            version = attributes["version"]
        except KeyError:
            version = "nightly"

        pyspec = get_pyspec(version)

        spec = None
        if "function" in attributes:
            spec = pyspec[preset][fork]["functions"][attributes["function"]]
        if "constant_var" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            info = pyspec[preset][fork]["constant_vars"][attributes["constant_var"]]
            spec = (
                attributes["constant_var"]
                + (": " + info[0] if info[0] is not None else "")
                + " = "
                + info[1]
            )
        if "preset_var" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            info = pyspec[preset][fork]["preset_vars"][attributes["preset_var"]]
            spec = (
                attributes["preset_var"]
                + (": " + info[0] if info[0] is not None else "")
                + " = "
                + info[1]
            )
        if "config_var" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            info = pyspec[preset][fork]["config_vars"][attributes["config_var"]]
            spec = (
                attributes["config_var"]
                + (": " + info[0] if info[0] is not None else "")
                + " = "
                + info[1]
            )
        if "custom_type" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            spec = (
                attributes["custom_type"]
                + " = "
                + pyspec[preset][fork]["custom_types"][attributes["custom_type"]]
            )
        if "ssz_object" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            spec = pyspec[preset][fork]["ssz_objects"][attributes["ssz_object"]]
        if "dataclass" in attributes:
            if spec is not None:
                raise Exception(f"Tag can only specify one spec item")
            spec = pyspec[preset][fork]["dataclasses"][attributes["dataclass"]].replace("@dataclass\n", "")

        if spec is None:
            raise Exception(f"Tag does not specify spec item type")

        # Extract the prefix from the previous line in the raw file
        prefix = content[:match.start()].splitlines()[-1]
        # Format the new function content with the extracted prefix
        prefixed_spec = "\n".join(f"{prefix}{line}" if line.strip() else prefix for line in spec.strip().split("\n"))
        # Unescape and rebuild the <spec> tag with its original attributes
        updated_tag = f"{opening_tag}\n{prefixed_spec}\n{prefix}{closing_tag}"

        return updated_tag

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