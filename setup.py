from setuptools import setup, Command, find_packages
import re
import os

description = 'Utility for simply creating and modifying VHDL bus slave modules'
with open("README.md", "r") as fh:
    long_description = fh.read()

class clean(Command):
    """Custom clean command to tidy up the project root."""
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        os.system("find . -name '*.pyc' -delete")
        os.system("find . -name '__pycache__' -delete")
        os.system('rm -rf ./build ./dist ./*.tgz ./*.egg-info ./.pytest_cache ./.eggs')

setup(
    name='bust',
    version='0.9.1',
    packages=find_packages(),
    license='MIT',
    install_requires=[
        'docopt>=0.6.2',
        'pylatexenc>=1.2',
      ],
    python_requires='~=3.4', # For Python 3.4 and up, but not yet Python 4
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': ['bust = bust.__main__:main'],
    },
    test_suite='tests',
    author='Ola Groettvik',
    author_email='olagrottvik@gmail.com',
    url='http://github.com/olagrottvik/bust',
    keywords=['vhdl', 'bus', 'axi'],
    cmdclass={
        'clean': clean,
    }
)
