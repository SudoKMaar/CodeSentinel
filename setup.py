"""Setup script for code-review-documentation-agent."""

from setuptools import setup, find_packages

setup(
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'code-review=api.cli:main',
        ],
    },
)
