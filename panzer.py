#!/usr/bin/env python

"""Panzer provides a way to drive pandoc using styles.

Style are combinations of templates, default variable settings, filters,
postprocessers, pre- and post-flight scripts, and options for those
scripts. Styles can be reused and customised in a flexible way. Panzer
allows you to manage styles via metadata keys in your document.

All command-line options to panzer, with the exception of the
panzer-specific options listed below, are passed to pandoc.

Author:     Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright:  Copyright 2013, Mark Sprevak
License:    BSD3
"""

import argparse
import json
import logging
import logging.config
import os
import re
import subprocess
import shlex
import sys
import tempfile
import time
from   distutils.version import StrictVersion
from pandocfilters import stringify

## -----------------------------------------------------------
## Constants
## -----------------------------------------------------------

__version__            = "1.0"
REQUIRE_PANDOC_ATLEAST = "1.12.1"
DEFAULT_SUPPORT_DIR    = os.path.join(os.path.expanduser('~'), '.panzer')
REMOTE_URL             = "https://github.com/msprev/.panzer.git"
T                      = 't'
C                      = 'c'
ADDITIVE_KEYS          = ['filter', 'postprocess', 'preflight', 'postflight']
PANZER_KEYS            = ['default', 'template'] + ADDITIVE_KEYS

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

