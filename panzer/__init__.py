""" check that python3 is being used """
import sys

if sys.version_info[0] != 3:
    print("panzer cannot run --- it requires Python 3")
    sys.exit(1)
