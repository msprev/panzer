#!/usr/bin/env python

"""Panzer provides an elegant and powerful tool to drive pandoc using
styles.

Style are combinations of templates, default variable settings, filters,
postprocessers, pre- and post-flight scripts, and options for those
scripts. Styles can be reused and customised in a flexible way. Panzer
allows you to manage styles via a simple configuration file and a metadata
field in your document.

All command line options to panzer, with the exception of the
panzer-specific options below, are passed tranparently to pandoc.

Author:     Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright:  Copyright 2013, Mark Sprevak
License:    BSD3
"""

__version__            = "0.1"
REQUIRE_PANDOC_ATLEAST = "1.12.1"

PANZER_HELP_DESCRIPTION = '''
Panzer provides an elegant and powerful way of driving pandoc using styles.

Command line options, with the exception of the triple-dashed (---)
panzer-specific ones below, are passed to pandoc.
'''

PANZER_HELP_EPILOG = '''
Copyright (C) 2013 Mark Sprevak
Web:  http://sites.google.com/site/msprevak
This is free software; see the source for copying conditions. There is no
warranty, not even for merchantability or fitness for a particular purpose.
'''

import argparse
import glob
import json
import logging
import logging.config
import os
import re
import shutil
import subprocess
import sys
import tempfile
import yaml
from   distutils.version import StrictVersion

TEMP_DIR               = '.tmp'
DEFAULT_SUPPORT_DIR    = os.path.join(os.path.expanduser('~'), '.panzer')

class PanzerError(Exception):
    pass

class PanzerSetupError(PanzerError):
    pass

default_styledef = {}

# default settings for command line arguments
cli_options = {
    'panzer': {
        'panzer_support' : DEFAULT_SUPPORT_DIR,
        'debug'          : False,
        'silent'         : False,
        'html'           : False,
        'stdin_temp_file': '',
        'style'          : ''
    },
    'pandoc': {
        'clioptions'      : [],
        'write'           : '',
        'output_filename' : '-',
        'input_filenames' : ['-'],
    }
}


PANDOC_WRITER_MAPPING = {
    ""          : "markdown", # empty extension
    ".tex"      : "latex",
    ".latex"    : "latex",
    ".ltx"      : "latex",
    ".context"  : "context",
    ".ctx"      : "context",
    ".rtf"      : "rtf",
    ".rst"      : "rst",
    ".s5"       : "s5",
    ".native"   : "native",
    ".json"     : "json",
    ".txt"      : "markdown",
    ".text"     : "markdown",
    ".md"       : "markdown",
    ".markdown" : "markdown",
    ".textile"  : "textile",
    ".lhs"      : "markdown+lhs",
    ".texi"     : "texinfo",
    ".texinfo"  : "texinfo",
    ".db"       : "docbook",
    ".odt"      : "odt",
    ".docx"     : "docx",
    ".epub"     : "epub",
    ".org"      : "org",
    ".asciidoc" : "asciidoc",
    ".pdf"      : "latex",
    ".fb2"      : "fb2",
    ".opml"     : "opml",
    ".1"        : "man",
    ".2"        : "man",
    ".3"        : "man",
    ".4"        : "man",
    ".5"        : "man",
    ".6"        : "man",
    ".7"        : "man",
    ".8"        : "man",
    ".9"        : "man"
}

def mangle(basename):
    """Creates names for temporary files

    Args:
        basename: A string with the name (without extension) to be mangled

    Returns:
        A string (input of 'this basefile name' returns '_this-basefile-name_')
    """
    mangled_name = '_' + basename.replace(' ','-') + '_'
    logger.debug('"%s" mangled to "%s"', basename, mangled_name)
    return mangled_name


def move_temp_files_out(basename):
    """Moves temporary files out of .tmp directory

    Args:
        basename: name (without extension) of temporary files
    """
    pattern_to_match = basename + '.*'
    temp_files       = glob.glob(os.path.join(TEMP_DIR, pattern_to_match))

    logger.info('moving files out of %s', TEMP_DIR)
    for temp_file in temp_files:
        shutil.copy(temp_file, '.')
        logger.debug('copying %s to .', temp_file)


