#!/usr/bin/env python3

import glob
import os
import shutil
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools

TEMP_DIR = '.tmp'


def move_temp_files_back(filepath):
    """Moves temporary files back into .tmp directory,

    Creates new .tmp if doesn't already exist

    Args:
        fullpath: fullpath to mangle
    """
    target = panzertools.FileInfo(filepath)
    mangled_target = target.mangle()
    basename = mangled_target.basename()
    pattern_to_match = basename + '.*'
    temp_path = os.path.join(target.parents(), TEMP_DIR)
    # check whether .tmp already exists...
    if os.path.exists(temp_path):
        # if .tmp exists, delete old temp files in it
        temp_files = glob.glob(os.path.join(temp_path, pattern_to_match))
        for temp_file in temp_files:
            os.remove(temp_file)
            panzertools.log('DEBUG', 'deleting %s' % temp_path)
    else:
        # otherwise make a new .tmp
        os.makedirs(temp_path)
        panzertools.log('DEBUG', 'creating %s' % temp_path)
    # move current temp files from current dir into .tmp
    panzertools.log('INFO', 'moving files back to %s' % temp_path)
    temp_files = glob.glob(os.path.join(target.parents(), pattern_to_match))
    for temp_file in temp_files:
        shutil.move(temp_file, temp_path)
        panzertools.log('DEBUG', 'moving %s to %s' % (temp_file, temp_path))


def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    if OPTIONS['pandoc']['output'] != '-':
        move_temp_files_back(OPTIONS['pandoc']['output'])


if __name__ == '__main__':
    main()
