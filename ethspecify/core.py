import difflib
import functools
import glob
import hashlib
import io
import os
import re
import requests
import textwrap
import tokenize
import yaml


def load_config(directory=None):
    """
    Load configuration from .ethspecify.yml file in the specified directory.
    Returns a dict with configuration values, or empty dict if no config file found.
    """
    if directory is None:
        directory = os.getcwd()

    config_path = os.path.join(directory, '.ethspecify.yml')

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except (yaml.YAMLError, IOError) as e:
            print(f"Warning: Error reading .ethspecify.yml file: {e}")
            return {}

    return {}


def is_excepted(item_name, fork, exceptions):
    """
    Check if an item#fork combination is in the exception list.
    Exceptions can be:
    - Just the item name (applies to all forks)
    - item#fork (specific fork)
    """
    if not exceptions:
        return False

    # Check for exact match with fork
    if f"{item_name}#{fork}" in exceptions:
        return True

    # Check for item name only (all forks)
    if item_name in exceptions:
        return True

    return False


def strip_comments(code):
    # Split the original code into lines so we can decide which to keep or skip
    code_lines = code.splitlines(True)  # Keep line endings in each element

    # Dictionary: line_index -> list of (column, token_string)
    non_comment_tokens = {}

    # Tokenize the entire code
    tokens = tokenize.generate_tokens(io.StringIO(code).readline)
    for ttype, tstring, (srow, scol), _, _ in tokens:
        # Skip comments and pure newlines
        if ttype == tokenize.COMMENT:
            continue
        if ttype in (tokenize.NEWLINE, tokenize.NL):
            continue
        # Store all other tokens, adjusting line index to be zero-based
        non_comment_tokens.setdefault(srow - 1, []).append((scol, tstring))

    final_lines = []
    # Reconstruct or skip lines
    for i, original_line in enumerate(code_lines):
        # If the line has no non-comment tokens
        if i not in non_comment_tokens:
            # Check whether the original line is truly blank (just whitespace)
            if original_line.strip():
                # The line wasn't empty => it was a comment-only line, so skip it
                continue
            else:
                # A truly empty/blank line => keep it
                final_lines.append("")
        else:
            # Reconstruct this line from the stored tokens (preserving indentation/spaces)
            tokens_for_line = sorted(non_comment_tokens[i], key=lambda x: x[0])
            line_str = ""
            last_col = 0
            for col, token_str in tokens_for_line:
                # Insert spaces if there's a gap
                if col > last_col:
                    line_str += " " * (col - last_col)
                line_str += token_str
                last_col = col + len(token_str)
            # Strip trailing whitespace at the end of the line
            final_lines.append(line_str.rstrip())

    return "\n".join(final_lines)


def grep(root_directory, search_pattern, excludes=[]):
    matched_files = []
    regex = re.compile(search_pattern)
    exclude_patterns = [re.compile(pattern) for pattern in excludes]
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if any(pattern.search(file_path) for pattern in exclude_patterns):
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    if any(regex.search(line) for line in file):
                        matched_files.append(file_path)
            except (UnicodeDecodeError, IOError):
                continue
    return matched_files


def diff(a_name, a_content, b_name, b_content):
    diff = difflib.unified_diff(
        a_content.splitlines(), b_content.splitlines(),
        fromfile=a_name, tofile=b_name, lineterm=""
    )
    return "\n".join(diff)


@functools.lru_cache()
def get_links(version="nightly"):
    url = f"https://raw.githubusercontent.com/jtraglia/ethspecify/main/pyspec/{version}/links.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


@functools.lru_cache()
def get_pyspec(version="nightly"):
    url = f"https://raw.githubusercontent.com/jtraglia/ethspecify/main/pyspec/{version}/pyspec.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def get_previous_forks(fork, version="nightly"):
    pyspec = get_pyspec(version)
    config_vars = pyspec["mainnet"][fork]["config_vars"]
    previous_forks = ["phase0"]
    for key in config_vars.keys():
        if key.endswith("_FORK_VERSION"):
            if key != f"{fork.upper()}_FORK_VERSION":
                if key != "GENESIS_FORK_VERSION":
                    f = key.split("_")[0].lower()
                    # Skip EIP forks
                    if not f.startswith("eip"):
                        previous_forks.append(f)
    return list(reversed(previous_forks))


