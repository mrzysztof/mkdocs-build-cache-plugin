import os
import glob
import hashlib
import json
import logging
from mkdocs.plugins import BasePlugin
from mkdocs.exceptions import Abort
from mkdocs.config import config_options

log = logging.getLogger("mkdocs.plugins.build_cache")


class BuildCacheAbort(Abort):
    exit_code = 0


class BuildCachePlugin(BasePlugin):
    config_scheme = (
        (
            'include',
            config_options.ListOfItems(config_options.Type(str), default=[])
        ),
    )

    CACHE_FILE = "build_cache.json"

    def on_config(self, config, **kwargs):
        """
        Compute a cache ID by hashing:
          - the main config file,
          - all files under docs_dir, and
          - any additional files matching glob patterns from the 'include' option.

        If a cached cache ID exists and matches the current one,
        and if the output directory (site_dir) exists and is nonempty,
        the build is aborted.
        """
        cache_id = self.compute_cache_id(config)

        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "r") as f:
                previous_cache = json.load(f)
            if previous_cache.get("cache_id") == cache_id:
                site_dir = config.get("site_dir", "")
                # Only skip the build if site_dir exists and contains files.
                if site_dir and os.path.isdir(site_dir) and os.listdir(site_dir):
                    log.info(
                        "Build cache is valid and site directory is nonempty. Skipping rebuild.")
                    raise BuildCacheAbort(
                        "Cached build is up to date. Exiting.")
                else:
                    log.info(
                        "Build cache is valid but site directory is missing or empty. Rebuilding.")

        # Store the computed cache ID in the config for later use.
        config["build_cache_id"] = cache_id
        return config

    def on_post_build(self, config, **kwargs):
        """
        After a successful build, save the new cache ID to the cache file.
        """
        cache_data = {"cache_id": config["build_cache_id"]}
        with open(self.CACHE_FILE, "w") as f:
            json.dump(cache_data, f)
        log.info("Build cache updated.")

    def compute_cache_id(self, config):
        """
        Generate a unique hash covering:
          - the configuration file,
          - all files in the docs_dir, and
          - any extra files specified via the 'include' glob patterns.
        """
        hasher = hashlib.sha256()
        config_file = config.get("config_file_path", "")

        def hash_file(file_path):
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                    hasher.update(content)
                    current_hash = hasher.hexdigest()
                    log.debug(
                        f"Processed file {file_path}, current cumulative hash: {current_hash}")
            except IOError as e:
                log.warning(f"Error reading file {file_path}: {e}")

        # Process the main configuration file.
        if config_file and os.path.exists(config_file):
            hash_file(config_file)

        # Process all files under docs_dir.
        docs_dir = config.get("docs_dir", "")
        for root, _, files in os.walk(docs_dir):
            for file in sorted(files):  # sort files for deterministic ordering
                file_path = os.path.join(root, file)
                hash_file(file_path)

        # Process any extra files matching the 'include' glob patterns.
        include_patterns = self.config.get("include", [])
        included_files = set()
        for pattern in include_patterns:
            # glob.glob with recursive=True allows patterns like **/*.txt
            for file_path in glob.glob(pattern, recursive=True):
                if os.path.isfile(file_path):
                    included_files.add(file_path)
        for file_path in sorted(included_files):
            hash_file(file_path)

        return hasher.hexdigest()
