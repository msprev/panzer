#!/usr/bin/env python3
# encoding: utf-8

""" automated test framework for panzer

this will:
    -   run panzer on series of source files
    -   run pandoc on series of source files
    -   compare the outputs to ensure that they are the same

for more info: <https://github.com/msprev/panzer>

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
"""

import os
import subprocess
import itertools
import shutil
import spec
import time
import datetime
import sys

def main():
    """ the main function """
    # - parse command line arguments
    remit, sourcelist = parse_argument(sys.argv)
    if not remit:
        exit(1)
    # - if sourcelist not specified on commandline, do all sources
    if not sourcelist:
        os.chdir('source-'+remit)
        sourcelist = [name for name in os.listdir(".") if os.path.isdir(name)]
        os.chdir('..')
    initial_cleanup(sourcelist)
    print('changing working directory to "source-%s"' % remit)
    os.chdir('source-' + remit)
    # - start doing it
    start_time = time.time()
    print(pretty_title('start'))
    for source in sourcelist:
        print(pretty_title(source))
        # - move into source's directory
        os.chdir(source)
        # - build worklist of commands
        worklist = list()
        worklist += test_matrix(source)
        worklist += extra_tests(source)
        worklist = remove_blacklist(source, worklist)
        # - run the commands
        for i, command in enumerate(worklist):
            print('[%s:%d/%d] %s'
                  % (source, i+1, len(worklist), ' '.join(command)))
            # subprocess.call(command)
        # - move out of source's directory
        os.chdir('..')
    # - stop and cleanup
    print(pretty_title('end'))
    elapsed_time = time.time() - start_time
    print('time taken: %s (%f seconds)'
          % (str(datetime.timedelta(seconds=elapsed_time)),
             elapsed_time))

# def cleanup_debugfiles(source):
#     target = os.path.join(os.getcwd(), 'debug')
#     if os.path.exitst

def parse_arguments(argv):
    sourcelist = list()
    remit = None
    if len(argv) < 2:
        print('syntax: runtest.py REMIT [FILE1] [FILE2] ...')
        print('     where REMIT could be "pandoc" or "panzer"')
        print('     if no files are specified on the command line then all tests are run')
        sys.exit(1)
    if len(argv) == 2:
        sourcelist = sys.argv[1:]
    if len(argv) > 2:
        sourcelist = argv[2:]

def initial_cleanup(remit, sourcelist):
    """ initial setup for tests """
    print('* test run for "%s"' % remit)
    print('* files to test: ')
    print('    ' + str(sourcelist))
    print('* writers to test: ')
    print('    ' + str(spec.TEST['writer']))
    print('* pandoc options to test: ')
    print('    ' + str(spec.TEST['pandoc_options']))
    input("Press Enter to continue...")
    # - initial cleanup
    for source in sourcelist:
        os.chdir('output-'+remit)
        if os.path.exists(source):
            shutil.rmtree(source)
            print('removed existing "output-%s/%s"' % (remit, source))
        os.mkdir(source)
        os.chdir(source)
        os.mkdir('debug')
        os.chdir('..')
        os.chdir('..')
    input("Press Enter to continue...")

def test_matrix(source):
    """ return commands for running all combinations of TEST on source """
    # - list all comibinations of pandoc_options
    combos = [list(set(x))
              for x in list(itertools.combinations_with_replacement(
                  spec.TEST['pandoc_options'],
                  len(spec.TEST['pandoc_options'])))]
    # - remove duplicates from list
    combos.sort()
    combos = list(combos for combos, _ in itertools.groupby(combos))
    # - add the 'no options' option at the start
    combos.insert(0, [])
    worklist = list()
    # - create worklist for every writer and combination of pandoc_options
    for config in itertools.product(spec.TEST['writer'], combos):
        command = make_command(source=source,
                               writer=config[0],
                               pandoc_options=config[1])
        worklist.append(command)
    return worklist

def extra_tests(source):
    """ return commands for running EXTRA_TESTS """
    worklist = list()
    for config in spec.EXTRA_TESTS:
        command = make_command(source=source,
                               writer=config['writer'],
                               pandoc_options=config['pandoc_options'],
                               extension=config['extension'])
        worklist.append(command)
    return worklist

def remove_blacklist(oeuo, source, worklist):
    """ return worklist with anything in BLACKLIST removed """
    return worklist

def make_command(source=str(),
                 writer=str(),
                 extension=str(),
                 pandoc_options=str()):
    """ return command to run remit based on arguments """
    if not extension and writer:
        if writer in spec.DEFAULT_EXTENSION:
            extension = spec.DEFAULT_EXTENSION[writer]
        else:
            extension = '.XXX'
    command = [remit]
    command += [source + '.md']
    if writer:
        command += ['-t']
        command += [writer]
    command.extend(pandoc_options)
    command += ['-o']
    if writer == '':
        pretty_writer = 'default'
    else:
        pretty_writer = writer
    target_path = os.path.join(os.getcwd(),
                               '..', '..', 'output-'+remit, source,
                               source)
    target_path = os.path.normpath(target_path)
    command += [target_path
                + "_"
                + pretty_writer
                + ''.join(pandoc_options)
                + extension]
    if remit == 'panzer':
        command += ['---debug']
        target_path = os.path.join(os.getcwd(),
                                   '..', '..', 'output-'+remit, source, 'debug',
                                   'debug_' + source)
        target_path = os.path.normpath(target_path)
        command += [target_path
                    + "_"
                    + pretty_writer
                    + ''.join(pandoc_options)]
    return command

def pretty_title(title):
    """ return pretty printed section title """
    output = '-' * 5 + ' ' + title + ' ' + '-' * 5
    return output


if __name__ == '__main__':
    main()
