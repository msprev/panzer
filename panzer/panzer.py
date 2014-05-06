#!/usr/bin/env python3
"""Panzer: Adds styles to pandoc

Styles provide an easy interface to combinations of templates, metadata,
filters, postprocessors, pre- and post-flight scripts for pandoc
documents. Styles can be invoked and customised on a per document basis.
Panzer allows you to manage default styles via a configuration file in
the support directory (default: "~./panzer/")

Panzer-specific command line options (prefixed by triple dashes '---')
are removed by panzer and all remaining command line options are passed
transparently to pandoc.

Author:     Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright:  Copyright 2014, Mark Sprevak
License:    BSD3
"""

import argparse
import json
import logging
import logging.config
import os
import pandocfilters
import shlex
import subprocess
import sys
import tempfile

__version__ = "0.9"

REQUIRE_PANDOC_ATLEAST = "1.12.1"
DEFAULT_SUPPORT_DIR = os.path.join(os.path.expanduser('~'), '.panzer')
ENCODING = 'utf8'
T = 't'
C = 'c'
ADDITIVE_KEYS = ['preflight', 'filter', 'postprocess', 'postflight', 'cleanup']
OPTIONS = {
    'panzer': {
        'support'         : DEFAULT_SUPPORT_DIR,
        'debug'           : False,
        'verbose'         : 2,
        'html'            : False,
        'stdin_temp_file' : ''
    },
    'pandoc': {
        'input'      : '',
        'output'     : '-',
        'pdf_output' : False,
        'read'       : '',
        'write'      : '',
        'template'   : '',
        'filter'     : [],
        'options'    : []
    }
}

# Document class

