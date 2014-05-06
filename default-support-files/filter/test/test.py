#!/usr/bin/env python

import json
import os
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools


def main():
    """docstring for main"""    
    ast = json.load(sys.stdin)
    sys.stdout.write(json.dumps(ast))
    sys.stdout.flush()

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