def move_temp_files_back(basename):
    """Moves temporary files back into .tmp directory,

    Creates new .tmp if doesn't already exist

    Args:
        basename: name (without extension) of temporary files
    """
    pattern_to_match = basename + '.*'

    # check whether .tmp already exists...
    if os.path.exists(TEMP_DIR):
        # if .tmp exists, delete old temp files in it
        temp_files = glob.glob(os.path.join(TEMP_DIR, pattern_to_match))
        for temp_file in temp_files:
            os.remove(temp_file)
            logger.debug('deleting %s', temp_file)
    else:
        # otherwise make a new .tmp
        os.makedirs(TEMP_DIR)
        logger.debug('creating %s', TEMP_DIR)

    # move current temp files from current dir into .tmp
    logger.info('moving back to %s', TEMP_DIR)
    temp_files = glob.glob(pattern_to_match)
    for temp_file in temp_files:
        shutil.move(temp_file, TEMP_DIR)
        logger.debug('moving %s to %s', temp_file, TEMP_DIR)

def check_support_directory():
    """docstring for create_default_data_directory"""

    support = cli_options['panzer']['panzer_support']

    if support != DEFAULT_SUPPORT_DIR:
        if not os.path.exists(support):
            logger.error('Panzer support directory "%s" not found.', support)
            logger.info('Using default panzer support directory: %s' % DEFAULT_SUPPORT_DIR)
            support = DEFAULT_SUPPORT_DIR

    if not os.path.exists(DEFAULT_SUPPORT_DIR):
        logger.info('Default panzer support directory does not exist.')
        os.makedirs(DEFAULT_SUPPORT_DIR)
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'defaults'))
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'filters'))
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'postflight_scripts'))
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'postprocessors'))
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'preflight_scripts'))
        os.makedirs(os.path.join(DEFAULT_SUPPORT_DIR, 'templates'))
        logger.info('Created default panzer support directory: %s' % DEFAULT_SUPPORT_DIR)


    # read the style in the list
    # find the template
    # find the filters
    # run the filters
    #
    # currentdocument.remove('stylecustom')
    # metadata = dict()
    # metadata.update(style.default.all_styles.all_writers.metadata)
    # metadata.update(style.default.all_styles.current_writer.metadata)
    # metadata.update(style.default.current_style.all_writers.metadata)
    # metadata.update(style.default.current_style.current_writer.metadata)
    # metadata.update(customstyle.default.all_styles.all_writers.metadata)
    # metadata.update(customstyle.default.all_styles.current_writer.metadata)
    # metadata.update(customstyle.default.current_style.all_writers.metadata)
    # metadata.update(customstyle.default.current_style.current_writer.metadata)
    # metadata.update(currentdocument)
    #
    # new_temp_md_file(input_filename, temp_md_filename)
    # append_metadata_defaults(new_filename)

    #

def start_logger():
    """docstring for initialise_logger"""
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'short': {
                'format': 'panzer - %(levelname)s - %(message)s'
            },
            'html': {
                'format': '<div class"%(levelname)s">%(message)s</div>'
            }
        },
        'handlers': {
            'log_file_handler': {
                'class'        : 'logging.handlers.RotatingFileHandler',
                'level'        : 'DEBUG',
                'formatter'    : 'detailed',
                'filename'     : 'panzer.log',
                'maxBytes'     : '10485760',
                'backupCount'  : '5',
                'encoding'     : 'utf8'
            },
            'console': {
                'class'      : 'logging.StreamHandler',
                'level'      : 'INFO',
                'formatter'  : 'short',
                'stream'     : 'ext://sys.stdout'
            }
        },
        'loggers': {
            __name__: {
                'handlers'   : [ 'console', 'log_file_handler' ],
                'level'      : 'DEBUG',
                'propagate'  : True
            }
        }
    }

    ## Modify default logging option with settings from cli
    if not cli_options['panzer']['debug']:
        config['loggers'][__name__]['handlers'].remove('log_file_handler')
        del config['handlers']['log_file_handler']

    if cli_options['panzer']['silent']:
        config['handlers']['console']['level'] = 'CRITICAL'

    if cli_options['panzer']['html']:
        config['handlers']['console']['formatter'] = 'html'

    ## Configure and create the logger
    logging.config.dictConfig(config)
    global logger
    logger = logging.getLogger(__name__)


