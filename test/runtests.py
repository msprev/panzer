#!/usr/bin/env python3
# encoding: utf-8
"""
Automated test framework for panzer

syntax: runtest.py REMIT [SOURCE1] [SOURCE2] ...
    where REMIT could be "pandoc" or "panzer" or "diff"
    if no sources specified, then all sources are tested

runtest.py will:

-   Run panzer on source files, dumping output to output-panzer/
-   Run pandoc on source files, dumping output to output-pandoc/
-   Diff relevant outputs in output-panzer/ and output-pandoc/

Tests are specified in:

-   'panzer.md' files in source-panzer/
-   'pandoc.md' and 'pandoc_WRITER.md' files in source-pandoc/ (WRITER is name of writer to run with that input)
-   spec.py, which specifies the command line options and writers to test

To write a new test:

-   Write a panzer source file
-   Write a pandoc source file that will produce the same output file
-   Place them in numbered directories in source-panzer/ and source-pandoc/

# Limitations

-   Does not test binary writers (docx, odt, etc.) or pdf output
-   Does not test runlists

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
"""

# TODO implement logging functions

import datetime
import filecmp
import itertools
import os
import shutil
import spec
import subprocess
import sys
import time

def main():
    """ the main function """
    remit, sourcelist = parse_cli(sys.argv)
    if not remit:
        exit(1)
    if not sourcelist:
        sourcelist = get_all_sources(remit)
    if remit == 'diff':
        do_diff(sourcelist)
        exit(0)
    describe_tests(remit, sourcelist)
    print('--> Start test run')
    # input("    Press Enter to continue...")
    clean_outputs(remit, sourcelist)
    print('--> Running tests for %s' % remit)
    # input("    Press Enter to continue...")
    os.chdir('source-' + remit)
    start_time = time.time()
    run_tests(remit, sourcelist)
    elapsed_time = time.time() - start_time
    print('time taken: %s (%f seconds)'
          % (str(datetime.timedelta(seconds=elapsed_time)),
             elapsed_time))

def parse_cli(argv):
    """ return remit and sourcelist by parsing cli arguments """
    possible_remits = ['pandoc', 'panzer', 'diff']
    sourcelist = list()
    remit = None
    if len(argv) < 2 or argv[1] not in possible_remits:
        print(__doc__)
        sys.exit(1)
    if len(argv) >= 2:
        remit = argv[1]
    if len(argv) > 2:
        sourcelist = argv[2:]
    return remit, sourcelist

def get_all_sources(remit):
    """ return sourcelist populated with all sources """
    if remit == 'panzer' or remit == 'pandoc':
        os.chdir('source-'+remit)
        sourcelist = [name for name in os.listdir(".") if os.path.isdir(name)]
        os.chdir('..')
    else:
        # get the maximal list of sources for a diff
        pandoc_list = get_all_sources('pandoc')
        panzer_list = get_all_sources('panzer')
        sourcelist = list(set(pandoc_list+panzer_list))
        sourcelist.sort()
    return sourcelist

def describe_tests(remit, sourcelist):
    """ print info about tests to be run """
    print('* run tests with "%s"' % remit)
    print('* tests to run: ')
    for line in pretty_list(sourcelist, 7):
        print('    ' + line)
    print('* writers to test: ')

def clean_outputs(remit, sourcelist):
    """ delete the output files for all the sources of remit """
    for source in sourcelist:
        os.chdir('output-'+remit)
        if os.path.exists(source):
            shutil.rmtree(source)
            print('* deleted old "output-%s/%s"' % (remit, source))
        os.mkdir(source)
        # os.chdir(source)
        # os.mkdir('debug')
        # os.chdir('..')
        os.chdir('..')

def run_tests(remit, sourcelist):
    """ run all the tests for remit on sourcelist """
    for source in sourcelist:
        # - move into source's directory
        os.chdir(source)
        # - build worklist of commands
        commands = list()
        commands += test_matrix(remit, source)
        commands += extra_tests(remit, source)
        commands = remove_blacklist(remit, source, commands)
        # - run the commands
        for i, command in enumerate(commands):
            print('[test %s: %s of %d] %s'
                  % (source,
                     str(i+1).rjust(len(str(len(commands)))),
                     len(commands),
                     ' '.join(command)))
            subprocess.call(command)
        # - move out of source's directory
        os.chdir('..')

