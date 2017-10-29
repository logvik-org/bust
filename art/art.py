"""art - axi register tool

Usage:
  art.py FILE [-o DIR]
  art.py -c [-o DIR]
  art.py --version
  art.py -h | --help

Options:
  -o DIR         Specify output directory
  -c             Start menu-based creation of JSON file
  -h --help      HELP!
  --version   Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

    

    