def check_pandoc_exists():
    """docstring for check_pandoc_exists"""
    try:
        stdout = subprocess.check_output(["pandoc", "--version"]).splitlines()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            raise PanzerSetupError('Pandoc not found')

    pandoc_version = re.sub('[^0-9.]', '', stdout[0])
    if StrictVersion(pandoc_version) < StrictVersion(REQUIRE_PANDOC_ATLEAST):
        raise PanzerSetupError('Pandoc %s or greater required. Found pandoc version %s' % (REQUIRE_PANDOC_ATLEAST, pandoc_version))


def parse_cli_options():
    """Parse the command line options passed to panzer, and print help text

    Sets the global variable `cli_options`.

    `cli_options` is a dict that holds all the options that apply to this
    invocation of panzer.
    """

    ## This function runs before logging starts so use print statements for debugging
    debug_cli = False

    ## Parse options specific to panzer
    panzer_parser = argparse.ArgumentParser(
        description     = PANZER_HELP_DESCRIPTION,
        epilog          = PANZER_HELP_EPILOG,
        formatter_class = argparse.RawTextHelpFormatter)
    panzer_parser.add_argument("---panzer-support", help='location of directory of support files for panzer')
    panzer_parser.add_argument("---debug", help='write debug info to `panzer.log`', action="store_true")
    panzer_parser.add_argument("---silent", help='suppress panzer-generated messages to console', action="store_true")
    panzer_parser.add_argument("---html", help='format console messages in HTML', action="store_true")
    panzer_parser.add_argument('---version', action='version', version=('%(prog)s ' + __version__))
    known, panzer_unknown = panzer_parser.parse_known_args()
    panzer_known = vars(known)

    ## Update cli_options with panzer-specific values passed from cli
    for key in panzer_known:
        value = panzer_known[key]
        if value is not None:
            cli_options['panzer'][key] = value

    if debug_cli:
        print '----------------------- panzer ------------------------------------'
        print 'Known:  ', json.dumps(panzer_known, indent=1)
        print 'Unknown:', json.dumps(panzer_unknown, indent=1)

    ## Parse options specific to pandoc
    pandoc_parser = argparse.ArgumentParser(prog='pandoc')
    pandoc_parser.add_argument("--write","-w","--to","-t", help='writer')
    pandoc_parser.add_argument("--output","-o", help='output')
    known, pandoc_unknown = pandoc_parser.parse_known_args(panzer_unknown)
    pandoc_known = vars(known)

    if debug_cli:
        print '----------------------- pandoc ------------------------------------'
        print 'Known:  ', json.dumps(pandoc_known, indent=1)
        print 'Unknown:', json.dumps(pandoc_unknown, indent=1)

    ## Update cli_options with input and output filenames for pandoc
    ## by running `pandoc --dump-args`. From pandoc's manual:
    ## --dump-args:
    ## Print information about command-line arguments to stdout, then exit. This option is intended primarily for use in wrapper scripts. The first line of output contains the name of the output file specified with the -o option, or - (for stdout) if no output file was specified. The remaining lines contain the command-line arguments, one per line, in the order they appear. These do not include regular Pandoc options and their arguments, but do include any options appearing after a -- separator at the end of the line.
    cmd = ["pandoc", "--dump-args"]
    cmd.extend(panzer_unknown)
    stdout = subprocess.check_output(cmd).splitlines()
    input_filenames = []
    output_filename = ''
    for index, line in enumerate(stdout):
        if index == 0:
            ## First line of --dump-args is output filename
            output_filename = line
        else:
            ## Other lines are input filenames
            input_filenames.append(line)
    if output_filename:
        cli_options['pandoc']['output_filename'] = output_filename
    if input_filenames:
        cli_options['pandoc']['input_filenames'] = input_filenames

    ## Update cli_options with pandoc's writer
    if pandoc_known['write']:
        ## First case: writer explicitly specified by cli option
        cli_options['pandoc']['write'] = pandoc_known['write']
    elif cli_options['pandoc']['output_filename'] == '-':
        ## Second case: html default writer for stdout
        cli_options['pandoc']['write'] = 'html'
    else:
        ## Third case: writer set via output filename extension
        ext = os.path.splitext(cli_options['pandoc']['output_filename'])[1].lower()
        implicit_writer = PANDOC_WRITER_MAPPING.get(ext)
        if implicit_writer is not None:
            cli_options['pandoc']['write'] = implicit_writer
        else:
            ## html is default writer for unrecognised extensions
            cli_options['pandoc']['write'] = 'html'

    ## Store all remaining cli options for pandoc in cli_options
    ## This is full list of options passed to panzer minus:
    ##      1. Panzer-specific options
    ##      2. -w option
    ##      3. -o option
    ##      4. - items for input files (replaced with temp filenames below)
    ## These all need to be replaced when pandoc runs internally in panzer
    cli_options['pandoc']['clioptions'] = pandoc_unknown

    ## If stdin one of the inputs then read from stdin into temp file and
    ## replace reference to stdin with reference to temporary file
    if '-' in cli_options['pandoc']['input_filenames']:
        ## Read from stdin now into temp file in cwd
        stdin = sys.stdin.read()
        fp = tempfile.NamedTemporaryFile(prefix='__stdin-panzer-', suffix='__', dir=os.getcwd(), delete=False)
        cli_options['panzer']['stdin_temp_file'] = os.path.join(os.getcwd(), fp.name)
        fp.write(stdin)
        fp.close()
        ## Replace all reference to stdin in pandoc cli with temp file
        for i, n in enumerate(cli_options['pandoc']['input_filenames']):
            if n == '-':
                cli_options['pandoc']['input_filenames'][i] = cli_options['panzer']['stdin_temp_file']
        for i, n in enumerate(cli_options['pandoc']['clioptions']):
            if n == '-':
                cli_options['pandoc']['clioptions'][i] = cli_options['panzer']['stdin_temp_file']

    if debug_cli:
        print '----------------------- cli_options -------------------------------'
        print json.dumps(cli_options, indent=1)

