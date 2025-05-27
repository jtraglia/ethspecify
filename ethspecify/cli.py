import argparse
import os

from .core import grep, replace_spec_tags, get_pyspec


def list_tags(args):
    """List all available tags for a specific fork and preset."""
    # Get the specification data
    pyspec = get_pyspec()
    fork = args.fork
    preset = args.preset

    # Validate that the fork exists
    if fork not in pyspec[preset]:
        print(f"Error: Fork '{fork}' not found in {preset} preset")
        available_forks = list(pyspec[preset].keys())
        print(f"Available forks: {', '.join(available_forks)}")
        return 1

    # Format output based on requested format
    if args.format == "json":
        import json
        result = {
            "fork": fork,
            "preset": preset,
            "tags": {
                "functions": list(pyspec[preset][fork]['functions'].keys()),
                "constant_vars": list(pyspec[preset][fork]['constant_vars'].keys()),
                "custom_types": list(pyspec[preset][fork]['custom_types'].keys()),
                "ssz_objects": list(pyspec[preset][fork]['ssz_objects'].keys()),
                "dataclasses": list(pyspec[preset][fork]['dataclasses'].keys()),
                "preset_vars": list(pyspec[preset][fork]['preset_vars'].keys()),
                "config_vars": list(pyspec[preset][fork]['config_vars'].keys()),
            }
        }
        print(json.dumps(result, indent=2))
    else:
        # Plain text output
        print(f"Available tags for {fork} fork ({preset} preset):")

        print("\nFunctions:")
        for fn_name in sorted(pyspec[preset][fork]['functions'].keys()):
            if args.search is None or args.search.lower() in fn_name.lower():
                print(f"  <spec fn=\"{fn_name}\" fork=\"{fork}\" />")

        print("\nConstants:")
        for const_name in sorted(pyspec[preset][fork]['constant_vars'].keys()):
            if args.search is None or args.search.lower() in const_name.lower():
                print(f"  <spec constant_var=\"{const_name}\" fork=\"{fork}\" />")

        print("\nCustom Types:")
        for type_name in sorted(pyspec[preset][fork]['custom_types'].keys()):
            if args.search is None or args.search.lower() in type_name.lower():
                print(f"  <spec custom_type=\"{type_name}\" fork=\"{fork}\" />")

        print("\nSSZ Objects:")
        for obj_name in sorted(pyspec[preset][fork]['ssz_objects'].keys()):
            if args.search is None or args.search.lower() in obj_name.lower():
                print(f"  <spec ssz_object=\"{obj_name}\" fork=\"{fork}\" />")

        print("\nDataclasses:")
        for class_name in sorted(pyspec[preset][fork]['dataclasses'].keys()):
            if args.search is None or args.search.lower() in class_name.lower():
                print(f"  <spec dataclass=\"{class_name}\" fork=\"{fork}\" />")

        print("\nPreset Variables:")
        for var_name in sorted(pyspec[preset][fork]['preset_vars'].keys()):
            if args.search is None or args.search.lower() in var_name.lower():
                print(f"  <spec preset_var=\"{var_name}\" fork=\"{fork}\" />")

        print("\nConfig Variables:")
        for var_name in sorted(pyspec[preset][fork]['config_vars'].keys()):
            if args.search is None or args.search.lower() in var_name.lower():
                print(f"  <spec config_var=\"{var_name}\" fork=\"{fork}\" />")

    return 0


def list_forks(args):
    """List all available forks."""
    pyspec = get_pyspec()
    preset = args.preset

    if preset not in pyspec:
        print(f"Error: Preset '{preset}' not found.")
        print(f"Available presets: {', '.join(pyspec.keys())}")
        return 1

    forks = sorted(
        pyspec[preset].keys(),
        # Put phase0 at the top & EIP feature forks at the bottom
        key=lambda x: (x != "phase0", x.startswith("eip"), x)
    )

    if args.format == "json":
        import json
        result = {
            "preset": preset,
            "forks": forks
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"Available forks for {preset} preset:")
        for fork in forks:
            print(f"  {fork}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Process files containing <spec> tags."
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Parser for the default 'process' command (original functionality)
    process_parser = subparsers.add_parser("process", help="Process spec tags in files")
    process_parser.add_argument(
        "--path",
        type=str,
        help="Directory to search for files containing <spec> tags",
        default=".",
    )
    process_parser.add_argument(
        "--exclude",
        action="append",
        help="Exclude paths matching this regex",
        default=[],
    )

    # Parser for the new 'list-tags' command
    list_parser = subparsers.add_parser("list-tags", help="List available specification tags")
    list_parser.add_argument(
        "--fork",
        type=str,
        help="Fork to list tags for",
        default="deneb",
    )
    list_parser.add_argument(
        "--preset",
        type=str,
        help="Preset to use (mainnet or minimal)",
        default="mainnet",
    )
    list_parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )
    list_parser.add_argument(
        "--search",
        type=str,
        help="Filter tags by search term",
        default=None,
    )

    # Parser for the 'list-forks' command
    list_forks_parser = subparsers.add_parser("list-forks", help="List available forks")
    list_forks_parser.add_argument(
        "--preset",
        type=str,
        help="Preset to use (mainnet or minimal)",
        default="mainnet",
    )
    list_forks_parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )

    # For backward compatibility, add the original arguments at the top level too
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

    # For backward compatibility, default to 'process' if no command is specified
    if args.command is None:
        args.command = "process"

    # Execute the appropriate command
    if args.command == "process":
        # Original functionality
        project_dir = os.path.abspath(os.path.expanduser(args.path))
        if not os.path.isdir(project_dir):
            print(f"Error: The directory '{project_dir}' does not exist.")
            exit(1)

        for f in grep(project_dir, r"<spec\b.*?>", args.exclude):
            print(f"Processing file: {f}")
            replace_spec_tags(f)
    elif args.command == "list-tags":
        # New functionality to list tags
        exit(list_tags(args))
    elif args.command == "list-forks":
        # New functionality to list forks
        exit(list_forks(args))

if __name__ == "__main__":
    main()