class Document(object):
    """

    panzer's representation of pandoc documents

    Attributes:
        - ast      : list giving input abstract syntax tree (taken from
        pandoc's json representation)
        - metadata : dict giving metadata branch of ast
        - style    : string style for document
        - template : string template for document
        - output   : string filled by pandoc's writer once run on ast

    Important methods:
        - transform    : transform document's metadata using panzer styles
        - pipe    : filter a document based on an external command
        - pandoc   : invoke pandoc, populating self.output
        - write : write self.output based on cli options

    """
    def __init__(self, ast=None):
        """

        Create a new document.

        Args:
            - ast : (optional) input ast (as taken from pandoc's json
            representation)

        """
        # 1. Defaults for new documents
        self.ast      = []
        self.metadata = {}
        self.style    = None
        self.template = None
        self.output   = None
        if not ast:
            return
        # 2. Apply passed values to set up document
        # - ast
        self.ast = ast
        # - metadata
        try:
            self.metadata = self.ast[0]['unMeta']
        except KeyError:
            log('WARNING', 'panzer', 'no metadata found in source documents')
        # - style
        try:
            style_raw = get_content(self.metadata, 'style', 'MetaInlines')
            self.style = pandocfilters.stringify(style_raw)
        except PanzerKeyError:
            log('DEBUG', 'panzer', 'no style key found')
        except PanzerTypeError as error:
            log('WARNING', 'panzer', error)
        # - template : set after transform has been applied
        # - output   : set after pandoc has been applied

    def transform(self, defaults):
        """

        Transforms document using panzer's styles.

        Modify metadata of document based on a style and writer.

        Args:
            - defaults : dict of metadata defaults

        """
        style = self.style
        if style:
            log('DEBUG', 'panzer', 'style "%s"' % style)
        else:
            log('DEBUG', 'panzer', 'no "style" key found')
        if style \
          and style not in self.metadata \
          and style not in defaults.metadata:
            log('ERROR',
                'panzer',
                'style definition for "%s" not found.' % style)
        # 1. Do transform
        # - start with blank metadata
        # - add global defaults one by one
        # - then add defaults specified in document
        writer = OPTIONS['pandoc']['write']
        work_list = [
            ( defaults.metadata , ['All' , 'all']  , 'MetaMap' ) ,
            ( defaults.metadata , ['All' , writer] , 'MetaMap' ) ,
            ( defaults.metadata , [style , 'all']  , 'MetaMap' ) ,
            ( defaults.metadata , [style , writer] , 'MetaMap' ) ,
            ( self.metadata     , ['All' , 'all']  , 'MetaMap' ) ,
            ( self.metadata     , ['All' , writer] , 'MetaMap' ) ,
            ( self.metadata     , [style , 'all']  , 'MetaMap' ) ,
            ( self.metadata     , [style , writer] , 'MetaMap' ) ]
        new_metadata = {}
        for item in work_list:
            update_metadata(new_metadata, get_nested_content(*item))
        # - finally, add metadata settings of document
        new_metadata.update(self.metadata)
        # 2. Apply kill rules to trim lists
        for key in ADDITIVE_KEYS:
            try:
                original_list = get_content(new_metadata, key, 'MetaList')
                trimmed_list = apply_kill_rules(original_list)
                if trimmed_list:
                    set_content(new_metadata, key, trimmed_list, 'MetaList')
                else:
                    # if all items killed, delete key
                    del new_metadata[key]
            except PanzerKeyError:
                continue
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
        # 3. Tidy up after transform
        # - remove now unneeded style keys from document's metadata
        if 'All' in new_metadata:
            del new_metadata['All']
        if style in new_metadata:
            del new_metadata[style]
        # 4. Add special panzer_reserved field to pass OPTIONS
        # - check if already exists
        try:
            get_content(new_metadata, 'panzer_reserved')
            log('ERROR',
                'panzer',
                'special key "panzer_reserved" already in metadata'
                '---overwriting it')
        except PanzerKeyError:
            pass
        # - add it
        data_out = [ { 'cli_options': OPTIONS } ]
        json_content = json.dumps(data_out)
        field_content = [{"t":"CodeBlock", "c":[["",[],[]],json_content]}]
        set_content(new_metadata, 'panzer_reserved',
                    field_content, 'MetaBlocks')
        # 4. Update document
        # - ast
        try:
            self.ast[0]['unMeta'] = new_metadata
        except (IndexError, KeyError):
            self.ast = [{'unMeta': new_metadata}, []]
        # - metadata
        self.metadata = new_metadata
        # - template
        try:
            template_raw = get_content(new_metadata, 'template', 'MetaInlines')
            template_str = pandocfilters.stringify(template_raw)
            self.template = resolve_path(template_str, 'template')
        except (PanzerKeyError, PanzerTypeError) as error:
            log('DEBUG', 'panzer', error)
        log('DEBUG', 'panzer', 'template: %s' % self.template)
        log('DEBUG', 'panzer', '-'*20+'NEW METADATA'+'-'*20+'\n'+
            json.dumps(self.metadata, sort_keys=True, indent=1))

    def pipe(self, kind, commands):
        """ Pass document through an external command.

        This method is used to run filters and postprocessors on
        document.

        Args:
            commands : list of commands to run. Commands are run from
                    first to last. Standard output of one is fed into
                    the standard input of next. Commands must be given
                    in format of subprocess.Popen.
            kind     : string type of command. Values can be:
                'filter'      --- command is json filter
                'postprocess' --- command is postprocessor

        Raises:
            PanzerInternalError : if called with unknown kind setting
        """
        # - if no commands of this kind to run, then return
        if kind not in commands:
            return
        # 1. Set up incoming pipe
        if kind == 'filter':
            in_pipe = json.dumps(self.ast)
        elif kind == 'postprocess':
            # pdf output: skip postprocess
            if OPTIONS['pandoc']['pdf_output']:
                log('INFO', kind, 'skipping since output is PDF')
                return
            in_pipe = self.output
        else:
            raise PanzerInternalError('illegal invocation of'
                                      '"pipe" in panzer.py')
        # 2. Set up outgoing pipe in case of failure
        out_pipe = in_pipe
        # 3. Run commands
        for command in commands[kind]:
            # - pandoc requires filters be passed writer as 1st argument
            if kind == 'filter':
                command.insert(1, OPTIONS['pandoc']['write'])
            # - add debugging info
            command_name = os.path.basename(command[0])
            command_path = ' '.join(command).replace(os.path.expanduser('~'),
                                                     '~')
            log('DEBUG', kind, command_name, submessage=command_path)
            # - run the command and log any errors
            stderr = ''
            try:
                p = subprocess.Popen(command,
                                    stderr = subprocess.PIPE,
                                    stdin  = subprocess.PIPE,
                                    stdout = subprocess.PIPE)
                in_pipe_bytes = in_pipe.encode(ENCODING)
                out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
                out_pipe = out_pipe_bytes.decode(ENCODING)
                stderr = stderr_bytes.decode(ENCODING)
            except OSError as error:
                log('ERROR', command_name, error)
                continue
            else:
                in_pipe = out_pipe
            finally:
                log_stderr(stderr, command_name)
        # 4. Update document's data with output from commands
        if kind == 'filter':
            try:
                self.ast = json.loads(out_pipe)
            except ValueError:
                log('ERROR',
                    'panzer',
                    'failed to receive json object from filters'
                    '---ignoring all filters')
                return
        elif kind == 'postprocess':
            self.output = out_pipe

    def pandoc(self):
        """ Run pandoc on the document.

        This method uses the options set in OPTIONS['pandoc'] as the cli
        settings for the pandoc command.

        Normally, input to pandoc is passed via stdin in json format and
        output is received via stout in the writer format. The exception
        is when the output file has a .pdf extension. Here, the output
        is simply a pdf file that panzer does not process further, and
        the internal document is not updated by pandoc.
        """
        # 1. Build pandoc command
        command =  [ 'pandoc' ]
        command += [ '-' ]
        command += [ '--read', 'json' ]
        command += [ '--write', OPTIONS['pandoc']['write'] ]
        if OPTIONS['pandoc']['pdf_output']:
            command += [ '--output', OPTIONS['pandoc']['output'] ]
        else:
            command += [ '--output', '-' ]
        # - template specified on cli has precedence
        if OPTIONS['pandoc']['template']:
            command += [ '--template=%s' % OPTIONS['pandoc']['template'] ]
        elif self.template:
            command += [ '--template=%s' % self.template ]
        # - remaining options
        command += OPTIONS['pandoc']['options']
        # 2. Prefill input and output pipes
        in_pipe  = json.dumps(self.ast)
        out_pipe = ''
        stderr   = ''
        # 3. Run pandoc command
        log('DEBUG', 'pandoc', ' '.join(command))
        try:
            p = subprocess.Popen(command,
                                 stderr = subprocess.PIPE,
                                 stdin  = subprocess.PIPE,
                                 stdout = subprocess.PIPE)
            in_pipe_bytes = in_pipe.encode(ENCODING)
            out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
            out_pipe = out_pipe_bytes.decode(ENCODING)
            stderr = stderr_bytes.decode(ENCODING)
        except OSError as error:
            log('ERROR', 'pandoc', error)
        finally:
            log_stderr(stderr)
        # 4. Deal with output of pandoc
        if OPTIONS['pandoc']['pdf_output']:
            # do nothing with a pdf
            pass
        else:
            self.output = out_pipe

    def write(self):
        """ Writes the document in the requested format.

        The format is specified by OPTIONS['pandoc'].
        """
        # case 1: pdf as output file
        if OPTIONS['pandoc']['pdf_output']:
            pass
        # case 2: stdout as output
        if OPTIONS['pandoc']['output'] == '-':
            sys.stdout.buffer.write(self.output.encode(ENCODING))
            sys.stdout.flush()
        # case 3: any other file as output
        else:
            with open(OPTIONS['pandoc']['output'], 'wt',
                    encoding=ENCODING) as output_file:
                output_file.write(self.output)
                output_file.flush()
            log('INFO',
                'panzer',
                'output written to "%s"' % OPTIONS['pandoc']['output'])