def get_spec(attributes, preset, fork, version="nightly"):
    pyspec = get_pyspec(version)
    spec = None
    if "function" in attributes or "fn" in attributes:
        if "function" in attributes and "fn" in attributes:
            raise Exception(f"cannot contain 'function' and 'fn'")
        if "function" in attributes:
            function_name = attributes["function"]
        else:
            function_name = attributes["fn"]

        spec = pyspec[preset][fork]["functions"][function_name]
        spec_lines = spec.split("\n")
        start, end = None, None

        try:
            vars = attributes["lines"].split("-")
            if len(vars) == 1:
                start = min(len(spec_lines), max(1, int(vars[0])))
                end = start
            elif len(vars) == 2:
                start = min(len(spec_lines), max(1, int(vars[0])))
                end = max(1, min(len(spec_lines), int(vars[1])))
            else:
                raise Exception(f"Invalid lines range for {function_name}: {attributes['lines']}")
        except KeyError:
            pass

        if start or end:
            start = start or 1
            if start > end:
                raise Exception(f"Invalid lines range for {function_name}: ({start}, {end})")
            # Subtract one because line numbers are one-indexed
            spec = "\n".join(spec_lines[start-1:end])
            spec = textwrap.dedent(spec)

    elif "constant_var" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        info = pyspec[preset][fork]["constant_vars"][attributes["constant_var"]]
        spec = (
            attributes["constant_var"]
            + (": " + info[0] if info[0] is not None else "")
            + " = "
            + info[1]
        )
    elif "preset_var" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        info = pyspec[preset][fork]["preset_vars"][attributes["preset_var"]]
        spec = (
            attributes["preset_var"]
            + (": " + info[0] if info[0] is not None else "")
            + " = "
            + info[1]
        )
    elif "config_var" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        info = pyspec[preset][fork]["config_vars"][attributes["config_var"]]
        spec = (
            attributes["config_var"]
            + (": " + info[0] if info[0] is not None else "")
            + " = "
            + info[1]
        )
    elif "custom_type" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        spec = (
            attributes["custom_type"]
            + " = "
            + pyspec[preset][fork]["custom_types"][attributes["custom_type"]]
        )
    elif "ssz_object" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        spec = pyspec[preset][fork]["ssz_objects"][attributes["ssz_object"]]
    elif "dataclass" in attributes:
        if spec is not None:
            raise Exception(f"Tag can only specify one spec item")
        spec = pyspec[preset][fork]["dataclasses"][attributes["dataclass"]].replace("@dataclass\n", "")
    else:
        raise Exception("invalid spec tag")
    return spec

def get_latest_fork(version="nightly"):
    """A helper function to get the latest non-eip fork."""
    pyspec = get_pyspec(version)
    forks = sorted(
        [fork for fork in pyspec["mainnet"].keys() if not fork.startswith("eip")],
        key=lambda x: (x != "phase0", x)
    )
    return forks[-1] if forks else "phase0"


def get_spec_item_changes(fork, preset="mainnet", version="nightly"):
    """
    Compare spec items in the given fork with previous forks to detect changes.
    Returns dict with categories containing items marked as (new) or (modified).
    """
    pyspec = get_pyspec(version)
    if fork not in pyspec[preset]:
        raise ValueError(f"Fork '{fork}' not found in {preset} preset")

    current_fork_data = pyspec[preset][fork]
    previous_forks = get_previous_forks(fork, version)

    changes = {
        'functions': {},
        'constant_vars': {},
        'custom_types': {},
        'ssz_objects': {},
        'dataclasses': {},
        'preset_vars': {},
        'config_vars': {},
    }

    # Check each category of spec items
    for category in changes.keys():
        if category not in current_fork_data:
            continue

        for item_name, item_content in current_fork_data[category].items():
            status = _get_item_status(item_name, item_content, category, previous_forks, pyspec, preset)
            if status:
                changes[category][item_name] = status

    return changes


