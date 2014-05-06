#!/usr/bin/env python3

import json
import os
import subprocess
import shutil
import sys
import re
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools
from resources import parseTeXlog

def print_log(filename):
    """docstring for print_log"""
    basename = os.path.splitext(filename)[0]
    basename_ = panzertools.mangle(basename)
    print_debug = True
    interactive = True
    warning = []

    try:
        logfilename = basename_ + '.log'
        data = open(logfilename, 'r').read()
        (errors, warnings) = parseTeXlog.parse_tex_log(data)

    except Exception as e:
        import traceback
        traceback.print_exc()

    for line in warnings:
        line = ' '.join(line.split())
        line = line.replace(basename_ + '.tex', basename + '.tex')
        line = line.replace('./'+ basename + '.tex', basename + '.tex')
        # re.sub( '\s+', ' ', x ).strip()
        # re.sub(basename_ + '.tex', basename + '.tex', x)
        panzertools.log('WARNING', line)

    for line in errors:
        panzertools.log('ERROR', line)

    panzertools.log('INFO', '%d warnings    %d errors' % (len(warnings), len(errors)))

def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    filename = OPTIONS['pandoc']['output']
    if filename != '-':
        print_log(OPTIONS['pandoc']['output'])


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()

