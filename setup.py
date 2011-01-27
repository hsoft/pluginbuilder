#!/usr/bin/env python

try:
    import setuptools
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()

import sys, os
import os.path
from setuptools import setup, find_packages
from distutils.errors  import DistutilsError
from distutils import log

from pkg_resources import require, DistributionNotFound

LONG_DESCRIPTION = open('README.txt').read()

CLASSIFIERS = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: MacOS X :: Cocoa',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Objective C',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Build Tools',
]

if not os.path.exists('py2plugin/bundletemplate/prebuilt/main'):
    print("Run py2plugin/bundletemplate first.")
    sys.exit(1)

setup(
    # metadata
    name='py2plugin',
    version='0.1.0',
    description='Create standalone Mac OS X plugins with Python',
    author='Virgil Dupras',
    author_email='hsoft@hardcoded.net',
    url='http://bitbucket.org/hsoft/py2plugin',
    download_url='http://pypi.python.org/pypi/py2plugin',
    license='MIT or PSF License',
    platforms=['MacOS X'],
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    install_requires=[
        "altgraph>=0.7",
        "modulegraph>=0.8.1",
        "macholib>=1.3",
    ],
    packages=find_packages(),
    package_data={
        'py2plugin.bundletemplate': [
            'prebuilt/main',
            'lib/site.py',
            'src/main.m',
        ],
    },
    entry_points={
        'distutils.commands': [
            "py2plugin = py2plugin.build_app:py2plugin",
        ],
        'distutils.setup_keywords': [
            "plugin = py2plugin.build_app:validate_target",
        ],
    },
    zip_safe=False,
    dependency_links=[],
    test_suite='py2plugin_tests',
)
