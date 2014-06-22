import sys

if sys.version_info[0] != 3:
    print("error: panzer requires Python 3")
    sys.exit(1)

from .panzer import *
