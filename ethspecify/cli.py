import argparse
import os

from .core import grep, replace_spec_tags

def main():
    parser = argparse.ArgumentParser(
        description="Process files containing <spec> tags."
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Directory to search for files containing <spec> tags",
        default=".",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Exclude paths matching this regex",
        default=[],
    )
    args = parser.parse_args()

    project_dir = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isdir(project_dir):
        print(f"Error: The directory '{project_dir}' does not exist.")
        exit(1)

    for f in grep(project_dir, r"<spec\b.*?>", args.exclude):
        print(f"Processing file: {f}")
        replace_spec_tags(f)

if __name__ == "__main__":
    main()