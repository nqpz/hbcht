#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='hbcht',
    version='0.1.1',
    author='Niels G. W. Serup',
    author_email='ngws@metanohi.name',
    package_dir={'': '.'},
    py_modules=['hbcht'],
    scripts=['hbcht'],
    url='http://metanohi.name/projects/hbcht/',
    license='WTFPL',
    description='A combined interpreter and compiler for the Half-Broken Car in Heavy Traffic programming language',
    long_description=open('README.txt').read(),
    classifiers=['Development Status :: 3 - Alpha',
                 'Intended Audience :: Developers',
                 'Intended Audience :: Education',
                 'Environment :: Console',
                 'Topic :: Utilities',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 'Topic :: Other/Nonlisted Topic',
                 'License :: DFSG approved',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 3'
                 ]
)
