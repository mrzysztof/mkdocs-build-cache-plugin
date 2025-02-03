import os
import json
import shutil
import tempfile

import pytest

from mkdocs.exceptions import Abort
from mkdocs.config import Config
from mkdocs.theme import Theme
from mkdocs.plugins import BasePlugin

from mkdocs_build_cache.plugin import BuildCachePlugin, BuildCacheAbort, MkDocsEncoder


@pytest.fixture
def temp_project_dir():
    """
    Create a temporary directory simulating a MkDocs project.
    This fixture creates:
      - a docs directory with at least one markdown file.
      - sets the current working directory to the temp directory.
    """
    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    docs_dir = os.path.join(temp_dir, "docs")
    os.makedirs(docs_dir)

    # Create a sample markdown file.
    index_md = os.path.join(docs_dir, "index.md")
    with open(index_md, "w", encoding="utf-8") as f:
        f.write("# Hello MkDocs\n\nThis is a test file.")

    # Change cwd to the temporary directory.
    os.chdir(temp_dir)
    yield temp_dir, docs_dir

    # Cleanup: return to original cwd and remove temp directory.
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config(temp_project_dir):
    """
    Return a minimal MkDocs config dictionary.
    """
    _, docs_dir = temp_project_dir
    config = {
        "docs_dir": docs_dir,
        "site_name": "Test Site",
    }
    return config


@pytest.fixture
def plugin_instance():
    """Return an instance of the BuildCachePlugin."""
    return BuildCachePlugin()


def test_compute_cache_id(sample_config, plugin_instance):
    """
    Test that compute_cache_id returns a valid hex digest
    and that changing the file content changes the cache id.
    """
    cache_id1 = plugin_instance.compute_cache_id(sample_config)
    assert isinstance(cache_id1, str)
    # Cache id should be 64 hex characters for SHA-256.
    assert len(cache_id1) == 64

    # Now modify a file and ensure the hash changes.
    docs_dir = sample_config["docs_dir"]
    index_md = os.path.join(docs_dir, "index.md")
    with open(index_md, "a", encoding="utf-8") as f:
        f.write("\nAdditional content.")

    cache_id2 = plugin_instance.compute_cache_id(sample_config)
    assert cache_id1 != cache_id2


def test_on_config_no_existing_cache(sample_config, plugin_instance):
    """
    Test that on_config sets the build_cache_id in config when no cache file exists.
    """
    # Ensure no cache file exists.
    cache_file = plugin_instance.CACHE_FILE
    if os.path.exists(cache_file):
        os.remove(cache_file)

    # on_config should set "build_cache_id" in the config.
    config = sample_config.copy()
    returned_config = plugin_instance.on_config(config)
    assert "build_cache_id" in returned_config
    # Check that the computed cache id matches.
    computed_id = plugin_instance.compute_cache_id(sample_config)
    assert returned_config["build_cache_id"] == computed_id


def test_on_config_with_valid_cache(sample_config, plugin_instance):
    """
    Test that on_config raises BuildCacheAbort if the cache file exists and is valid.
    """
    # First, compute the expected cache id.
    cache_id = plugin_instance.compute_cache_id(sample_config)

    # Write the valid cache file.
    cache_file = plugin_instance.CACHE_FILE
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"cache_id": cache_id}, f)

    config = sample_config.copy()
    with pytest.raises(BuildCacheAbort) as exc_info:
        plugin_instance.on_config(config)
    assert "Cached build is up to date" in str(exc_info.value)

    # Clean up
    if os.path.exists(cache_file):
        os.remove(cache_file)


def test_on_post_build(sample_config, plugin_instance):
    """
    Test that on_post_build writes the cache file with the correct build_cache_id.
    """
    # Prepare config with a build_cache_id (simulate that on_config was called).
    computed_id = plugin_instance.compute_cache_id(sample_config)
    sample_config["build_cache_id"] = computed_id

    # Remove any existing cache file.
    cache_file = plugin_instance.CACHE_FILE
    if os.path.exists(cache_file):
        os.remove(cache_file)

    plugin_instance.on_post_build(sample_config)

    # Read the cache file and verify its content.
    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("cache_id") == computed_id

    # Clean up
    if os.path.exists(cache_file):
        os.remove(cache_file)
