# portage-rust-deps

A Python utility to generate and update Gentoo `CRATES` variables for Rust-based ebuilds. This is the Rust equivalent of [portage-dotnet-deps](https://github.com/mrazza/portage-dotnet-deps).

## Features

- **Dependency Extraction**: Supports two methods for identifying dependencies:
  - `metadata`: Uses `cargo metadata` (requires Rust/Cargo installed). Most reliable for complex workspaces.
  - `lockfile`: Parses `Cargo.lock` directly using Python's built-in `tomllib` (requires Python 3.11+). Works without Rust installed.
- **Ebuild Updating**: Can automatically update an existing `CRATES` block in an ebuild or insert one before the `inherit cargo` line.
- **Legacy Format**: Generates entries in the `name@version` format.

## Usage

### Basic Usage (Print to Console)
```bash
./generate_ebuild_crates.py /path/to/rust-project
```

### Update an Ebuild
```bash
./generate_ebuild_crates.py /path/to/rust-project --ebuild /path/to/your.ebuild
```

### Use Lockfile Method (No Cargo required)
```bash
./generate_ebuild_crates.py /path/to/rust-project --method lockfile
```

## Requirements

- Python 3.11+ (for `tomllib` support in the `lockfile` method).
- Rust/Cargo (only if using the `metadata` method).

## Running Tests

To run the automated test suite, use the built-in `unittest` module:
```bash
python3 -m unittest tests/test_generate_ebuild_crates.py
```

## License

Apache License 2.0
