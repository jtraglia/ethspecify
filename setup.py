from setuptools import setup, find_packages

setup(
    name="ethspecify",
    version="0.1.0",
    description="A utility for processing Ethereum specification tags.",
    author="Justin Traglia",
    author_email="jtraglia@pm.me",
    url="https://github.com/jtraglia/ethspecify",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ethspecify=ethspecify.cli:main",
        ],
    },
    install_requires=[
        "requests==2.32.3",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)