def _get_item_status(item_name, current_content, category, previous_forks, pyspec, preset):
    """
    Determine if an item is new or modified compared to previous forks.
    Returns 'new', 'modified', or None if unchanged.
    """
    # Check if item exists in any previous fork
    found_in_previous = False
    previous_content = None

    for prev_fork in previous_forks:
        if (prev_fork in pyspec[preset] and
            category in pyspec[preset][prev_fork] and
            item_name in pyspec[preset][prev_fork][category]):

            found_in_previous = True
            prev_content = pyspec[preset][prev_fork][category][item_name]

            # Compare content with immediate previous version
            if prev_content != current_content:
                return "modified"
            else:
                # Found unchanged version, so this is not new or modified
                return None

    # If not found in any previous fork, it's new
    if not found_in_previous:
        return "new"

    return None


def get_spec_item_history(preset="mainnet", version="nightly"):
    """
    Get the complete history of all spec items across all forks.
    Returns dict with categories containing items and their fork history.
    """
    pyspec = get_pyspec(version)
    if preset not in pyspec:
        raise ValueError(f"Preset '{preset}' not found")

    # Get all forks in chronological order, excluding EIP forks
    all_forks = sorted(
        [fork for fork in pyspec[preset].keys() if not fork.startswith("eip")],
        key=lambda x: (x != "phase0", x)
    )

    # Track all unique items across all forks
    all_items = {
        'functions': set(),
        'constant_vars': set(),
        'custom_types': set(),
        'ssz_objects': set(),
        'dataclasses': set(),
        'preset_vars': set(),
        'config_vars': set(),
    }

    # Collect all item names
    for fork in all_forks:
        if fork not in pyspec[preset]:
            continue
        fork_data = pyspec[preset][fork]
        for category in all_items.keys():
            if category in fork_data:
                all_items[category].update(fork_data[category].keys())

    # Build history for each item
    history = {}
    for category in all_items.keys():
        history[category] = {}
        for item_name in all_items[category]:
            item_history = _trace_item_history(item_name, category, all_forks, pyspec, preset)
            if item_history:
                history[category][item_name] = item_history

    return history


def _trace_item_history(item_name, category, all_forks, pyspec, preset):
    """
    Trace the history of a specific item across all forks.
    Returns a list of forks where the item was introduced or modified.
    """
    history_forks = []
    previous_content = None

    for fork in all_forks:
        if (fork in pyspec[preset] and
            category in pyspec[preset][fork] and
            item_name in pyspec[preset][fork][category]):

            current_content = pyspec[preset][fork][category][item_name]

            if previous_content is None:
                # First appearance
                history_forks.append(fork)
            elif current_content != previous_content:
                # Content changed
                history_forks.append(fork)

            previous_content = current_content

    return history_forks

def parse_common_attributes(attributes, config=None):
    if config is None:
        config = {}

    try:
        preset = attributes["preset"]
    except KeyError:
        preset = "mainnet"

    try:
        version = attributes["version"]
    except KeyError:
        version = config.get("version", "nightly")

    try:
        fork = attributes["fork"]
    except KeyError:
        fork = get_latest_fork(version)

    try:
        style = attributes["style"]
    except KeyError:
        style = config.get("style", "hash")

    return preset, fork, style, version

def get_spec_item(attributes, config=None):
    preset, fork, style, version = parse_common_attributes(attributes, config)
    spec = get_spec(attributes, preset, fork, version)

    if style == "full" or style == "hash":
        return spec
    elif style == "diff":
        previous_forks = get_previous_forks(fork, version)

        previous_fork = None
        previous_spec = None
        for i, _ in enumerate(previous_forks):
            previous_fork = previous_forks[i]
            previous_spec = get_spec(attributes, preset, previous_fork, version)
            if previous_spec != "phase0":
                try:
                    previous_previous_fork = previous_forks[i+1]
                    previous_previous_spec = get_spec(attributes, preset, previous_previous_fork, version)
                    if previous_previous_spec == previous_spec:
                        continue
                except KeyError:
                    pass
                except IndexError:
                    pass
            if previous_spec != spec:
                break
            if previous_spec == "phase0":
                raise Exception("there is no previous spec for this")
        return diff(previous_fork, strip_comments(previous_spec), fork, strip_comments(spec))
    if style == "link":
        if "function" in attributes or "fn" in attributes:
            if "function" in attributes and "fn" in attributes:
                raise Exception(f"cannot contain 'function' and 'fn'")
            if "function" in attributes:
                function_name = attributes["function"]
            else:
                function_name = attributes["fn"]
            for key, value in get_links(version).items():
                if fork in key and key.endswith(function_name):
                    return value
            return "Could not find link"
        else:
            return "Not available for this type of spec"
    else:
        raise Exception("invalid style type")


