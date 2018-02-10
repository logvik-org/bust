from setuptools import setup

setup(
    name='uart',
    version='0.3.4',
    packages=['uart'],
    license='MIT',
    install_requires=[
        'curses-menu==0.5.0',
        'docopt==0.6.2',
        'prettytable==0.7.2',
      ],
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': ['uart = uart.__main__:main'],
    },
    author='Ola Groettvik',
    author_email='olagrottvik@gmail.com',
    url='http://github.com/olagrottvik/art',
    keywords=['vhdl', 'bus', 'axi'],
)
