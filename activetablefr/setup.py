"""Setup for ActiveTable FR XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


def readme():
    if os.path.exists('README.rst'):
        with open('README.rst') as f:
            return f.read()
    else:
        # fallback to a default description
        return 'ActiveTable FR XBlock'


setup(
    name='activetablefr-xblock',
    version='0.1.0',
    description='ActiveTable FR XBlock',
    long_description=readme(),
    packages=['activetablefr'],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'activetablefr = activetablefr:ActiveTablefrXBlock',
        ]
    },
    package_data=package_data("activetablefr", ["static", "public", "translations"]),
    keywords=['edx', 'activetablefr', 'open-craft'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Framework :: Django",
        "Intended Audience :: Education",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: JavaScript",
        "Topic :: Education",
    ],
)