def extract_attributes(tag):
    attr_pattern = re.compile(r'(\w+)="(.*?)"')
    return dict(attr_pattern.findall(tag))


def replace_spec_tags(file_path, config=None):
    with open(file_path, 'r') as file:
        content = file.read()

    # Use provided config or load from file's directory as fallback
    if config is None:
        config = load_config(os.path.dirname(file_path))

    # Define regex to match self-closing tags and long (paired) tags separately
    pattern = re.compile(
        r'(?P<self><spec\b[^>]*\/>)|(?P<long><spec\b[^>]*>[\s\S]*?</spec>)',
        re.DOTALL
    )

    def rebuild_opening_tag(attributes, hash_value):
        # Rebuild a fresh opening tag from attributes, overriding any existing hash.
        new_opening = "<spec"
        for key, val in attributes.items():
            if key != "hash":
                new_opening += f' {key}="{val}"'
        new_opening += f' hash="{hash_value}">'
        return new_opening

    def rebuild_self_closing_tag(attributes, hash_value):
        # Build a self-closing tag from attributes, forcing a single space before the slash.
        new_tag = "<spec"
        for key, val in attributes.items():
            if key != "hash":
                new_tag += f' {key}="{val}"'
        new_tag += f' hash="{hash_value}" />'
        return new_tag

    def replacer(match):
        # Always use the tag text from whichever group matched:
        if match.group("self") is not None:
            original_tag_text = match.group("self")
        else:
            original_tag_text = match.group("long")
        # Determine the original opening tag (ignore inner content)
        if match.group("self") is not None:
            original_tag_text = match.group("self")
        else:
            long_tag_text = match.group("long")
            opening_tag_match = re.search(r'<spec\b[^>]*>', long_tag_text)
            original_tag_text = opening_tag_match.group(0) if opening_tag_match else long_tag_text

        attributes = extract_attributes(original_tag_text)
        print(f"spec tag: {attributes}")
        preset, fork, style, version = parse_common_attributes(attributes, config)
        spec = get_spec(attributes, preset, fork, version)
        hash_value = hashlib.sha256(spec.encode('utf-8')).hexdigest()[:8]

        if style == "hash":
            # Rebuild a fresh self-closing tag.
            updated_tag = rebuild_self_closing_tag(attributes, hash_value)
            return updated_tag
        else:
            # For full/diff styles, rebuild as a long (paired) tag.
            new_opening = rebuild_opening_tag(attributes, hash_value)
            spec_content = get_spec_item(attributes, config)
            prefix = content[:match.start()].splitlines()[-1]
            prefixed_spec = "\n".join(
                f"{prefix}{line}" if line.rstrip() else prefix.rstrip()
                for line in spec_content.rstrip().split("\n")
            )
            updated_tag = f"{new_opening}\n{prefixed_spec}\n{prefix}</spec>"
            return updated_tag


    # Replace all matches in the content
    updated_content = pattern.sub(replacer, content)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.write(updated_content)