# Functions for manipulating metadata

def update_metadata(dictionary, new_data):
    """ This updates dictionary with new metadata. The update is done
    respecting panzer's rules on additive lists, killing, etc.

    Args:
        dictionary : dictionary metadata to be updated
        new_data   : dictionary new metadata to be used for update

    Returns:
        dictionary updated with new_data
    """
    # 1. Update with values in 'default' key
    try:
        dictionary.update(get_content(new_data, 'default', 'MetaMap'))
        del new_data['default']
    except (PanzerKeyError, KeyError):
        pass
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
    # 2. Update with values in keys for additive lists
    for key in ADDITIVE_KEYS:
        try:
            try:
                new_list = get_content(new_data, key, 'MetaList')
            except PanzerKeyError:
                # key not in incoming metadata, move to next list
                continue
            try:
                old_list = get_content(dictionary, key, 'MetaList')
            except PanzerKeyError:
                # key not in old metadata, start with an empty list
                old_list = []
        except PanzerTypeError as error:
            # wrong type of value under key, skip to next list
            log('WARNING', 'panzer', error)
            continue
        old_list.extend(new_list)
        set_content(dictionary, key, old_list, 'MetaList')
        del new_data[key]
    # 3. Update with values of all remaining keys
    # - includes 'template' key
    dictionary.update(new_data)
    return dictionary

def apply_kill_rules(old_list):
    """ Apply panzer's rules on killing to additive lists. 'kill' and
    'killall' fields remove previous items in the list (either
    selectively or indiscriminately).

    Args:
        old_list : list to be processed according to kill rules

    Returns:
        list after kill rules applied
    """
    new_list = []
    for item in old_list:
        # 1. Sanity checks
        check_C_and_T_exist(item)
        item_content = item[C]
        item_tag     = item[T]
        if item_tag != 'MetaMap':
            log('ERROR',
                'panzer',
                'keys "' + '", "'.join(ADDITIVE_KEYS) + '" '
                'value must be of type "MetaMap"---ignoring 1 item')
            continue
        if len(item_content.keys() & {'run', 'kill', 'killall'}) != 1:
            log('ERROR',
                'panzer',
                'must contain exactly one "run", "kill", or "killall" per item'
                '---ignoring 1 item')
            continue
        # 2. Now operate on content
        if 'run' in item_content:
            if get_tag(item_content, 'run') != 'MetaInlines':
                log('ERROR',
                    'panzer',
                    '"run" value must be of type "MetaInlines"'
                    '---ignoring 1 item')
                continue
            new_list.append(item)
        elif 'kill' in item_content:
            try:
                to_be_killed = get_content(item_content, 'kill', 'MetaInlines')
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
            new_list = [ new_item for new_item in new_list if
                         get_content(new_item[C], 'run', 'MetaInlines') !=
                         to_be_killed ]
        elif 'killall' in item_content:
            try:
                if get_content(item_content, 'killall', 'MetaBool') == True:
                    new_list = []
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
        else:
            # Should never occur, caught by previous syntax check
            continue
    return new_list

