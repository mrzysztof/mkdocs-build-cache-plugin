from setuptools import setup, find_packages

setup(
    name="mkdocs-build-cache",
    version="0.1.0",
    description="MkDocs plugin to check if a build is necessary by hashing configuration and documentation files.",
    author="Your Name",
    author_email="your.email@example.com",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "mkdocs>=1.4.0",
    ],
    entry_points={
        "mkdocs.plugins": [
            "build-cache = mkdocs_build_cache.plugin:BuildCachePlugin",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
