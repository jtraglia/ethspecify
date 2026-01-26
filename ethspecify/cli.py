import argparse
import json
import os
import sys

from .core import grep, replace_spec_tags, get_pyspec, get_spec_item_history, load_config, run_checks, sort_specref_yaml, generate_specref_files


def process(args):
    """Process all spec tags and sort specref YAML files."""
    project_dir = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isdir(project_dir):
        print(f"Error: The directory {repr(project_dir)} does not exist.")
        return 1

    # Load config once from the project directory
    config = load_config(project_dir)

    # Check if auto_add_missing_entries and auto_standardize_names are enabled
    specrefs_config = config.get('specrefs', {})
    if isinstance(specrefs_config, dict):
        auto_add_missing = specrefs_config.get('auto_add_missing_entries', False)
        auto_standardize_names = specrefs_config.get('auto_standardize_names', False)
        specrefs_files = specrefs_config.get('files', [])
    elif isinstance(specrefs_config, list):
        auto_add_missing = False
        auto_standardize_names = False
        specrefs_files = specrefs_config
    else:
        auto_add_missing = False
        auto_standardize_names = False
        specrefs_files = []

    # Process spec tags in files
    for f in grep(project_dir, r"<spec\b.*?>", args.exclude):
        print(f"Processing file: {f}")
        replace_spec_tags(f, config)

    # Add missing spec items to YAML files if enabled
    if auto_add_missing:
        from .core import add_missing_spec_items_to_yaml_files
        add_missing_spec_items_to_yaml_files(project_dir, config, specrefs_files)

    # Update entry names to <spec_item>#<fork> format if enabled
    if auto_standardize_names:
        from .core import update_entry_names_in_yaml_files
        update_entry_names_in_yaml_files(project_dir, specrefs_files)

    # Sort specref YAML files if they exist in config
    for yaml_file in specrefs_files:
        yaml_path = os.path.join(project_dir, yaml_file)
        if os.path.exists(yaml_path):
            if not sort_specref_yaml(yaml_path):
                print(f"Error sorting: {yaml_file}")

    return 0


def list_tags(args):
    """List all available tags with their fork history."""
    preset = getattr(args, 'preset', 'mainnet')
    version = getattr(args, 'version', 'nightly')
    return _list_tags_with_history(args, preset, version)


def _list_tags_with_history(args, preset, version):
    """List all tags with their fork history."""
    try:
        history = get_spec_item_history(preset, version)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    if args.format == "json":
        result = {
            "preset": preset,
            "mode": "history",
            "history": history
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"Available tags across all forks ({preset} preset):")

        def _print_items_with_history(category_name, items_dict, spec_attr):
            """Helper to print items with their fork history."""
            if not items_dict:
                return
            print(f"\n{category_name}:")
            for item_name in sorted(items_dict.keys()):
                if args.search is None or args.search.lower() in item_name.lower():
                    forks = items_dict[item_name]
                    fork_list = ", ".join(forks)
                    print(f"  <spec {spec_attr}=\"{item_name}\" /> ({fork_list})")

        _print_items_with_history("Functions", history['functions'], "fn")
        _print_items_with_history("Constants", history['constant_vars'], "constant_var")
        _print_items_with_history("Custom Types", history['custom_types'], "custom_type")
        _print_items_with_history("SSZ Objects", history['ssz_objects'], "ssz_object")
        _print_items_with_history("Dataclasses", history['dataclasses'], "dataclass")
        _print_items_with_history("Preset Variables", history['preset_vars'], "preset_var")
        _print_items_with_history("Config Variables", history['config_vars'], "config_var")

    return 0


