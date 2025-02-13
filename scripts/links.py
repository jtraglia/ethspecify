#!/usr/bin/env python3
import os
import re
import json
import argparse

def parse_toc_from_file(file_path, base_github_url, root_dir):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Try to extract a TOC block between <!-- TOC --> and <!-- /TOC -->
    toc_block_match = re.search(r'<!--\s*TOC\s*-->(.*?)<!--\s*/TOC\s*-->', content, re.DOTALL | re.IGNORECASE)
    if toc_block_match:
        toc_block = toc_block_match.group(1)
    else:
        # If no TOC block is found, use the whole file (or you can choose to skip)
        toc_block = content

    # Find markdown links in the TOC block; these are in the form [text](#anchor)
    links = re.findall(r'\[([^\]]+)\]\((#[^)]+)\)', toc_block)
    toc_dict = {}
    # Compute the file path relative to the provided root directory (excluding the root dir name)
    relative_path = os.path.relpath(file_path, root_dir).replace(os.path.sep, '/')
    for _, anchor in links:
        # Clean the anchor (remove the '#' for URL fragment construction)
        anchor_clean = anchor.lstrip('#')
        # Build the full GitHub URL (assumes base_github_url points to the blob view and branch, e.g. .../blob/main)
        url = f"{base_github_url}/{relative_path}#{anchor_clean}"
        # Use a key that includes both the relative file path and the anchor
        key = f"{relative_path}::{anchor}"
        toc_dict[key] = url
    return toc_dict

def main():
    parser = argparse.ArgumentParser(
        description="Generate a dictionary mapping TOC anchors to GitHub links for markdown files."
    )
    parser.add_argument("directory", help="Directory to search for markdown files.")
    parser.add_argument("base_github_url",
                        help="Base GitHub URL (e.g. https://github.com/ethereum/consensus-specs/blob/dev)")
    parser.add_argument("--output", default="output.json", help="Output JSON file name.")
    args = parser.parse_args()

    result = {}
    # Walk through the given directory and process each markdown file
    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.lower().endswith(".md"):
                file_path = os.path.join(root, file)
                toc_entries = parse_toc_from_file(file_path, args.base_github_url, args.directory)
                # If the same anchor appears in multiple files, later ones will overwrite earlier entries.
                result.update(toc_entries)

    # Write the resulting dictionary to a JSON file
    with open(args.output, "w", encoding='utf-8') as out_file:
        json.dump(result, out_file, indent=2)
    print(f"Dictionary written to {args.output}")

if __name__ == "__main__":
    main()