from setuptools import setup, Command
import re
import os

description = 'Utility for simply creating and modifying VHDL bus slave modules'
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = 'Utility for simply creating and modifying VHDL bus slave modules'

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run():
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')

setup(
    name='bust',
    version='0.7',
    packages=['bust'],
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
        'console_scripts': ['bust = bust.__main__:main'],
    },
    test_suite='tests',
    author='Ola Groettvik',
    author_email='olagrottvik@gmail.com',
    url='http://github.com/olagrottvik/bust',
    keywords=['vhdl', 'bus', 'axi'],
    cmdclass={
        'clean': CleanCommand,
    }
)
