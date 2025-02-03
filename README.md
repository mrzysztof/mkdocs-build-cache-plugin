# MkDocs Build Cache Plugin

A simple [MkDocs](https://www.mkdocs.org/) plugin to cache build outputs and skip rebuilds when nothing has changed. This plugin computes a unique hash based on your MkDocs configuration and source files, and only triggers a rebuild when changes are detected.

## Features

- **Build Caching:** Saves a cache file (`build_cache.json`) that stores a hash of the build configuration and source files.
- **Skip Unnecessary Rebuilds:** If the computed hash matches the cache file from a previous build, the plugin will skip the rebuild process.
- **Seamless MkDocs Integration:** Built as a standard MkDocs plugin that hooks into the `on_config` and `on_post_build` events.

## Installation

```bash
pip install mkdocs-build-cache-plugin
```

## Usage

1. **Configure MkDocs:**
   In your `mkdocs.yml`, add the plugin to your plugins list:

   ```yaml
   plugins:
     - search
     - build-cache
   ```

2. **Run MkDocs:**
   When you run `mkdocs build`, the plugin will compute a cache ID based on your configuration and documentation files. If nothing has changed since the last build, the plugin will log a message and skip the rebuild.

## How It Works

- **on_config:**
  During the configuration phase, the plugin computes a SHA-256 hash of your MkDocs configuration and the content of all files in the `docs_dir`.

  - If a cache file (`build_cache.json`) exists and its stored hash matches the computed hash, the plugin raises a `BuildCacheAbort` exception to skip the build.
  - Otherwise, it sets the `build_cache_id` in the configuration.

- **on_post_build:**
  After a successful build, the plugin writes the computed hash to `build_cache.json` for future comparisons.

## Development and Testing

The project uses [pytest](https://docs.pytest.org/) for testing. To run the tests:

1. Install the development dependencies:

   ```bash
   pip install -r requirements/dev.txt
   ```

2. Run the tests:

   ```bash
   pytest
   ```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/my-new-feature`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature/my-new-feature`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- [MkDocs](https://www.mkdocs.org/) for the excellent static site generator.