def check(args):
    """Run checks to validate spec references."""
    project_dir = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isdir(project_dir):
        print(f"Error: The directory {repr(project_dir)} does not exist.")
        return 1

    # Load config
    config = load_config(project_dir)

    # Run checks
    success, results = run_checks(project_dir, config)

    # Collect all missing items and errors
    all_missing = []
    all_errors = []
    total_coverage = {"found": 0, "expected": 0}
    total_source_files = {"valid": 0, "total": 0}

    for section_name, section_results in results.items():
        # Collect source file errors
        source = section_results['source_files']
        total_source_files["valid"] += source["valid"]
        total_source_files["total"] += source["total"]
        all_errors.extend(source["errors"])

        # Collect missing items
        coverage = section_results['coverage']
        total_coverage["found"] += coverage["found"]
        total_coverage["expected"] += coverage["expected"]

        # For Project Coverage, items already have the proper prefix
        if section_name == "Project Coverage":
            for missing in coverage['missing']:
                all_missing.append(f"MISSING: {missing}")
        else:
            # Determine the type prefix from section name for YAML-based checks
            if "Config Variables" in section_name:
                type_prefix = "config_var"
            elif "Preset Variables" in section_name:
                type_prefix = "preset_var"
            elif "Ssz Objects" in section_name:
                type_prefix = "ssz_object"
            elif "Dataclasses" in section_name:
                type_prefix = "dataclass"
            else:
                type_prefix = section_name.lower().replace(" ", "_")

            for missing in coverage['missing']:
                all_missing.append(f"MISSING: {type_prefix}.{missing}")

    # Display only errors and missing items
    for error in all_errors:
        print(error)

    for missing in sorted(all_missing):
        print(missing)

    if all_errors or all_missing:
        return 1
    else:
        total_refs = total_coverage['expected']
        print(f"All specification references ({total_refs}) are valid.")
        return 0


def list_forks(args):
    """List all available forks."""
    pyspec = get_pyspec()
    preset = args.preset

    if preset not in pyspec:
        print(f"Error: Preset '{preset}' not found.")
        print(f"Available presets: {', '.join(pyspec.keys())}")
        return 1

    # Filter out EIP forks
    forks = sorted(
        [fork for fork in pyspec[preset].keys() if not fork.startswith("eip")],
        key=lambda x: (x != "phase0", x)
    )

    if args.format == "json":
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


def init(args):
    """Initialize a specrefs directory with basic configuration and empty source mappings."""
    output_dir = args.path or "specrefs"
    version = args.version

    # Check if output directory already exists
    if os.path.exists(output_dir):
        print(f"Error: directory {repr(output_dir)} already exists.")
        print("Please specify a different directory or remove the existing one.")
        return 1

    try:
        # Generate the specref files
        print(f"Initializing specrefs directory: {version}")
        generate_specref_files(output_dir, version, "mainnet")
        print(f"Successfully created specrefs directory at: {output_dir}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Process files containing <spec> tags."
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Parser for 'process' command
    process_parser = subparsers.add_parser("process", help="Process spec tags in files")
    process_parser.set_defaults(func=process)
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

    # Parser for 'list-tags' command
    list_tags_parser = subparsers.add_parser("list-tags", help="List available specification tags with fork history")
    list_tags_parser.set_defaults(func=list_tags)
    list_tags_parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (text or json)",
    )
    list_tags_parser.add_argument(
        "--search",
        type=str,
        help="Filter tags by search term",
        default=None,
    )
    list_tags_parser.add_argument(
        "--version",
        type=str,
        help="Specification version to use (default: nightly)",
        default="nightly",
    )

    # Parser for 'check' command
    check_parser = subparsers.add_parser("check", help="Check spec reference coverage and validity")
    check_parser.set_defaults(func=check)
    check_parser.add_argument(
        "--path",
        type=str,
        help="Directory containing YAML files to check",
        default=".",
    )

    # Parser for 'list-forks' command
    list_forks_parser = subparsers.add_parser("list-forks", help="List available forks")
    list_forks_parser.set_defaults(func=list_forks)
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

    # Parser for 'init' command
    init_parser = subparsers.add_parser("init", help="Initialize a specrefs directory")
    init_parser.set_defaults(func=init)
    init_parser.add_argument(
        "version",
        type=str,
        help="Specification version (e.g., 'nightly' or 'v1.6.0-alpha.5')",
    )
    init_parser.add_argument(
        "--path",
        type=str,
        help="Output directory for specrefs (default: specrefs)",
        default="specrefs",
    )

    # Default to 'process' if no args are provided
    if len(sys.argv) == 1:
        sys.argv.insert(1, "process")

    args = parser.parse_args()
    exit(args.func(args))


if __name__ == "__main__":
    main()
