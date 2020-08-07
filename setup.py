#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""libvcs lives at <https://github.com/vcs-python/libvcs>."""
from setuptools import setup

about = {}
with open("libvcs/__about__.py") as fp:
    exec(fp.read(), about)

with open('requirements/base.txt') as f:
    install_reqs = [line for line in f.read().split('\n') if line]

with open('requirements/test.txt') as f:
    tests_reqs = [line for line in f.read().split('\n') if line]

readme = open('README.rst').read()
history = open('CHANGES').read().replace('.. :changelog:', '')


setup(
    name=about['__title__'],
    version=about['__version__'],
    url='http://github.com/vcs-python/libvcs/',
    download_url='https://pypi.python.org/pypi/libvcs',
    project_urls={
        'Documentation': about['__docs__'],
        'Code': about['__github__'],
        'Issue tracker': about['__tracker__'],
    },
    license=about['__license__'],
    author=about['__author__'],
    author_email=about['__email__'],
    description=about['__description__'],
    long_description=readme,
    include_package_data=True,
    install_requires=install_reqs,
    tests_require=tests_reqs,
    zip_safe=False,
    keywords=about['__title__'],
    packages=['libvcs'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Utilities',
        'Topic :: System :: Shells',
    ],
)
