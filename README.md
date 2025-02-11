# MkDocs Build Cache Plugin

**MkDocs Build Cache Plugin** is a [MkDocs](https://www.mkdocs.org/) plugin that speeds up your documentation builds by caching the build state. It computes a unique hash based on your configuration, source files, and any additional files you wish to include. If nothing has changed since the last build and your output directory already contains valid content, the plugin can abort the build early, saving valuable time.

## Installation

Install the plugin via pip:

```bash
pip install mkdocs-build-cache-plugin
```

Alternatively, add it to your project’s dependencies.

## Usage

To enable the plugin, add it to your `mkdocs.yml` configuration file. You can also pass an optional list of glob patterns to include additional files in the cache hash computation.

```yaml
site_name: My Docs Site

plugins:
  - search
  - build_cache:
      include:
        - "extras/*.txt"
        - "assets/**/*.css"
```

### How It Works

1. **Cache ID Calculation:**  
   When MkDocs starts, the plugin calculates a unique cache ID based on:

   - The main configuration file (if available).
   - All files under your `docs_dir`.
   - Any extra files that match the glob patterns provided in the `include` option.

2. **Build Skipping:**
   - If a cache file exists and its cache ID matches the newly computed one **and** the output directory (`site_dir`) exists and is nonempty, the plugin raises an abort exception. This tells MkDocs that the build is up to date, and it can safely skip rebuilding.
   - Otherwise, the build proceeds normally. After a successful build, the plugin updates the cache file with the new cache ID.

## Configuration Options

### `include`

- **Type:** `List[str]`
- **Default:** `[]`
- **Description:**  
  A list of glob patterns specifying extra files to be included in the cache hash computation. For example:

  ```yaml
  include:
    - "extras/*.txt"
    - "assets/**/*.css"
  ```

## Development

To run tests locally, ensure you have [pytest](https://docs.pytest.org/) installed and run:

```bash
pytest
```

## Logging

This plugin uses the `mkdocs.plugins` logger namespace. You can control the log output via MkDocs’ verbosity flags (e.g., `--verbose` or `--debug`).

## Contributing

Contributions, suggestions, and bug reports are welcome! Please open an issue or submit a pull request in the project's repository.

## License

This project is licensed under the [MIT License](LICENSE).
