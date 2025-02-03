import os
import hashlib
import json
import logging
from mkdocs.plugins import BasePlugin
from mkdocs.exceptions import Abort
from mkdocs.theme import Theme
from mkdocs.config import Config

log = logging.getLogger("mkdocs.plugins.build_cache")


class BuildCacheAbort(Abort):
    exit_code = 0


class MkDocsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BasePlugin):
            return obj.config
        elif isinstance(obj, Theme):
            return dict(obj)
        elif isinstance(obj, Config):
            return dict(obj)
        else:
            return str(obj)


class BuildCachePlugin(BasePlugin):
    CACHE_FILE = "build_cache.json"

    def on_config(self, config, **kwargs):
        """Compute build cache ID and check if rebuild is necessary."""
        cache_id = self.compute_cache_id(config)
        if os.path.exists(self.CACHE_FILE):
            with open(self.CACHE_FILE, "r") as f:
                previous_cache = json.load(f)
            if previous_cache.get("cache_id") == cache_id:
                log.info("Build cache is valid. Skipping rebuild.")
                raise BuildCacheAbort(
                    "Cached build is up to date. Exiting.")

        config["build_cache_id"] = cache_id
        return config

    def on_post_build(self, config, **kwargs):
        """Save the build cache ID after a successful build."""
        cache_data = {"cache_id": config["build_cache_id"]}
        with open(self.CACHE_FILE, "w") as f:
            json.dump(cache_data, f)
        log.info("Build cache updated.")

    def compute_cache_id(self, config):
        """Generate a unique hash based on config and source files."""
        hasher = hashlib.sha256()

        for k, v in config.items():
            hasher.update(json.dumps((k, v), cls=MkDocsEncoder).encode())

        # Hash all source files
        docs_dir = config.get("docs_dir", "")
        for root, _, files in os.walk(docs_dir):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    hasher.update(f.read())

        return hasher.hexdigest()