def check_source_files(yaml_file, project_root, exceptions=None):
    """
    Check that source files referenced in a YAML file exist and contain expected search strings.
    Returns (valid_count, total_count, errors)
    """
    if exceptions is None:
        exceptions = []
    if not os.path.exists(yaml_file):
        return 0, 0, [f"YAML file not found: {yaml_file}"]

    errors = []
    total_count = 0

    try:
        with open(yaml_file, 'r') as f:
            content_str = f.read()

        # Try to fix common YAML issues with unquoted search strings
        # Replace unquoted search values ending with colons
        content_str = re.sub(r'(\s+search:\s+)([^"\n]+:)(\s*$)', r'\1"\2"\3', content_str, flags=re.MULTILINE)

        try:
            content = yaml.safe_load(content_str)
        except yaml.YAMLError:
            # Fall back to FullLoader if safe_load fails
            content = yaml.load(content_str, Loader=yaml.FullLoader)
    except (yaml.YAMLError, IOError) as e:
        return 0, 0, [f"YAML parsing error in {yaml_file}: {e}"]

    if not content:
        return 0, 0, []

    # Handle both array of objects and single object formats
    items = content if isinstance(content, list) else [content]

    for item in items:
        if not isinstance(item, dict) or 'sources' not in item:
            continue

        # Extract spec reference information from the item
        spec_ref = None
        if 'spec' in item and isinstance(item['spec'], str):
            # Try to extract spec reference from spec content
            spec_content = item['spec']
            # Look for any spec tag attribute and fork
            spec_tag_match = re.search(r'<spec\s+([^>]+)>', spec_content)
            if spec_tag_match:
                tag_attrs = spec_tag_match.group(1)
                # Extract fork
                fork_match = re.search(r'fork="([^"]+)"', tag_attrs)
                # Extract the main attribute (not hash or fork)
                attr_matches = re.findall(r'(\w+)="([^"]+)"', tag_attrs)

                if fork_match:
                    fork = fork_match.group(1)
                    # Find the first non-meta attribute
                    for attr_name, attr_value in attr_matches:
                        if attr_name not in ['fork', 'hash', 'preset', 'version', 'style']:
                            # Map attribute names to type prefixes
                            type_map = {
                                'fn': 'functions',
                                'function': 'functions',
                                'constant_var': 'constants',
                                'config_var': 'configs',
                                'preset_var': 'presets',
                                'ssz_object': 'ssz_objects',
                                'dataclass': 'dataclasses',
                                'custom_type': 'custom_types'
                            }
                            type_prefix = type_map.get(attr_name, attr_name)
                            spec_ref = f"{type_prefix}.{attr_value}#{fork}"
                            break

        # Fallback to just the name if spec extraction failed
        if not spec_ref and 'name' in item:
            spec_ref = item['name']

        # Check if sources list is empty
        if not item['sources']:
            if spec_ref:
                # Extract item name and fork from spec_ref for exception checking
                if '#' in spec_ref and '.' in spec_ref:
                    # Format: "functions.item_name#fork"
                    _, item_with_fork = spec_ref.split('.', 1)
                    if '#' in item_with_fork:
                        item_name, fork = item_with_fork.split('#', 1)
                        # Check if this item is in exceptions
                        if is_excepted(item_name, fork, exceptions):
                            total_count += 1
                            continue

                errors.append(f"EMPTY SOURCES: {spec_ref}")
            else:
                # Fallback if we can't extract spec reference
                item_name = item.get('name', 'unknown')
                errors.append(f"EMPTY SOURCES: No sources defined ({item_name})")
            total_count += 1
            continue

        for source in item['sources']:
            # All sources now use the standardized dict format with file and optional search
            if not isinstance(source, dict) or 'file' not in source:
                continue

            file_path = source['file']
            search_string = source.get('search')
            is_regex = source.get('regex', False)

            total_count += 1

            # Parse line range from file path if present (#L123 or #L123-L456)
            line_range = None
            if '#L' in file_path:
                base_path, line_part = file_path.split('#L', 1)
                file_path = base_path
                # Format is always #L123 or #L123-L456, so just remove all 'L' characters
                line_range = line_part.replace('L', '')

            full_path = os.path.join(project_root, file_path)

            # Create error prefix with spec reference if available
            ref_prefix = f"{spec_ref} | " if spec_ref else ""

            # Check if file exists
            if not os.path.exists(full_path):
                errors.append(f"MISSING FILE: {ref_prefix}{file_path}")
                continue

            # Check line range if specified
            if line_range:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        total_lines = len(lines)

                    # Parse line range
                    if '-' in line_range:
                        # Range like "123-456"
                        start_str, end_str = line_range.split('-', 1)
                        start_line = int(start_str)
                        end_line = int(end_str)

                        if start_line < 1 or end_line < 1 or start_line > end_line:
                            errors.append(f"INVALID LINE RANGE: {ref_prefix}#{line_range} - invalid range in {file_path}")
                            continue
                        elif end_line > total_lines:
                            errors.append(f"INVALID LINE RANGE: {ref_prefix}#{line_range} - line {end_line} exceeds file length ({total_lines}) in {file_path}")
                            continue
                    else:
                        # Single line like "123"
                        line_num = int(line_range)
                        if line_num < 1:
                            errors.append(f"INVALID LINE RANGE: {ref_prefix}#{line_range} - invalid line number in {file_path}")
                            continue
                        elif line_num > total_lines:
                            errors.append(f"INVALID LINE RANGE: {ref_prefix}#{line_range} - line {line_num} exceeds file length ({total_lines}) in {file_path}")
                            continue

                except ValueError:
                    errors.append(f"INVALID LINE RANGE: {ref_prefix}#{line_range} - invalid line format in {file_path}")
                    continue
                except (IOError, UnicodeDecodeError):
                    errors.append(f"ERROR READING: {ref_prefix}{file_path}")
                    continue

            # Check search string if provided
            if search_string:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                        if is_regex:
                            # Use regex search
                            try:
                                pattern = re.compile(search_string, re.MULTILINE)
                                matches = list(pattern.finditer(content))
                                count = len(matches)
                                search_type = "REGEX"
                            except re.error as e:
                                errors.append(f"INVALID REGEX: {ref_prefix}'{search_string}' in {file_path} - {e}")
                                continue
                        else:
                            # Use literal string search
                            count = content.count(search_string)
                            search_type = "SEARCH"

                        if count == 0:
                            errors.append(f"{search_type} NOT FOUND: {ref_prefix}'{search_string}' in {file_path}")
                        elif count > 1:
                            errors.append(f"AMBIGUOUS {search_type}: {ref_prefix}'{search_string}' found {count} times in {file_path}")
                except (IOError, UnicodeDecodeError):
                    errors.append(f"ERROR READING: {ref_prefix}{file_path}")

    valid_count = total_count - len(errors)
    return valid_count, total_count, errors


