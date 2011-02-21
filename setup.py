#!/usr/bin/env python

try:
    import setuptools
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()

import os
import os.path
from distutils.command.build_py import build_py as _build_py
from setuptools import setup, find_packages
from pluginbuilder import __version__

LONG_DESCRIPTION = open('README').read()

CLASSIFIERS = [
        'Environment :: Console',
        'Environment :: MacOS X :: Cocoa',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Objective C',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Build Tools',
]

class build_py(_build_py):
    def get_data_files(self):
        # BEGIN RANT: distutils sucks
        # What we want to do here is to compile main.m before we install the package and send the
        # result in the package destination as a data file. The normal way to do this would be to
        # override build_py.run(), but unfortunately, get_data_files() is called in
        # finalize_options() (which happens before run()). The end result is that even though
        # 'prebuilt/main' is in package_data, it won't be copied in the final destination because
        # it doesn't exist when get_data_files() is called. Therefore, we have to override
        # get_data_files() instead, which feels like a hack, which is what distutils is anyway.
        # END RANT: distutils sucks
        if not os.path.exists('pluginbuilder/bundletemplate/prebuilt/main'):
            print("Pre-building plugin executable file")
            import pluginbuilder.bundletemplate.setup
            pluginbuilder.bundletemplate.setup.main()
        return _build_py.get_data_files(self)
    

setup(
    name='pluginbuilder',
    version=__version__,
    description='Create standalone Mac OS X plugins with Python',
    author='Virgil Dupras',
    author_email='hsoft@hardcoded.net',
    url='http://bitbucket.org/hsoft/pluginbuilder',
    download_url='http://pypi.python.org/pypi/pluginbuilder',
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
        'pluginbuilder.bundletemplate': [
            'prebuilt/main',
            'lib/site.py',
            'src/main.m',
        ],
    },
    scripts=['bin/pluginbuilder'],
    zip_safe=False,
    cmdclass={'build_py': build_py},
)