def test_matrix(remit, source):
    """ return worklist of commands for all combinations of TEST on source """
    # - list of all combinations of pandoc_options
    combos = [list(set(x))
              for x in list(itertools.combinations_with_replacement(
                  spec.TEST['pandoc_options'],
                  len(spec.TEST['pandoc_options'])))]
    # - remove duplicates from list
    combos.sort()
    combos = list(combos for combos, _ in itertools.groupby(combos))
    combos = [sorted(x) for x in combos]
    # - add the 'no options' option at the start of list
    combos.insert(0, [])
    commands = list()
    # - create worklist for every writer and combination of pandoc_options
    for config in itertools.product(spec.TEST['writer'], combos):
        command = make_command(remit=remit,
                               source=source,
                               writer=config[0],
                               pandoc_options=config[1])
        commands.append(command)
    return commands

def extra_tests(remit, source):
    """ return commands for running EXTRA_TESTS """
    commands = list()
    for config in spec.EXTRA_TESTS:
        command = make_command(remit=remit,
                               source=source,
                               writer=config['writer'],
                               pandoc_options=config['pandoc_options'],
                               extension=config['extension'])
        commands.append(command)
    return commands

def remove_blacklist(remit, source, commands):
    """ return worklist with anything in BLACKLIST removed """
    return commands

def make_command(remit=str(),
                 source=str(),
                 writer=str(),
                 extension=str(),
                 pandoc_options=str()):
    """ return command to run remit on source based on arguments """
    # if no extension specified, infer it from writer
    if not extension and writer:
        if writer in spec.DEFAULT_EXTENSION:
            extension = spec.DEFAULT_EXTENSION[writer]
        else:
            print('WARNING: No known extension for writer "%s", '
                  'using ".UNKNOWN"' % writer)
            extension = '.UNKNOWN'
    # start building the command...
    # remit
    command = [remit]
    # input file
    # - if remit_WRITER.md exists, then use it!
    writer_specific_source = remit + '_' + writer + '.md'
    if os.path.exists(writer_specific_source):
        command += [writer_specific_source]
    else:
        command += [remit + '.md']
    # writer
    if writer:
        command += ['-t']
        command += [writer]
    # other options
    command.extend(pandoc_options)
    # output
    # - first build output filename...
    if writer == '':
        pretty_writer_string = 'default'
    else:
        pretty_writer_string = writer
    target = os.path.join(os.getcwd(), '..', '..', 'output-'+remit,
                          source,
                          pretty_writer_string
                          + ''.join(pandoc_options)
                          + extension)
    target = os.path.normpath(target)
    target = os.path.relpath(target)
    command += ['-o']
    command += [target]
    # panzer-specific options
    if remit == 'panzer':
        # support directory
        command += ['---panzer-support']
        target = os.path.join(os.getcwd(), '..', '..', 'dot-panzer')
        target = os.path.normpath(target)
        target = os.path.relpath(target)
        command += [target]
        # debug outputs
        # command += ['---debug']
        # target = os.path.join(os.getcwd(), '..', '..', 'output-'+remit,
        #                       source, 'debug', 'debug_' + source)
        # target = os.path.normpath(target)
        # command += [target
        #             + "_"
        #             + pretty_writer_string
        #             + ''.join(pandoc_options)]
    # done!
    return command

def pretty_title(title):
    """ return pretty printed section title """
    output = '-' * 5 + ' ' + title + ' ' + '-' * 5
    return output

def do_diff(sourcelist):
    """ diff the pandoc and panzer output directories """
    for source in sourcelist:
        dc = filecmp.dircmp('output-pandoc/'+source, 'output-panzer/'+source)
        if dc.right_only or dc.left_only or dc.diff_files:
            print(pretty_title(source))
        if dc.right_only:
            print('* only in output-panzer/%s:' % source)
            for line in pretty_list(dc.right_only):
                print('    ' + line)
        if dc.left_only:
            print('* only in output-pandoc/%s:' % source)
            for line in pretty_list(dc.left_only):
                print('    ' + line)
        if dc.diff_files:
            print('* differing:')
            for line in pretty_list(dc.diff_files):
                print('    ' + line)

def pretty_list(keys, num=3):
    """ return pretty printed list of dictionary keys, num per line """
    if not keys:
        return []
    # - turn into sorted list
    keys.sort()
    # - fill with blank elements to width num
    missing = (len(keys) % num)
    if missing != 0:
        to_add = num - missing
        keys.extend([''] * to_add)
    # - turn into 2D matrix
    matrix = [[keys[i+j] for i in range(0, num)]
              for j in range(0, len(keys), num)]
    # - calculate max width for each column
    len_matrix = [[len(col) for col in row] for row in matrix]
    max_len_col = [max([row[j] for row in len_matrix])
                   for j in range(0, num)]
    # - pad with spaces
    matrix = [[row[j].ljust(max_len_col[j]) for j in range(0, num)]
              for row in matrix]
    # - return list of lines to print
    matrix = ['  '.join(row) for row in matrix]
    return matrix

if __name__ == '__main__':
    main()