def extract_spec_tags_from_yaml(yaml_file, tag_type):
    """
    Extract spec tags from a YAML file and return item#fork pairs.
    """
    if not os.path.exists(yaml_file):
        return set()

    pairs = set()
    try:
        with open(yaml_file, 'r') as f:
            content_str = f.read()

        # Try to fix common YAML issues with unquoted search strings
        # Replace unquoted search values ending with colons
        content_str = re.sub(r'(\s+search:\s+)([^"\n]+:)(\s*$)', r'\1"\2"\3', content_str, flags=re.MULTILINE)

        try:
            content = yaml.safe_load(content_str)
        except yaml.YAMLError:
            # Fall back to FullLoader if safe_load fails
            content = yaml.load(content_str, Loader=yaml.FullLoader)

        if not content:
            return set()

        # Handle both array of objects and single object formats
        items = content if isinstance(content, list) else [content]

        for item in items:
            if not isinstance(item, dict) or 'spec' not in item:
                continue

            spec_content = item['spec']
            if not isinstance(spec_content, str):
                continue

            # Find spec tags using regex in the spec field
            pattern = rf'<spec\s+{tag_type}="([^"]+)"[^>]*fork="([^"]+)"'
            matches = re.findall(pattern, spec_content)

            for match_item, fork in matches:
                pairs.add(f"{match_item}#{fork}")

    except (IOError, UnicodeDecodeError, yaml.YAMLError):
        pass

    return pairs