# Taken from https://github.com/jgm/pandoc/blob/master/pandoc.hs#L841
PANDOC_WRITER_MAPPING = {
    ""          : "markdown",
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

## -----------------------------------------------------------
## Global variables
## -----------------------------------------------------------

# pylint: disable=C0103
logger           = logging.getLogger(__name__)
TIMING_DATA = []
OPTIONS      = {
    'panzer': {
        'support' : DEFAULT_SUPPORT_DIR,
        'debug'          : False,
        'silent'         : False,
        'html'           : False,
        'stdin_temp_file': ''
    },
    'pandoc': {
        'options'         : [],
        'write'           : '',
        'output'          : '-',
        'input'           : ''
    }
}


## -----------------------------------------------------------
## Exception classes
## -----------------------------------------------------------

class PanzerError(Exception):
    """docstring for getMetadataFromAST"""
    pass

class PanzerSetupError(PanzerError):
    """docstring for getMetadataFromAST"""
    pass

class PanzerBadASTError(PanzerError):
    """docstring for getMetadataFromAST"""
    pass

class PanzerKeyError(PanzerError):
    """docstring for getMetadataFromAST"""
    pass

class PanzerTypeError(PanzerError):
    """docstring for getMetadataFromAST"""
    pass

class PanzerCommandNotFound(PanzerError):
    """docstring for getMetadataFromAST"""
    pass


## -----------------------------------------------------------
## Document class
## -----------------------------------------------------------

class Document(object):

    def __init__(self, ast=None):
        """docstring for __init__"""
        self.ast          = {}
        self.metadata     = {}
        self.template     = None
        self.style        = None
        if ast:
            self.ast      = ast
            self.metadata = self.get_ast_metadata()
            try:
                # pylint: disable=C0301
                self.style = stringify(get_content(self.metadata, 'style', 'MetaInlines'))
            except PanzerKeyError:
                pass
            except PanzerTypeError as error:
                logger.warning(error)


    def get_ast_metadata(self):
        """docstring for getMetadataFromAST"""
        try:
            return self.ast[0]['unMeta']
        except KeyError:
            logger.warning('No metadata found in source documents')
            return None

    def set_ast_metadata(self, new_metadata):
        """docstring for getMetadataFromAST"""
        self.ast[0]['unMeta'] = new_metadata


    def transform(self, defaults, style, writer):
        """docstring for transform"""
        start_time = time.clock()

        # pylint: disable=C0301
        new_metadata = update_metadata({},           get_nested_content(defaults.metadata, ['all_styles', 'all_writers'], 'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(defaults.metadata, ['all_styles', writer],        'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(defaults.metadata, [style, 'all_writers'],        'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(defaults.metadata, [style, writer],               'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(self.metadata,     ['all_styles', 'all_writers'], 'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(self.metadata,     ['all_styles', writer],        'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(self.metadata,     [style, 'all_writers'],        'MetaMap'))
        new_metadata = update_metadata(new_metadata, get_nested_content(self.metadata,     [style, writer],               'MetaMap'))
        new_metadata.update(self.metadata)

        # remove unneeded style keys from metadata
        if 'all_styles' in new_metadata:
            del new_metadata['all_styles']
        if style in new_metadata:
            del new_metadata[style]

        # update additive lists
        for key in ADDITIVE_KEYS:
            try:
                updated_list = apply_kill_rules(get_content(new_metadata, key, 'MetaList'))
                if updated_list:
                    set_content(new_metadata, key, updated_list, 'MetaList')
                else:
                    # if all items have been killed, delete the key
                    del new_metadata[key]
            except PanzerKeyError:
                continue
            except PanzerTypeError as error:
                logger.warning(error)
                continue

        # update template info
        try:
            self.template = stringify(get_content(new_metadata, 'template', 'MetaInlines'))
        except (PanzerKeyError, PanzerTypeError) as error:
            logger.warning(error)

        self.metadata = new_metadata
        self.set_ast_metadata(new_metadata)
        TIMING_DATA.append(('tranform metadata', time.clock() - start_time))

    def run_filters(self, commands):
        """docstring for run_filters"""
        processes = []
        
        # Using a temp file to give input data to the subprocess instead of stdin.write to avoid deadlocks.
        f = tempfile.TemporaryFile()
        f.write(json.dumps(self.ast))
        # Return at the start of the file so that the subprocess p1 can read what we wrote.
        f.seek(0)  
        
        for index, command in enumerate(commands['filter']):
            logger.info('applying filter: "%s"', ' '.join(command))
            subprocess_time = time.clock()
            ## insert writer as first argument to filters
            # command.insert(1, OPTIONS['pandoc']['write'])

            if index == 0:
                ## first filter
                try:
                    p = subprocess.Popen(command, stdin=f, 
                                                  stdout=subprocess.PIPE)
                except ENOENT
                    processes.append(p)
                                                 
            else:
                ## all subsequent filters
                p = subprocess.Popen(command, stdin=processes[index-1].stdout, 
                                              stdout=subprocess.PIPE)
                processes.append(p)

            TIMING_DATA.append(('filter: ' + command[0], time.clock() - subprocess_time))

        # close all but the last process to ensure everything gone through
        for index in range(len(commands['filter']) - 1):
                processes[index].stdout.close()
        
        # Using communicate() instead of stdout.read to avoid deadlocks
        stdout = processes[-1].communicate()[0]
        self.ast = json.loads(stdout)


## -----------------------------------------------------------
## Manipulate metadata
## -----------------------------------------------------------

def check_C_and_T_exist(item):
    """docstring for well_formed"""
    if C not in item:
        raise PanzerBadASTError('Value of "%s" corrupt: "C" key missing'
                                % repr(item))
    if T not in item:
        raise PanzerBadASTError('Value of "%s" corrupt: "T" key missing'
                                % repr(item))


def set_content(dictionary, key, content, tag):
    dictionary[key] = {C: content, T: tag}


def get_nested_content(dictionary, keys, expected_type_of_leaf=None):
    """docstring for get_nested_content"""
    key = keys.pop(0)
    try:
        if keys:
        # on a branch...
            return get_nested_content(                              \
                        get_content(dictionary, key, 'MetaMap'),    \
                        keys,                                       \
                        expected_type_of_leaf)
        else:
        # on the leaf...
            return get_content(dictionary, key, expected_type_of_leaf)
    except PanzerKeyError:
        # key not found, return {}: nothing to update
        return {}
    except PanzerTypeError as error:
        logger.warning(error)
        # wrong type found, return {}: nothing to update
        return {}


def get_content(dictionary, key, expected_type=None):
    """docstring for get_content"""
    if key not in dictionary:
        raise PanzerKeyError('Key "%s" not found' % key)

    check_C_and_T_exist(dictionary[key])

    if expected_type:
        found_type = dictionary[key][T]
        if found_type != expected_type:
            raise PanzerTypeError('Value of "%s": expecting type "%s", but '
                                  'found type "%s"' %
                                  (key, expected_type, found_type))
    return dictionary[key][C]


def get_tag(dictionary, key):
    """docstring for get_tag"""
    if key not in dictionary:
        raise PanzerKeyError('Key "%s" not found' % key)

    check_C_and_T_exist(dictionary[key])

    return dictionary[key][T]


def update_metadata(dictionary, incoming):

    ## values listed in 'default' get moved to global scope
    try:
        dictionary.update(get_content(incoming, 'default', 'MetaMap'))
        del incoming['default']
    except (PanzerKeyError, KeyError):
        pass
    except PanzerTypeError as error:
        logger.warning(error)

    ## lists get added rather than overwritten
    for key in ADDITIVE_KEYS:
        try:
            try:
                new_list = get_content(incoming, key, 'MetaList')
            except PanzerKeyError:
                # key not in incoming metadata, move to next list
                continue
            try:
                old_list = get_content(dictionary, key, 'MetaList')
            except PanzerKeyError:
                # key not in old metadata, start with an empty list
                old_list = []
        except PanzerTypeError as error:
            # wrong type, skip to next list
            logger.warning(error)
            continue
        old_list.extend(new_list)
        set_content(dictionary, key, old_list, 'MetaList')
        del incoming[key]

    # update all other keys, including 'template'
    dictionary.update(incoming)
    return dictionary


def apply_kill_rules(old_list):
    """docstring for applyKillRules"""
    # pylint: disable=R0912
    new_list = []
    for item in old_list:

        check_C_and_T_exist(item)

        item_content = item[C]
        item_tag     = item[T]

        # syntax check on item
        if item_tag != 'MetaMap':
            message =  'Keys "' + '", "'.join(ADDITIVE_KEYS) + '" '
            message += 'value must be of type "MetaMap". Ignoring 1 item.'
            logger.error(message)
            continue
        if len(item_content.viewkeys() & {'run', 'kill', 'killall'}) != 1:
            message =  'Keys "' + '", "'.join(ADDITIVE_KEYS) + '" '
            message += 'must contain exactly one "run", "kill", or "killall" '
            message += 'per item. Ignoring 1 item.'
            logger.error(message)
            continue

        # now operate on content
        if 'run' in item_content:
            # syntax check
            if get_tag(item_content, 'run') != 'MetaInlines':
                logger.error('"run" value must be of type "MetaInlines". '
                             'Ignoring 1 item.')
                continue
            new_list.append(item)

        elif 'kill' in item_content:
            try:
                to_be_killed = get_content(item_content, 'kill', 'MetaInlines')
            except PanzerTypeError as error:
                logger.warning(error)
                continue
            new_list = [ new_item for new_item in new_list if               \
                         get_content(new_item[C], 'run', 'MetaInlines') !=  \
                         to_be_killed]

        elif 'killall' in item_content:
            try:
                if get_content(item_content, 'killall', 'MetaBool') == True:
                    new_list = []
            except PanzerTypeError as error:
                logger.warning(error)
                continue
        else:
            ## Should never occur, caught by previous syntax check
            continue

    if new_list:
        return new_list
    else:
        return None


## -----------------------------------------------------------
## Load documents
## -----------------------------------------------------------

def load(files_and_options):
    """docstring for pandoc2json"""
    start_time = time.clock()
    cmd = ['pandoc'] + files_and_options + ['--write', 'json', '--output', '-']
    logger.debug('running: "' + ' '.join(cmd) + '"')
    json_dict = json.loads(subprocess.check_output(cmd))
    TIMING_DATA.append(('load files', time.clock() - start_time))
    return Document(json_dict)


def load_defaults():
    """docstring for load_defaults"""
    filename = os.path.join(OPTIONS['panzer']['support'],
                    'defaults',
                    'defaults.yaml')
    if os.path.exists(filename):
        json_dict = load([filename])
        # tweak timing data label
        label, timing = TIMING_DATA.pop()
        TIMING_DATA.append(('load defaults', timing))
        return json_dict
    else:
        logger.error('Defaults file not found: %s', filename)
        return Document()


## -----------------------------------------------------------
## Filters and pre/postflight script functions
## -----------------------------------------------------------


def run_scripts(commands, kind):
    """docstring for run_preflight"""
    for command in commands[kind]:
        subprocess_time = time.clock()
        logger.info('running %s: "%s"', kind, ' '.join(command))
        command[0] = get_path_to_command(command[0], kind)
        try:
            p = subprocess.Popen(command, stdin=subprocess.PIPE)
            ## send panzer's OPTIONS as json to scripts via stdin
            p.communicate(input=json.dumps(OPTIONS))
        except OSError as error:
            if error.errno == os.errno.ENOENT:
                logger.error('"%s" file not found', command[0])
                continue
        TIMING_DATA.append(('%s: %s' % (kind, command[0]), \
                           time.clock() - subprocess_time))


def run_postprocessors(commands):
    """docstring for run_filters"""
    for cmd in commands['postprocess']:
        logger.info('applying postprocessor: "%s"', ' '.join(cmd))
        subprocess_time = time.clock()
        # subprocess.check_call(cmd)
        TIMING_DATA.append(                                         \
            ('postprocess: ' + cmd[0], time.clock() - subprocess_time))


def build_commands(dictionary):
    """docstring for buildCommands"""
    start_time = time.clock()
    commands = {}

    for key in ADDITIVE_KEYS:
        if key in dictionary:
            command_list = build_command(dictionary, key)
            if command_list:
                commands[key] = command_list

    TIMING_DATA.append(('build commands', time.clock() - start_time))
    return commands


def build_command(dictionary, key):
    """docstring for buildCommand"""
    command_list  = []

    try:
        metadata_list = get_content(dictionary, key, 'MetaList')
    except (PanzerTypeError, PanzerKeyError) as error:
        logger.warning(error)
        return []

    for item in metadata_list:

        check_C_and_T_exist(item)
        item_content = item[C]

        command = stringify(get_content(item_content, 'run', 'MetaInlines'))
        command = [ get_path_to_command(command, key) ]

        options = []
        if 'options' in item_content:
            if get_tag(item_content, 'options') == 'MetaInlines':
                # pylint: disable=C0301
                # raw string of options
                options = shlex.split(stringify(get_content(item_content, 'options', 'MetaInlines')))
            elif get_tag(item_content, 'options') == 'MetaMap':
                # options specified in yaml
                options_dict = get_content(item_content, 'options', 'MetaMap')
                options = parse_options_dict(options_dict)
            command.extend(options)
        command_list.append(command)

    return command_list


def get_path_to_command(command, key):
    """docstring for find_shell_command"""
    paths = []
    basename = os.path.splitext(command)[0]
    ## first check current directory, then support directory
    paths.append(command)
    paths.append(os.path.join(OPTIONS['panzer']['support'],
                              key, basename, command))
    for path in paths:
        if os.path.exists(path):
            return path

    ## If no path found, assume command is somewhere in shell
    ## when subprocess is called. So, run the command as is
    return command


def parse_options_dict(options_dict):
    """docstring for parseOptions"""
    options = []

    for key in options_dict:
        value_tag = get_tag(options_dict, key)

        # pylint: disable=C0301
        if value_tag == 'MetaBool' and get_content(options_dict, key, 'MetaBool') == True:
            options.append('--' + key)
        elif value_tag == 'MetaInlines':
            # pylint: disable=C0301
            options.append('--%s="%s"' % (key, stringify(get_content(options_dict, key, 'MetaInlines'))))
        else:
            logger.error('Option values of type "%s" not supported,'
                         '"%s" ignored.', value_tag, key)

    return options


## -----------------------------------------------------------
## Support functions for non-core operations
## -----------------------------------------------------------

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
                'format': '%(levelname)s - %(message)s'
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
    if not OPTIONS['panzer']['debug']:
        ## ---debug flag not set...
        config['loggers'][__name__]['handlers'].remove('log_file_handler')
        del config['handlers']['log_file_handler']

    if OPTIONS['panzer']['silent']:
        ## ---silent flag set...
        config['handlers']['console']['level'] = 'CRITICAL'

    if OPTIONS['panzer']['html']:
        ## ---html flag set...
        config['handlers']['console']['formatter'] = 'html'

    ## Configure the logger
    logging.config.dictConfig(config)


def check_pandoc_exists():
    """docstring for check_pandoc_exists"""
    start_time = time.clock()
    try:
        stdout = subprocess.check_output(["pandoc", "--version"]).splitlines()
    except OSError as error:
        if error.errno == os.errno.ENOENT:
            raise PanzerSetupError('Pandoc not found')

    pandoc_version = re.sub('[^0-9.]', '', stdout[0])
    if StrictVersion(pandoc_version) < StrictVersion(REQUIRE_PANDOC_ATLEAST):
        raise PanzerSetupError('Pandoc %s or greater required.'
                               'Found pandoc version %s' %
                               (REQUIRE_PANDOC_ATLEAST, pandoc_version))
    TIMING_DATA.append(('check pandoc exists', time.clock() - start_time))


def check_support_directory():
    """docstring for create_default_data_directory"""

    support = OPTIONS['panzer']['support']

    if support != DEFAULT_SUPPORT_DIR:
        if not os.path.exists(support):
            logger.error('Panzer support directory "%s" not found.',
                         support)
            logger.info('Using default panzer support directory: %s',
                         DEFAULT_SUPPORT_DIR)
            support = DEFAULT_SUPPORT_DIR

    if not os.path.exists(DEFAULT_SUPPORT_DIR):
        logger.error('Default panzer support directory does not exist.')
        logger.info('Attempting to download support from %s',
                    REMOTE_URL)
        return_code = subprocess.call(["git", "clone",
                                       REMOTE_URL, DEFAULT_SUPPORT_DIR])
        if return_code == 0:
            logger.info('Successfully downloaded panzer support to: %s',
                        DEFAULT_SUPPORT_DIR)
        else:
            logger.error('Failed attempt to clone from %s', REMOTE_URL)


def parse_cli_options():
    """Parse the command line options passed to panzer, and print help text

    Sets the global variable `OPTIONS`.

    `OPTIONS` is a dict that holds all the options that apply to this
    invocation of panzer.
    """
    # pylint: disable=R0914
    start_time = time.clock()
    ## Parse options specific to panzer
    panzer_parser = argparse.ArgumentParser(
        description     = PANZER_HELP_DESCRIPTION,
        epilog          = PANZER_HELP_EPILOG,
        formatter_class = argparse.RawTextHelpFormatter)
    panzer_parser.add_argument("---panzer-support",
        help    = 'location of directory of support files for panzer')
    panzer_parser.add_argument("---debug",
        help    = 'write debug info to `panzer.log`',
        action  = "store_true")
    panzer_parser.add_argument("---silent",
        help    = 'suppress panzer-generated messages to console',
        action  = "store_true")
    panzer_parser.add_argument("---html",
        help    = 'format console messages in HTML',
        action  = "store_true")
    panzer_parser.add_argument('---version',
        action  = 'version',
        version = ('%(prog)s ' + __version__))
    known, panzer_unknown = panzer_parser.parse_known_args()
    panzer_known = vars(known)

    ## Update OPTIONS with panzer-specific values passed from cli
    for key in panzer_known:
        value = panzer_known[key]
        if value is not None:
            OPTIONS['panzer'][key] = value

    ## Parse options specific to pandoc
    pandoc_parser = argparse.ArgumentParser(prog = 'pandoc')
    pandoc_parser.add_argument("--write", "-w", "--to", "-t",
        help = 'writer')
    pandoc_parser.add_argument("--output", "-o",
        help = 'output')
    known, pandoc_unknown = pandoc_parser.parse_known_args(panzer_unknown)
    pandoc_known = vars(known)

    ## Update OPTIONS with pandoc's output, with '-' as default output
    OPTIONS['pandoc']['output'] = \
        pandoc_known['output'] if pandoc_known['output'] else '-'

    ## Update OPTIONS with pandoc's writer
    if pandoc_known['write']:
        ## First case: writer explicitly specified by cli option
        OPTIONS['pandoc']['write'] = pandoc_known['write']
    elif OPTIONS['pandoc']['output'] == '-':
        ## Second case: html default writer for stdout
        OPTIONS['pandoc']['write'] = 'html'
    else:
        ## Third case: writer set via output filename extension
        ext = os.path.splitext(OPTIONS['pandoc']['output'])[1].lower()
        implicit_writer = PANDOC_WRITER_MAPPING.get(ext)
        if implicit_writer is not None:
            OPTIONS['pandoc']['write'] = implicit_writer
        else:
            ## html is default writer for unrecognised extensions
            OPTIONS['pandoc']['write'] = 'html'

    ## If one of the inputs is stdin then read from stdin now into
    ## a temp file, then replace '-'s in input with reference to file
    if '-' in pandoc_unknown:
        ## Read from stdin now into temp file in cwd
        stdin     = sys.stdin.read()
        temp_file = tempfile.NamedTemporaryFile(prefix='__stdin-panzer-',
                        suffix = '__',
                        dir    = os.getcwd(),
                        delete = False)
        temp_filename = os.path.join(os.getcwd(), temp_file.name)
        OPTIONS['panzer']['stdin_temp_file'] = temp_filename
        temp_file.write(stdin)
        temp_file.close()
        ## Replace all reference to stdin in pandoc cli with temp file
        for index, value in enumerate(pandoc_unknown):
            if value == '-':
                pandoc_unknown[index] = OPTIONS['panzer']['stdin_temp_file']

    ## Find all input files by using `pandoc --dump-args`
    command = ["pandoc", "--dump-args"] + pandoc_unknown
    stdout = subprocess.check_output(command).splitlines()
    ## first line is output file, ignore it
    OPTIONS['pandoc']['input'] = stdout[1:]
    ## remove input files from pandoc_unknown
    pandoc_unknown = [ opt for opt in pandoc_unknown if                 \
                               opt not in OPTIONS['pandoc']['input'] ]

    ## Store all remaining options for pandoc in OPTIONS
    ## This is full list of options passed to panzer minus:
    ##      1. Panzer-specific options
    ##      2. -w option
    ##      3. -o option
    ##      4. all input files
    ## These all need to be replaced when pandoc runs internally in panzer
    OPTIONS['pandoc']['options'] = pandoc_unknown

    TIMING_DATA.append(('parse cli', time.clock() - start_time))


def plot(labels_and_data):
    """
    Histogram data to stdout
    """
    # pylint: disable=W0142
    labels, data = zip(*labels_and_data)
    # pylint: disable=W0141
    longest = max(map(len, labels))
    largest = max(data)
    scale = 50.0 / largest
    for i, datum in enumerate(data):
        bar_rep = "#" * int(datum * scale)
        logger.debug("%s: %s (%fs)", labels[i].ljust(longest), bar_rep, datum)


## -----------------------------------------------------------
## Main function
## -----------------------------------------------------------


def main():
    """This is the main.
    Here is the documentation.
    """
    start_time = time.clock()
    commands   = []
    
    try:
        check_pandoc_exists()
        parse_cli_options()
        start_logger()
        logger.info('---- Panzer started -----')
        logger.debug('------------------ OPTIONS --------------------------')
        logger.debug('\n' + json.dumps(OPTIONS, indent=1))

        check_support_directory()
        input_docs = OPTIONS['pandoc']['input'] + OPTIONS['pandoc']['options']
        default_document = load_defaults()
        current_document = load(input_docs)
        if current_document.style:
            logger.info('Style: "%s"', current_document.style)
        else:
            logger.warning('Key "style" not found')
        current_document.transform(default_document,
                                   current_document.style,
                                   OPTIONS['pandoc']['write'])
        logger.debug('----------------- METADATA -------------------------')
        logger.debug('\n' + json.dumps(current_document.metadata,        \
                                       sort_keys=True, indent=1))

        commands = build_commands(current_document.metadata)
        logger.debug('----------------- COMMANDS -------------------------')
        logger.debug('\n' + json.dumps(commands,                         \
                                       sort_keys=True, indent=1))

        if 'preflight' in commands:
            run_scripts(commands, 'preflight')

        if 'filter' in commands:
            current_document.run_filters(commands)

    except PanzerSetupError as error:
        # Errors that occur before logging starts
        print(error)
        sys.exit(1)
    except (KeyError,
            PanzerKeyError,
            PanzerBadASTError,
            PanzerTypeError) as error:
        logger.critical(error)
        sys.exit(1)
    except subprocess.CalledProcessError:
        logger.critical('Panzer cannot continue because of pandoc fatal error')
        sys.exit(1)

    finally:
        
        if 'postflight' in commands:
            run_scripts(commands, 'postflight')
            
        if OPTIONS['panzer']['stdin_temp_file']:
            # if a temp file was created, remove it
            os.remove(OPTIONS['panzer']['stdin_temp_file'])
            logger.debug('Deleted temp file: %s',
                         OPTIONS['panzer']['stdin_temp_file'])
        
        total_time = time.clock() - start_time
        TIMING_DATA.append(('total', total_time))
        logger.debug('----------------- TIMING -------------------------')
        plot(TIMING_DATA)
        
        logger.info('------ Panzer quit ------')
    
    ## successful exit
    sys.exit(0)


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
