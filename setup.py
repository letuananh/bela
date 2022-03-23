#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Setup script for BELA.

Latest version can be found at https://github.com/letuananh/bela

:copyright: (c) 2019 Le Tuan Anh, BLIP lab NTU, Singapore <tuananh.ke@gmail.com>
:license: MIT, see LICENSE for more details.
'''

import io
from setuptools import setup


def read(*filenames, **kwargs):
    ''' Read contents of multiple files and join them together '''
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


readme_file = 'README.md'
long_description = read(readme_file)
pkg_info = {}
exec(read('bela/__version__.py'), pkg_info)

with open('requirements.txt', 'r') as infile:
    requirements = infile.read().splitlines()

setup(
    name='bela',  # package file name (<package-name>-version.tar.gz)
    version=pkg_info['__version__'],
    url=pkg_info['__url__'],
    project_urls={
        "Bug Tracker": "https://github.com/letuananh/bela/issues",
        "Source Code": "https://github.com/letuananh/bela/"
    },
    keywords=["corpus", "linguistics", "multilingual", "transcription",
              "ELAN", "NLP", "children", "language acquisition",
              "parent-child", "conversation", "discourse analysis"],
    license=pkg_info['__license__'],
    author=pkg_info['__author__'],
    tests_require=[],
    install_requires=requirements,
    python_requires=">=3.5",
    author_email=pkg_info['__email__'],
    description=pkg_info['__description__'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=['bela', 'bela.data'],
    package_data={'bela': ['data/*.gz']},
    include_package_data=True,
    platforms='any',
    test_suite='test',
    # Reference: https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=['Programming Language :: Python',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',
                 'Programming Language :: Python :: 3.10',
                 'Programming Language :: Python :: 3.11',
                 'Development Status :: {}'.format(pkg_info['__status__']),
                 'Natural Language :: English',
                 'Natural Language :: Chinese (Simplified)',
                 'Natural Language :: Malay',
                 'Natural Language :: Tamil',
                 'Environment :: Plugins',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: {}'.format(pkg_info['__license__']),
                 'Operating System :: OS Independent',
                 'Topic :: Text Processing',
                 'Topic :: Software Development :: Libraries :: Python Modules']
)
