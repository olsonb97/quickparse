from setuptools import setup, find_namespace_packages

setup(
    name="quickparse",
    version="1.0.0",
    packages=find_namespace_packages(include=['src.utils']),
    entry_points={
        'console_scripts': [
            'quickparse=src.utils.cli:main',
        ],
    },
)