def pandoc2json(files_and_options):
    """docstring for pandoc2json"""
    cmd = ['pandoc']
    cmd.extend(files_and_options)
    cmd.extend(['--write', 'json', '--output', '-'])
    logger.debug('pandoc run to create single JSON output:')
    logger.debug(' '.join(cmd))
    output = json.loads(subprocess.check_output(cmd))
    return output

def load_defaults():
    """docstring for load_defaults"""
    filename = os.path.join(cli_options['panzer']['panzer_support'], 'defaults', 'defaults.yaml')
    try:
        stream = open(filename, 'r')
    except IOError, e:
        if e.errno == os.errno.ENOENT:
            logger.info('Defaults file not found: %s' % filename)
            return
    default_styledef = yaml.safe_load(stream)

# class document (Object):
#     self.full_ast       = {}
#     self.metadata       = {}
#     self.style          = ''
#     self.filters        = []
#     self.postprocessors = []
# 
# def __init__(self, full_ast):
#     """docstring for __init__"""
#     # set the metadata, style, etc
#     pass
# 
# def transform(self, default_styledef, style, writer):
#     """docstring for transform"""
#     pass
# 
# def extract_preflight(self, default_styledef, style, writer):
#     """docstring for extract_preflight"""
#     pass
# 
# def update_full_ast(self, metadata):
#     """docstring for update_full_ast"""
#     pass


def main():
    """This is the main.
    Here is the documentation.
    """
    try:
        check_pandoc_exists()
        parse_cli_options()
        start_logger()
        logger.info('panzer started -----')
        check_support_directory()
        load_defaults()
        mydoc = document(pandoc2json(cli_options['pandoc']['clioptions']))
        # print json.dumps(document, indent=1)

        # transform_doc(document, default_styledef, cli_options['panzer']['style'], cli_options['pandoc']['write'])

    except PanzerSetupError, e:
        # Catch errors that occur before logging starts
        print(e)
        sys.exit(1)
    except subprocess.CalledProcessError:
        logger.critical('Panzer cannot continue because pandoc failed')
        sys.exit(1)

    finally:
        if cli_options['panzer']['stdin_temp_file']:
            os.remove(cli_options['panzer']['stdin_temp_file'])
            logger.debug('Deleted temp file: %s' % cli_options['panzer']['stdin_temp_file'])
        logger.info('panzer quitting ----')

    sys.exit(0)

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
