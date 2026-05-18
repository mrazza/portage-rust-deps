#!/usr/bin/env python3

# Copyright 2026 Matt Razza
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import os
import re
import subprocess
import sys

try:
    import tomllib
except ImportError:
    # Fallback for Python < 3.11 if needed, but we'll prefer 3.11+
    tomllib = None

def get_crates_metadata(target_path):
    """Runs cargo metadata and extracts dependencies from crates.io."""
    manifest_path = os.path.join(target_path, "Cargo.toml")
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest file {manifest_path} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Running 'cargo metadata' on {manifest_path}...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["cargo", "metadata", "--format-version", "1", "--manifest-path", manifest_path],
            check=True,
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: 'cargo metadata' failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'cargo' command not found. Please ensure Rust/Cargo is installed.", file=sys.stderr)
        sys.exit(1)

    crates = set()
    packages = data.get("packages", [])
    for pkg in packages:
        source = pkg.get("source")
        # We only care about crates from the crates.io registry
        if source and "crates.io" in source:
            name = pkg.get("name")
            version = pkg.get("version")
            crates.add(f"{name}@{version}")

    return sorted(list(crates))

def get_crates_lockfile(target_path):
    """Parses Cargo.lock directly to extract dependencies from crates.io."""
    if tomllib is None:
        print("Error: 'tomllib' not found. This method requires Python 3.11+.", file=sys.stderr)
        sys.exit(1)

    lock_path = os.path.join(target_path, "Cargo.lock")
    if not os.path.exists(lock_path):
        print(f"Error: Lock file {lock_path} not found. Please run 'cargo generate-lockfile' if it's a new project.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {lock_path}...", file=sys.stderr)
    with open(lock_path, "rb") as f:
        data = tomllib.load(f)

    crates = set()
    packages = data.get("package", [])
    for pkg in packages:
        source = pkg.get("source")
        if source and "crates.io" in source:
            name = pkg.get("name")
            version = pkg.get("version")
            crates.add(f"{name}@{version}")

    return sorted(list(crates))

def format_crates_block(crates):
    """Formats the list of crates into a Bash variable block."""
    if not crates:
        return 'CRATES=""'
    
    block = 'CRATES="\n'
    for c in crates:
        block += f"    {c}\n"
    block += '"'
    return block

def update_ebuild(ebuild_path, crates_block):
    """Updates the CRATES variable in an ebuild file, or appends it."""
    if not os.path.exists(ebuild_path):
        print(f"Error: Ebuild file {ebuild_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(ebuild_path, 'r') as f:
        content = f.read()

    # Regex to find CRATES="..." block.
    # Matches CRATES=" followed by anything (including newlines) until " at the start of a line or end of block.
    pattern = re.compile(r'^CRATES=".*?"', re.MULTILINE | re.DOTALL)
    
    if pattern.search(content):
        new_content = pattern.sub(crates_block, content)
        print(f"Updating existing CRATES block in {ebuild_path}...")
    else:
        # If CRATES doesn't exist, try to insert it before inherit
        if "inherit " in content:
            new_content = content.replace("inherit ", f"{crates_block}\n\ninherit ", 1)
            print(f"Inserting CRATES block before 'inherit' in {ebuild_path}...")
        else:
            new_content = content + f"\n\n{crates_block}\n"
            print(f"Appending CRATES block to {ebuild_path}...")

    with open(ebuild_path, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully updated {ebuild_path}.")

def main():
    parser = argparse.ArgumentParser(description="Generate Gentoo CRATES variable for an ebuild.")
    parser.add_argument("path", nargs="?", default=".", help="Path to rust project directory (default: current directory).")
    parser.add_argument("--ebuild", help="Path to an existing ebuild file to update.")
    parser.add_argument("--method", choices=["metadata", "lockfile"], default="metadata", 
                        help="Method to extract dependencies: 'metadata' (requires cargo) or 'lockfile' (requires Python 3.11+).")
    
    args = parser.parse_args()
    
    if args.method == "metadata":
        crates = get_crates_metadata(args.path)
    else:
        crates = get_crates_lockfile(args.path)
        
    crates_block = format_crates_block(crates)
    
    if args.ebuild:
        update_ebuild(args.ebuild, crates_block)
    else:
        print(crates_block)

if __name__ == "__main__":
    main()
