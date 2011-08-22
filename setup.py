#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='hbcht',
    version='0.1.0',
    author='Niels Serup',
    author_email='ns@metanohi.name',
    package_dir={'': '.'},
    py_modules=['hbcht'],
    scripts=['hcbht'],
    url='http://metanohi.name/projects/hbcht/',
    license='AGPLv3+',
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
                 'License :: OSI Approved :: GNU Affero General Public License v3',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python 3'
                 ]
)
