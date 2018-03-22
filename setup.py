from setuptools import setup
import re

description = 'Utility for simply creating and modifying VHDL bus slave modules'
long_description = re.sub(
    "\`(.*)\<#.*\>\`\_",
    r"\1",
    str(open('README.md', 'rb').read()).replace(description, '')
)


setup(
    name='uart',
    version='0.5.0',
    packages=['uart'],
    license='MIT',
    install_requires=[
        'curses-menu==0.5.0',
        'docopt==0.6.2',
        'prettytable==0.7.2',
        'pylatexenc==1.2',
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