def get_nested_content(dictionary, keys, expected_type_of_leaf=None):
    """ Returns content of key by traversing a list of MetaMaps.

    Args:
        dictionary : dictionary to traverse
        keys       : list of keys to traverse in dictionary from
        shallowest to deepest. Content of every key, except the last,
        must be type 'MetaMap' (otherwise keys could not be traversed).
        The content of final key in the list is returned.
        expected_type_of_leaf : (optional) expected type of final key's
        content

    Returns:
        content of final key in list, or the empty dict ({}) if key of
        expected type is not found
    """
    current_key = keys.pop(0)
    try:
        # If on a branch...
        if keys:
            next_content = get_content(dictionary, current_key, 'MetaMap')
            return get_nested_content(next_content, keys, expected_type_of_leaf)
        # Else on a leaf...
        else:
            return get_content(dictionary, current_key, expected_type_of_leaf)
    except PanzerKeyError:
        # current_key not found, return {}: nothing to update
        return {}
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
        # wrong type found, return {}: nothing to update
        return {}

def get_content(dictionary, key, expected_type=None):
    """ Returns content of key from metadata dictionary.

    Args:
        dictionary : dictionary source
        key        : key to retrieve
        expected_type : (optional) expected type of content

    Returns:
        content of key

    Raises:
        PanzerKeyError if key not found
        PanzerTypeError if content not of expected type
    """
    if key not in dictionary:
        raise PanzerKeyError('key "%s" not found' % key)

    check_C_and_T_exist(dictionary[key])

    if expected_type:
        found_type = dictionary[key][T]
        if found_type != expected_type:
            raise PanzerTypeError('value of "%s": expecting type "%s", '
                                  'but found type "%s"'
                                  % (key, expected_type, found_type))
    return dictionary[key][C]

def get_tag(dictionary, key):
    """ Returns type of key from metadata dictionary.

    Args:
        dictionary : dictionary source
        key        : key to retrieve

    Returns:
        type of key

    Raises:
        PanzerKeyError if key not found
    """
    if key not in dictionary:
        raise PanzerKeyError('key "%s" not found' % key)

    check_C_and_T_exist(dictionary[key])

    return dictionary[key][T]

def set_content(dictionary, key, content, tag):
    """Sets the content and type of key in a dictionary

    Args:
        dictionary : dict where key is to be set
        key        : key of dict
        content    : content of key
        tag        : tag (pandoc type) of key
    """
    dictionary[key] = {C: content, T: tag}

def check_C_and_T_exist(item):
    """Syntax check dict contains both C and T keys.

    Args:
        item : dict to be checked

    Raises:
        PanzerBadASTError : Either C or T keys missing
    """
    if C not in item:
        message = 'Value of "%s" corrupt: "C" key missing' % repr(item)
        raise PanzerBadASTError(message)
    if T not in item:
        message = 'Value of "%s" corrupt: "T" key missing' % repr(item)
        raise PanzerBadASTError(message)


# Load documents

def load():
    """ Load input files and return a Document

    panzer uses pandoc to load its input by asking it to output a json object
    representing the concatenated files.

    Args:
        input_files : list of filenames to load
        options : (optional) command line options passed to pandoc during loading

    Returns:
        Document containing parsed input_files concatenated

    Raises:
        PanzerBadASTError : if pandoc cannot pass a valid json object back
    """
    # 1. Build pandoc command
    command = OPTIONS['pandoc']['input']
    if OPTIONS['pandoc']['read']:
        command += [ '--read', OPTIONS['pandoc']['read'] ]
    command += ['--write', 'json', '--output', '-']
    command += OPTIONS['pandoc']['options']
    log('DEBUG', 'pandoc', ' '.join(command))
    ast = pandoc_read_json(command)
    current_doc = Document(ast)
    log('DEBUG', 'panzer', '-'*20+'ORIGINAL METADATA'+'-'*20+'\n'+
        json.dumps(current_doc.metadata, sort_keys=True, indent=1))
    return current_doc

def load_defaults():
    """ Load panzer defaults file from support directory.

    Returns:
        Document containing parsed defaults file
    """
    filename = os.path.join(OPTIONS['panzer']['support'], 'defaults.yaml')
    if os.path.exists(filename):
        command = [ filename ]
        command += ['--write', 'json', '--output', '-']
        ast = pandoc_read_json(command)
        default_doc = Document(ast)
        log('DEBUG', 'panzer', '-'*20+'DEFAULTS METADATA'+'-'*20+'\n'+
            json.dumps(default_doc.metadata, sort_keys=True, indent=1))
        return default_doc
    else:
        log('ERROR', 'panzer', 'defaults file not found: %s' % filename)
        return Document()

