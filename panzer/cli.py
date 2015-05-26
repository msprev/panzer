""" command line options for panzer """
import argparse
import os
import shutil
import sys
import tempfile
from . import const
from . import version

PANZER_DESCRIPTION = '''
Panzer-specific arguments are prefixed by triple dashes ('---').
Other arguments are passed to pandoc.

  panzer default user data directory: "%s"
  pandoc executable: "%s"
''' % (const.DEFAULT_SUPPORT_DIR, shutil.which('pandoc'))

PANZER_EPILOG = '''
Copyright (C) 2015 Mark Sprevak
Web:  http://sites.google.com/site/msprevak
This is free software; see the source for copying conditions. There is no
warranty, not even for merchantability or fitness for a particular purpose.
'''

def parse_cli_options(options):
    """ parse command line options """
    #
    # disable pylint warnings:
    #     + Too many local variables (too-many-locals)
    #     + Too many branches (too-many-branches)
    # pylint: disable=R0912
    # pylint: disable=R0914
    #
    # 1. Parse options specific to panzer
    panzer_known, unknown = panzer_parse()
    # 2. Update options with panzer-specific values
    for field in panzer_known:
        val = panzer_known[field]
        if val:
            options['panzer'][field] = val
    # 3. Parse options specific to pandoc
    pandoc_known, unknown = pandoc_parse(unknown)
    # 2. Update options with pandoc-specific values
    for field in pandoc_known:
        val = pandoc_known[field]
        if val:
            options['pandoc'][field] = val
    # 3. Check for pandoc output being pdf
    if os.path.splitext(options['pandoc']['output'])[1].lower() == '.pdf':
        options['pandoc']['pdf_output'] = True
    # 4. Detect pandoc's writer
    # - first case: writer explicitly specified by cli option
    if options['pandoc']['write']:
        pass
    # - second case: html default writer for stdout
    elif options['pandoc']['output'] == '-':
        options['pandoc']['write'] = 'html'
    # - third case: writer set via output filename extension
    else:
        ext = os.path.splitext(options['pandoc']['output'])[1].lower()
        implicit_writer = const.PANDOC_WRITER_MAPPING.get(ext)
        if implicit_writer is not None:
            options['pandoc']['write'] = implicit_writer
        else:
            # - html is default writer for unrecognised extensions
            options['pandoc']['write'] = 'html'
    # 5. Input from stdin
    # - if one of the inputs is stdin then read from stdin now into
    # - temp file, then replace '-'s in input filelist with reference to file
    if '-' in options['pandoc']['input']:
        # Read from stdin now into temp file in cwd
        stdin_bytes = sys.stdin.buffer.read()
        with tempfile.NamedTemporaryFile(prefix='__panzer-',
                                         suffix='__',
                                         dir=os.getcwd(),
                                         delete=False) as temp_file:
            temp_filename = os.path.join(os.getcwd(), temp_file.name)
            options['panzer']['stdin_temp_file'] = temp_filename
            temp_file.write(stdin_bytes)
            temp_file.flush()
        # Replace all reference to stdin in pandoc cli with temp file
        for index, val in enumerate(options['pandoc']['input']):
            if val == '-':
                options['pandoc']['input'][index] = options['panzer']['stdin_temp_file']
    # 6. Remaining options for pandoc
    options['pandoc']['options'] = unknown
    print(options['pandoc'])
    return options

def panzer_parse():
    """ return list of arguments recognised by panzer + unknowns """
    panzer_parser = argparse.ArgumentParser(
        description=PANZER_DESCRIPTION,
        epilog=PANZER_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False)
    panzer_parser.add_argument("-h", "--help", '---help', '---h',
                               action="help",
                               help="show this help message and exit")
    panzer_parser.add_argument('-v', '--version', '---version', '---v',
                               action='version',
                               version=('%(prog)s ' + version.VERSION))
    panzer_parser.add_argument("---quiet",
                               action='store_true',
                               help='only print errors and warnings')
    panzer_parser.add_argument("---panzer-support",
                               help='.panzer directory')
    panzer_parser.add_argument("---debug",
                               help='filename to write .log and .json debug files')
    panzer_known_raw, unknown = panzer_parser.parse_known_args()
    panzer_known = vars(panzer_known_raw)
    return (panzer_known, unknown)

def pandoc_parse(args):
    """ return list of arguments recognised by pandoc + unknowns """
    pandoc_parser = argparse.ArgumentParser(prog='pandoc')
    pandoc_parser.add_argument('input', nargs='*')
    pandoc_parser.add_argument("--read", "-r", "--from", "-f")
    pandoc_parser.add_argument("--write", "-w", "--to", "-t")
    pandoc_parser.add_argument("--output", "-o")
    pandoc_parser.add_argument("--template")
    pandoc_parser.add_argument("--filter", nargs=1, action='append')
    pandoc_known_raw, unknown = pandoc_parser.parse_known_args(args)
    pandoc_known = vars(pandoc_known_raw)
    return (pandoc_known, unknown)