def check_coverage(yaml_file, tag_type, exceptions, preset="mainnet"):
    """
    Check that all spec items from ethspecify have corresponding tags in the YAML file.
    Returns (found_count, total_count, missing_items)
    """
    # Map tag types to history keys
    history_key_map = {
        'ssz_object': 'ssz_objects',
        'config_var': 'config_vars',
        'preset_var': 'preset_vars',
        'dataclass': 'dataclasses',
        'fn': 'functions',
        'constant_var': 'constant_vars',
        'custom_type': 'custom_types'
    }

    # Get expected items from ethspecify
    history = get_spec_item_history(preset)
    expected_pairs = set()

    history_key = history_key_map.get(tag_type, tag_type)
    if history_key in history:
        for item_name, forks in history[history_key].items():
            for fork in forks:
                expected_pairs.add(f"{item_name}#{fork}")

    # Get actual pairs from YAML file
    actual_pairs = extract_spec_tags_from_yaml(yaml_file, tag_type)

    # Find missing items (excluding exceptions)
    missing_items = []
    total_count = len(expected_pairs)

    for item_fork in expected_pairs:
        item_name, fork = item_fork.split('#', 1)

        if is_excepted(item_name, fork, exceptions):
            continue

        if item_fork not in actual_pairs:
            missing_items.append(item_fork)

    found_count = total_count - len(missing_items)
    return found_count, total_count, missing_items


def run_checks(project_dir, config):
    """
    Run all checks based on the configuration.
    Returns (success, results)
    """
    results = {}
    overall_success = True

    # Get specrefs config
    specrefs_config = config.get('specrefs', {})

    # Handle both old format (specrefs as array) and new format (specrefs as dict)
    if isinstance(specrefs_config, list):
        # Old format: specrefs: [file1, file2, ...]
        specrefs_files = specrefs_config
        exceptions = config.get('exceptions', {})
    else:
        # New format: specrefs: { files: [...], exceptions: {...} }
        specrefs_files = specrefs_config.get('files', [])
        exceptions = specrefs_config.get('exceptions', {})

    if not specrefs_files:
        print("Error: No specrefs files specified in .ethspecify.yml")
        print("Please add a 'specrefs:' section with 'files:' listing the files to check")
        return False, {}

    # File type mapping for coverage checking
    file_type_mapping = {
        'ssz-objects': 'ssz_object',
        'config-variables': 'config_var',
        'preset-variables': 'preset_var',
        'dataclasses': 'dataclass',
        'functions': 'fn',
        'constants': 'constant_var',
    }

    # Use explicit file list only
    for filename in specrefs_files:
        yaml_path = os.path.join(project_dir, filename)

        if not os.path.exists(yaml_path):
            print(f"Error: File {filename} defined in config but not found")
            overall_success = False
            continue

        # Determine the tag type from filename for coverage checking
        tag_type = None
        preset = "mainnet"  # default preset

        for pattern, file_tag_type in file_type_mapping.items():
            if pattern in filename:
                tag_type = file_tag_type
                # Check for preset indicators
                if 'minimal' in filename.lower():
                    preset = "minimal"
                break

        # Get the appropriate exceptions for this file type
        section_exceptions = []
        if tag_type:
            # Map tag types to exception keys (support both singular and plural)
            exception_key_map = {
                'ssz_object': ['ssz_objects', 'ssz_object'],
                'config_var': ['configs', 'config_variables', 'config_var'],
                'preset_var': ['presets', 'preset_variables', 'preset_var'],
                'dataclass': ['dataclasses', 'dataclass'],
                'fn': ['functions', 'fn'],
                'constant_var': ['constants', 'constant_variables', 'constant_var'],
                'custom_type': ['custom_types', 'custom_type']
            }

            # Try plural first, then singular for backward compatibility
            if tag_type in exception_key_map:
                for key in exception_key_map[tag_type]:
                    if key in exceptions:
                        section_exceptions = exceptions[key]
                        break

        # Check source files
        valid_count, total_count, source_errors = check_source_files(yaml_path, os.path.dirname(project_dir), section_exceptions)

        # Check coverage if we can determine the type
        found_count, expected_count, missing_items = 0, 0, []
        if tag_type:
            found_count, expected_count, missing_items = check_coverage(yaml_path, tag_type, section_exceptions, preset)

        # Store results using filename as section name
        section_name = filename.replace('.yml', '').replace('-', ' ').title()
        if preset != "mainnet":
            section_name += f" ({preset.title()})"

        results[section_name] = {
            'source_files': {
                'valid': valid_count,
                'total': total_count,
                'errors': source_errors
            },
            'coverage': {
                'found': found_count,
                'expected': expected_count,
                'missing': missing_items
            }
        }

        # Update overall success
        if source_errors or missing_items:
            overall_success = False

    return overall_success, results