def pandoc_read_json(command):
    command = ['pandoc'] + command
    stderr = []
    try:
        p = subprocess.Popen(command,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        out_pipe_bytes, stderr_bytes = p.communicate()
        out_pipe = out_pipe_bytes.decode(ENCODING)
        stderr = stderr_bytes.decode(ENCODING)
    except OSError as error:
        log('ERROR', 'pandoc', error)
    finally:
        log_stderr(stderr)
    try:
        ast = json.loads(out_pipe)
    except ValueError:
        raise PanzerBadASTError('failed to receive valid'
                                'json object from pandoc')
    return ast


# Filters and pre/post-flight scripts

def run_scripts(kind, commands, force_run=False):
    """docstring for run_preflight"""
    # - if no commands to run, then return
    if kind not in commands:
        return
    for command in commands[kind]:
        filename = os.path.basename(command[0])
        fullpath = ' '.join(command).replace(os.path.expanduser('~'), '~')
        log('DEBUG', kind, filename, submessage=fullpath)
        stderr = out_pipe = str()
        try:
            p = subprocess.Popen(command,
                                 stdin=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            # send panzer's OPTIONS to scripts via stdin as a json
            message_out = [ { 'cli_options': OPTIONS } ]
            in_pipe = json.dumps(message_out)
            in_pipe_bytes = in_pipe.encode(ENCODING)
            out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
            if out_pipe_bytes:
                out_pipe = out_pipe_bytes.decode(ENCODING)
            if stderr_bytes:
                stderr = stderr_bytes.decode(ENCODING)
        except OSError as error:
            log('ERROR', filename, error)
            continue
        except Exception as error:
            # if force_run: always run next script
            if force_run:
                log('ERROR', filename, error)
                continue
            else:
                raise
        finally:
            log_stderr(stderr, filename)

def build_commands(dictionary):
    """docstring for buildCommands"""
    commands = dict()
    for key in ADDITIVE_KEYS:
        command_list = list()
        # add filter list specified on command line
        if key == 'filter' and OPTIONS['pandoc']['filter']:
            command_list = [list(f) for f in OPTIONS['pandoc']['filter']]
        # add commands specified in metadata
        if key in dictionary:
            command_list.extend(build_command(dictionary, key))
        if command_list:
            commands[key] = command_list
    log('DEBUG', 'panzer', '-'*20+'COMMANDS'+'-'*20+'\n'+
        json.dumps(commands, sort_keys=True, indent=1))
    return commands

def build_command(dictionary, key):
    """docstring for buildCommand"""
    command_list  = list()
    try:
        metadata_list = get_content(dictionary, key, 'MetaList')
    except (PanzerTypeError, PanzerKeyError) as error:
        log('WARNING', 'panzer', error)
        return command_list
    for item in metadata_list:
        check_C_and_T_exist(item)
        item_content = item[C]
        # command name
        command_raw = get_content(item_content, 'run', 'MetaInlines')
        command_str = pandocfilters.stringify(command_raw)
        command = [ resolve_path(command_str, key) ]
        # options
        options = []
        if 'opt' in item_content:
            if get_tag(item_content, 'opt') == 'MetaInlines':
                # options are raw string
                options_raw = get_content(item_content, 'opt', 'MetaInlines')
                options_str = pandocfilters.stringify(options_raw)
                options = shlex.split(options_str)
            elif get_tag(item_content, 'opt') == 'MetaMap':
                # options specified as MetaMap
                options_dict = get_content(item_content, 'opt', 'MetaMap')
                options = parse_command_options(options_dict)
            command.extend(options)
        command_list.append(command)
    return command_list

def parse_command_options(options_dict):
    """docstring for parseOptions"""
    options = []
    for key in options_dict:
        value_tag = get_tag(options_dict, key)
        if value_tag == 'MetaBool' \
          and get_content(options_dict, key, 'MetaBool') == True:
            options.append('--' + key)
        elif value_tag == 'MetaInlines':
            value_raw = get_content(options_dict, key, 'MetaInlines')
            value_str = pandocfilters.stringify(value_raw)
            options.append('--%s="%s"' % (key, value_str))
        else:
            log('ERROR',
                'panzer',
                'option values of type "%s" not' 'supported---"%s" ignored'
                % (value_tag, key))
    return options

def resolve_path(filename, key):
    """docstring for find_shell_filename

    when looking for file 'foo.py' of kind 'key', look in the following places:
        1) ./foo.py
        2) ./key/foo.py
        3) ./key/foo/foo.py
        4) OPTIONS['panzer']['support']/key/foo.py
        5) OPTIONS['panzer']['support']/key/foo/foo.py
    If 'filename' not found, assume it is otherwise reachable in system's path
        i.e. return 'filename' as is, and hope for best
    """
    basename = os.path.splitext(filename)[0]
    paths = []
    paths.append(filename)
    paths.append(os.path.join(key, filename))
    paths.append(os.path.join(key, basename, filename))
    paths.append(os.path.join(OPTIONS['panzer']['support'],
                              key, filename))
    paths.append(os.path.join(OPTIONS['panzer']['support'],
                              key, basename, filename))
    for path in paths:
        if os.path.exists(path):
            return path
    return filename


# Support functions for non-core operations

def start_logger():
    """ Set up the logger for panzer and its subprocesses.
    """
    config = {
        'version'                  : 1,
        'disable_existing_loggers' : False,
        'formatters': {
            'detailed': {
                'format': '%(relativeCreated)d - %(message)s'
            },
            'mimimal': {
                'format': '%(message)s'
            }
        },
        'handlers': {
            'log_file_handler': {
                'class'        : 'logging.handlers.RotatingFileHandler',
                'level'        : 'DEBUG',
                'formatter'    : 'detailed',
                'filename'     : 'panzer.log',
                'maxBytes'     : 10485760,
                'backupCount'  : 5,
                'encoding'     : ENCODING
            },
            'console': {
                'class'      : 'logging.StreamHandler',
                'level'      : 'INFO',
                'formatter'  : 'mimimal',
                'stream'     : 'ext://sys.stderr'
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
    # - check debug flag
    if not OPTIONS['panzer']['debug']:
        config['loggers'][__name__]['handlers'].remove('log_file_handler')
        del config['handlers']['log_file_handler']
    # - set verbosity level
    verbosity = [ 'CRITICAL', 'WARNING', 'INFO' ]
    index = OPTIONS['panzer'].get('verbose', 2)
    try:
        verbosity_level = verbosity[index]
    except IndexError:
        print('error: unknown setting for verbosity level', file=sys.stderr)
        verbosity_level = 'INFO'
    config['handlers']['console']['level'] = verbosity_level
    # - send configuration to logger
    logging.config.dictConfig(config)
    log('DEBUG', 'panzer', '>>>>> panzer starts <<<<<')
    log('DEBUG', 'panzer', '-'*20+'OPTIONS'+'-'*20+'\n'+
        json.dumps(OPTIONS, indent=1))

def log(level_str, sender, message, submessage=str()):
    """ Send a log message with appropriate formatting. All log messages
    in panzer and its subprocesses are sent via this function. Do not
    call the logging module functions directly.

    Args:
        level_str       : string giving error level (see table below)
        sender          : string giving name of process sending message
        message         : string or list of characters
        submessage      : (optional) additional information to be displayed in
                          more minor role
    """
    my_logger = logging.getLogger(__name__)
    # - lookup table for internal strings to logging levels
    levels = {
        'CRITICAL' : logging.CRITICAL,
        'ERROR'    : logging.ERROR,
        'WARNING'  : logging.WARNING,
        'INFO'     : logging.INFO,
        'DEBUG'    : logging.DEBUG,
        'NOTSET'   : logging.NOTSET
    }
    # - lookup table for internal strings to pretty output strings
    pretty_levels = {
        'CRITICAL' : 'fatal:   ',
        'ERROR'    : 'error:   ',
        'WARNING'  : 'warning: ',
        'INFO'     : '         ',
        'DEBUG'    : '         ',
        'NOTSET'   : '         '
    }
    message        = str(message)
    sender_str     = ''
    message_str    = ''
    submessage_str = ''
    level = levels.get(level_str, levels['ERROR'])
    # - HTML output
    if OPTIONS['panzer']['html']:
        sender_str     = '<span class="sender">%s</span>' % sender
        message_str    = '<span class="message">%s</span>' % message
        submessage_str = '<span class="submessage">%s</span>' % submessage
        output =  '<div class="%s">' % level_str
        output += sender_str + message_str + submessage_str
        output += '</div>'
        my_logger.log(level, output)
        return
    # - normal output
    # -- level
    pretty_level_str = pretty_levels.get(level_str, pretty_levels['ERROR'])
    # -- sender - right justify name if less than 8 chars long
    if len(sender) < 8:
        sender_str = sender[:8].rjust(8)
    else:
        sender_str = sender
    # -- message
    message_str = message
    # -- submessage
    if submessage:
        submessage_str = ' (%s)' % submessage
    output = ''
    output += pretty_level_str
    output += sender_str + ': '
    output += message_str
    output += submessage_str
    my_logger.log(level, output)

def log_stderr(stderr, sender=str()):
    """

    Handle messages from subprocesses sent via stderr and pass them on
    to the log function.

    Messages from subprocesses are sent in a json format that specifies
    the error level and message text.

    New lines in stderr indicate a new message.

    Args:
        - stderr : string returned from the stderr of subprocess
        - sender : name of process sending message

    """
    # 1. check for blank input
    if not stderr:
        # - nothing to do
        return
    # 2. get a string with sender's name
    if sender:
        # - remove file extension from sender's name if present
        sender = os.path.splitext(sender)[0]
    # 3. now handle the messages sent by sender
    # - split the input (based on newlines) into list of json strings
    for line in stderr.split('\n'):
        if not line:
            # - skip blank lines: no valid json or message to decode
            continue
        incoming = dict()
        try:
            incoming = json.loads(line)
        except ValueError:
            # - if json cannot be decoded, just log as ERROR prefixed by '!'
            log('DEBUG',
                'panzer',
                'failed to decode json message from %s: "%s"' % (sender, line))
            incoming = [ {'error_msg':
                            {
                              'level': 'ERROR',
                              'message': '!' + line
                            }
                         } ]
        for item in incoming:
            level = item['error_msg']['level']
            message = item['error_msg']['message']
            log(level, sender, message)

def check_pandoc_exists():
    """docstring for check_pandoc_exists"""
    try:
        stdout_bytes = subprocess.check_output(["pandoc", "--version"])
        stdout = stdout_bytes.decode(ENCODING)
    except OSError as error:
        if error.errno == os.errno.ENOENT:
            raise PanzerSetupError('pandoc not found')
        else:
            raise PanzerSetupError(error)
    stdout_list = stdout.splitlines()
    pandoc_version = stdout_list[0].split(' ')[1]
    if versiontuple(pandoc_version) < versiontuple(REQUIRE_PANDOC_ATLEAST):
        raise PanzerSetupError('pandoc %s or greater required'
                               '---found pandoc version %s'
                               % (REQUIRE_PANDOC_ATLEAST, pandoc_version))

def versiontuple(version_string):
    return tuple(map(int, (version_string.split("."))))

def check_support_directory():
    """docstring for create_default_data_directory"""

    if OPTIONS['panzer']['support'] != DEFAULT_SUPPORT_DIR:
        if not os.path.exists(support):
            log('ERROR',
                'panzer',
                'panzer support directory "%s" not found'
                % OPTIONS['panzer']['support'])
            log('WARNING',
                'panzer',
                'using default panzer support directory: %s'
                % DEFAULT_SUPPORT_DIR)
            OPTIONS['panzer']['support'] = DEFAULT_SUPPORT_DIR

    if not os.path.exists(DEFAULT_SUPPORT_DIR):
        log('WARNING',
            'panzer',
            'default panzer support directory "%s" not found'
            % DEFAULT_SUPPORT_DIR)
        if query_yes_no('would you like me to download and install an '
                        'example panzer support directory? (y/n)'):
            log('INFO', 'panzer',
                'installing example support directory in "%s"'
                % DEFAULT_SUPPORT_DIR)
        #    return_code = subprocess.call(["git", "clone",
        #                                   REMOTE_URL,
        #                                   DEFAULT_SUPPORT_DIR])
        #    if return_code == 0:
        #        log('INFO', 'panzer',
        #            'successfully cloned using git to: %s'
        #            % DEFAULT_SUPPORT_DIR)
        #    else:
        #        log('ERROR', 'panzer',
        #            'failed to clone using git to: %s'
        #            % DEFAULT_SUPPORT_DIR)
        #        return
    os.environ['PANZER_SHARED'] = os.path.join(OPTIONS['panzer']['support'],
                                               'shared')

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,   "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        stdout = question + prompt
        sys.stdout.buffer.write(stdout.encode(ENCODING))
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.buffer.write("Please respond with 'yes' or 'no'"
                                    "(or 'y' or 'n').\n".encode(ENCODING))

def parse_cli_options():
    """Parse the command line options passed to panzer, and print help text

    Sets the global variable `OPTIONS`.

    `OPTIONS` is a dict that holds all the options that apply to this
    invocation of panzer.
    """
    panzer_description = '''
    Panzer: A way to add styles to pandoc

    Styles are handy ways to use templates, metadata, filters,
    postprocessors, pre- and post-flight scripts in pandoc documents.
    Styles can be invoked and customised on a per document basis. Panzer
    allows you to manage your defaults via a configuration file in the
    support directory (default: "~./panzer/")

    Panzer-specific command line options (prefixed by triple dashes '---')
    are removed by panzer and remaining command line options are passed
    transparently to the underlying instances of pandoc.
    '''
    panzer_epilog = '''
    Copyright (C) 2014 Mark Sprevak
    Web:  http://sites.google.com/site/msprevak
    This is free software; see the source for copying conditions. There is no
    warranty, not even for merchantability or fitness for a particular purpose.
    '''
    # Adapted from https://github.com/jgm/pandoc/blob/master/pandoc.hs#L841
    pandoc_writer_mapping   = {
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
    # 1. Parse options specific to panzer
    panzer_parser = argparse.ArgumentParser(
                                description=panzer_description,
                                epilog=panzer_epilog,
                                formatter_class=argparse.RawTextHelpFormatter)
    panzer_parser.add_argument("---panzer-support",
                               help='location of directory of support files')
    panzer_parser.add_argument("---debug",
                               action="store_true",
                               help='write debug info to panzer.log')
    panzer_parser.add_argument("---verbose",
                               type=int,
                               help='detail of console messages\n'
                                    ' 0: silent\n'
                                    ' 1: only errors and warnings\n'
                                    ' 2: full info (default)')
    panzer_parser.add_argument("---html",
                               action="store_true",
                               help='format console messages in HTML')
    panzer_parser.add_argument('---version',
                               action='version',
                               version=('%(prog)s ' + __version__))
    panzer_known_raw, unknown = panzer_parser.parse_known_args()
    panzer_known = vars(panzer_known_raw)

    # 2. Update OPTIONS with panzer-specific values
    for key in panzer_known:
        value = panzer_known[key]
        if value:
            OPTIONS['panzer'][key] = value

    # 3. Parse options specific to pandoc
    pandoc_parser = argparse.ArgumentParser(prog='pandoc')
    pandoc_parser.add_argument("--read",
                               "-r",
                               "--from",
                               "-f",
                               help='reader')
    pandoc_parser.add_argument("--write",
                               "-w",
                               "--to",
                               "-t",
                               help='writer')
    pandoc_parser.add_argument("--output",
                               "-o",
                               help='output')
    pandoc_parser.add_argument("--template",
                               help='template')
    pandoc_parser.add_argument("--filter",
                               "-F",
                               nargs=1,
                               action='append',
                               help='filter')
    pandoc_known_raw, unknown = pandoc_parser.parse_known_args(unknown)
    pandoc_known = vars(pandoc_known_raw)

    # 2. Update OPTIONS with pandoc-specific values
    for key in pandoc_known:
        value = pandoc_known[key]
        if value:
            OPTIONS['pandoc'][key] = value

    # 3. Check for pandoc output being pdf
    if os.path.splitext(OPTIONS['pandoc']['output'])[1].lower() == '.pdf':
        OPTIONS['pandoc']['pdf_output'] = True

    # 4. Detect pandoc's writer
    # - first case: writer explicitly specified by cli option
    if OPTIONS['pandoc']['write']:
        pass
    # - second case: html default writer for stdout
    elif OPTIONS['pandoc']['output'] == '-':
        OPTIONS['pandoc']['write'] = 'html'
    # - third case: writer set via output filename extension
    else:
        ext = os.path.splitext(OPTIONS['pandoc']['output'])[1].lower()
        implicit_writer = pandoc_writer_mapping.get(ext)
        if implicit_writer is not None:
            OPTIONS['pandoc']['write'] = implicit_writer
        else:
            # - html is default writer for unrecognised extensions
            OPTIONS['pandoc']['write'] = 'html'

    # 5. Input from stdin
    # - if one of the inputs is stdin then read from stdin now into
    # - temp file, then replace '-'s in input filelist with reference to file
    if '-' in unknown:
        # Read from stdin now into temp file in cwd
        stdin_bytes = sys.stdin.buffer.read()
        with tempfile.NamedTemporaryFile(prefix='__panzer-',
                                         suffix='__',
                                         dir=os.getcwd(),
                                         delete=False) as temp_file:
            temp_filename = os.path.join(os.getcwd(), temp_file.name)
            OPTIONS['panzer']['stdin_temp_file'] = temp_filename
            temp_file.write(stdin_bytes)
            temp_file.flush()
        # Replace all reference to stdin in pandoc cli with temp file
        for index, value in enumerate(unknown):
            if value == '-':
                unknown[index] = OPTIONS['panzer']['stdin_temp_file']

    # 6. Other input files
    # - detect input files by using `pandoc --dump-args`
    command = ['pandoc', '--dump-args'] + unknown
    stdout_bytes = subprocess.check_output(command)
    stdout = stdout_bytes.decode(ENCODING)
    stdout_list = stdout.splitlines()
    # - first line is output file, ignore it
    OPTIONS['pandoc']['input'] = stdout_list[1:]
    # - remove input files from unknown
    unknown = [ arg for arg in unknown
                        if arg not in OPTIONS['pandoc']['input'] ]
    # 7. Remaining options for pandoc
    OPTIONS['pandoc']['options'] = unknown

# Exception classes

class PanzerError(Exception):
    """Base class for all panzer exceptions"""
    pass

class PanzerSetupError(PanzerError):
    """Error in the setup phase"""
    pass

class PanzerBadASTError(PanzerError):
    """Malformatted AST encountered (e.g. C or T keys missing)"""
    pass

class PanzerKeyError(PanzerError):
    """Looked for key, did not find it"""
    pass

class PanzerTypeError(PanzerError):
    """Looked for value of a type, encountered different type"""
    pass

class PanzerInternalError(PanzerError):
    """Panzer function invoked with invalid parameters"""
    pass


# Main function

def main():
    """The main function"""
    commands = dict()

    try:
        check_pandoc_exists()
        parse_cli_options()
        start_logger()
        check_support_directory()
        default_doc = load_defaults()
        current_doc = load()
        current_doc.transform(default_doc)
        commands = build_commands(current_doc.metadata)
        run_scripts('preflight', commands)
        current_doc.pipe('filter', commands)
        current_doc.pandoc()
        current_doc.pipe('postprocess', commands)
        current_doc.write()
        run_scripts('postflight', commands)

    except PanzerSetupError as error:
        # - errors that occur before logging starts
        print(error, file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        log('CRITICAL',
            'panzer',
            'cannot continue because of fatal error')
        sys.exit(1)
    except (KeyError,
            PanzerKeyError,
            PanzerBadASTError,
            PanzerTypeError,
            PanzerInternalError) as error:
        # - panzer exceptions not caught elsewhere, should have been
        log('CRITICAL', 'panzer', error)
        sys.exit(1)
    finally:
        run_scripts('cleanup', commands, force_run=True)
        # - if temp file created in setup, remove it
        if OPTIONS['panzer']['stdin_temp_file']:
            os.remove(OPTIONS['panzer']['stdin_temp_file'])
            log('DEBUG',
                'panzer',
                'deleted temp file: %s'
                % OPTIONS['panzer']['stdin_temp_file'])
        log('DEBUG', 'panzer', '>>>>> panzer quits <<<<<')
    # 11. Successful exit
    sys.exit(0)

# Standard boilerplate to call the main() function to begin the program.
if __name__ == '__main__':
    main()
