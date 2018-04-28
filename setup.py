from setuptools import setup
import re
import os

description = 'Utility for simply creating and modifying VHDL bus slave modules'
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = 'Utility for simply creating and modifying VHDL bus slave modules'

setup(
    name='uart',
    version='0.5.5',
    packages=['uart'],
    license='MIT',
    install_requires=[
        'curses-menu==0.5.0',
        'docopt==0.6.2',
        'prettytable==0.7.2',
        'pylatexenc==1.2',
        'pypandoc==1.4',
      ],
    description=description,
    long_description=long_description,
    entry_points={
        'console_scripts': ['uart = uart.__main__:main'],
    },
    author='Ola Groettvik',
    author_email='olagrottvik@gmail.com',
    url='http://github.com/olagrottvik/art',
    keywords=['vhdl', 'bus', 'axi'],
)
