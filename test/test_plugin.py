import os
import json
import shutil
import tempfile
import glob

import pytest

from mkdocs.exceptions import Abort
from mkdocs.config import Config

from mkdocs_build_cache.plugin import BuildCachePlugin, BuildCacheAbort


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
    The config includes:
      - docs_dir (the source files),
      - site_name, and
      - site_dir (the output directory) which is pre-populated to be nonempty.
    """
    temp_dir, docs_dir = temp_project_dir
    site_dir = os.path.join(temp_dir, "site")
    os.makedirs(site_dir, exist_ok=True)
    # Create a dummy file in site_dir so that it is nonempty.
    dummy_file = os.path.join(site_dir, "dummy.html")
    with open(dummy_file, "w", encoding="utf-8") as f:
        f.write("<html></html>")
    config = {
        "docs_dir": docs_dir,
        "site_name": "Test Site",
        "site_dir": site_dir,
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
    # SHA-256 produces a 64-character hexadecimal digest.
    assert len(cache_id1) == 64

    # Now modify a source file and ensure the hash changes.
    docs_dir = sample_config["docs_dir"]
    index_md = os.path.join(docs_dir, "index.md")
    with open(index_md, "a", encoding="utf-8") as f:
        f.write("\nAdditional content.")

    cache_id2 = plugin_instance.compute_cache_id(sample_config)
    assert cache_id1 != cache_id2


def test_compute_cache_id_with_include(sample_config, plugin_instance, temp_project_dir):
    """
    Test that compute_cache_id takes into account extra files specified by the
    'include' configuration option (a list of glob patterns).
    """
    # Create an extra directory and file outside docs_dir.
    temp_dir, _ = temp_project_dir
    extras_dir = os.path.join(temp_dir, "extras")
    os.makedirs(extras_dir, exist_ok=True)
    extra_file = os.path.join(extras_dir, "extra.txt")
    with open(extra_file, "w", encoding="utf-8") as f:
        f.write("Extra content v1")

    plugin_instance.config["include"] = [os.path.join("extras", "*.txt")]

    cache_id1 = plugin_instance.compute_cache_id(sample_config)

    # Now change the content of the extra file.
    with open(extra_file, "w", encoding="utf-8") as f:
        f.write("Extra content v2")

    cache_id2 = plugin_instance.compute_cache_id(sample_config)

    # The cache IDs should differ because the extra file's content changed.
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
    Test that on_config raises BuildCacheAbort if the cache file exists, the cache ID is valid,
    and the site_dir exists and is nonempty.
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


def test_on_config_with_valid_cache_empty_site_dir(sample_config, plugin_instance, temp_project_dir):
    """
    Test that on_config does NOT abort when the cache is valid
    if the site_dir exists but is empty.
    """
    # Compute the cache ID.
    cache_id = plugin_instance.compute_cache_id(sample_config)
    cache_file = plugin_instance.CACHE_FILE
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"cache_id": cache_id}, f)

    # Create an empty site_dir.
    temp_dir, _ = temp_project_dir
    empty_site_dir = os.path.join(temp_dir, "empty_site")
    os.makedirs(empty_site_dir, exist_ok=True)
    # Ensure the directory is empty.
    for f_name in os.listdir(empty_site_dir):
        os.remove(os.path.join(empty_site_dir, f_name))

    # Override the site_dir in the config.
    sample_config["site_dir"] = empty_site_dir
    config = sample_config.copy()
    returned_config = plugin_instance.on_config(config)
    assert "build_cache_id" in returned_config

    # Clean up
    if os.path.exists(cache_file):
        os.remove(cache_file)


def test_on_config_with_valid_cache_missing_site_dir(sample_config, plugin_instance):
    """
    Test that on_config does NOT abort when the cache is valid
    if the site_dir is missing from the config.
    """
    # Compute the cache ID.
    cache_id = plugin_instance.compute_cache_id(sample_config)
    cache_file = plugin_instance.CACHE_FILE
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"cache_id": cache_id}, f)

    # Remove site_dir from the config.
    config = sample_config.copy()
    config.pop("site_dir", None)
    returned_config = plugin_instance.on_config(config)
    assert "build_cache_id" in returned_config

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
