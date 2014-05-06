#!/usr/bin/env python3

import glob
import os
import shutil
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools

TEMP_DIR = '.tmp'


def move_temp_files_out(filepath):
    """Moves temporary files out of .tmp directory

    Args:
        basename: name (without extension) of temporary files
    """
    target = panzertools.FileInfo(filepath)
    mangled_target = target.mangle()
    basename = mangled_target.basename()
    temp_path = os.path.join(target.parents(), TEMP_DIR)
    if not os.path.exists(temp_path):
        panzertools.log('DEBUG', 'no %s found' % temp_path)
        return
    pattern_to_match = basename + '.*'
    temp_files = glob.glob(os.path.join(temp_path, pattern_to_match))
    panzertools.log('INFO', 'moving files out of %s' % temp_path)
    for temp_file in temp_files:
        shutil.copy(temp_file, target.parents())
        panzertools.log('DEBUG', 'copying %s to %s' % (temp_file, target.parents()))


def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    if OPTIONS['pandoc']['output'] != '-':
        move_temp_files_out(OPTIONS['pandoc']['output'])

if __name__ == '__main__':
    main()
