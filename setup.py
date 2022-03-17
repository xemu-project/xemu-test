#!/usr/bin/env python3
from setuptools import setup


__version__ = '0.0.1'


setup(name='xemutest',
    version=__version__,
    description='xemu Automated Tests',
    author='Matt Borgerson',
    author_email='contact@mborgerson.com',
    url='https://github.com/mborgerson/xemu-test',
    packages=['xemutest'],
    include_package_data=True,
    package_data={'xemutest': ['data/**/*']},
    install_requires=[
        'pyfatx',
        'pywinauto; sys_platform == "win32"'
        ],
    python_requires='>=3.6'
    )
