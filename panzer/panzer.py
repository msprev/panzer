#!/usr/bin/env python3
""" panzer: pandoc with styles

for more info: <https://github.com/msprev/panzer>

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
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
from .version import VERSION
__version__ = VERSION

REQUIRE_PANDOC_ATLEAST = "1.12.1"
DEFAULT_SUPPORT_DIR = os.path.join(os.path.expanduser('~'), '.panzer')
ENCODING = 'utf8'
T = 't'
C = 'c'
ADDITIVE_FIELDS = ['preflight',
                   'filter',
                   'postprocess',
                   'postflight',
                   'cleanup']

# Document class

class Document(object):
    """ representation of pandoc/panzer documents
    - ast      : pandoc abstract syntax tree of document
    - style    : list of styles for document
    - styledef : style definitions
    - template : template for document
    - output   : string filled with output when processing complete
    """
    def __init__(self):
        """ new blank document """
        empty = [{'unMeta': {}}, []]
        # - defaults
        self.ast = empty
        self.style = []
        self.styledef = {}
        self.template = None
        self.output = None

    def populate(self, ast, global_styledef):
        """ populate document with data """
        # - template : set after 'transform' applied
        # - output   : set after 'pandoc' applied
        # - ast
        if ast:
            self.ast = ast
        else:
            log('DEBUG', 'panzer', 'source documents empty')
        # - get the source document's metadata
        metadata = self.get_metadata()
        log('DEBUG', 'panzer', debug_lined('ORIGINAL METADATA'))
        log('DEBUG', 'panzer', debug_json_dump(metadata))
        # - styledef
        self.populate_styledef(global_styledef)
        # - style
        self.populate_style()

    def populate_styledef(self, global_styledef):
        # - global style definitions
        log('INFO', 'panzer', '-- style definition --')
        if global_styledef:
            msg = debug_pretty_keys(global_styledef)
            log('INFO', 'panzer', 'global definitions:')
            for line in msg:
                log('INFO', 'panzer', '    ' + line)
            self.styledef = global_styledef
        else:
            log('INFO', 'panzer', 'no global definitions loaded')
        # - add local style definitions
        local_styledef = {}
        try:
            local_styledef = get_content(self.get_metadata(), 'styledef', 'MetaMap')
            self.styledef.update(local_styledef)
            msg = debug_pretty_keys(local_styledef)
            log('INFO', 'panzer', 'local definitions:')
            for line in msg:
                log('INFO', 'panzer', '    ' + line)
            overridden = [ key for key in local_styledef
                           if key in global_styledef ]
            for key in overridden:
                log('INFO', 'panzer',
                    'local definition "%s" overrides global' 
                    % key)
        except PanzerKeyError as info:
            log('DEBUG', 'panzer', info)
        except PanzerTypeError as error:
            log('ERROR', 'panzer', error)

    def populate_style(self):
        log('INFO', 'panzer', '-- document style --')
        try:
            self.style = get_list_or_inline(self.get_metadata(), 'style')
        except PanzerKeyError:
            log('INFO', 'panzer', 'no "style" field found, will just run pandoc')
        except PanzerTypeError as error:
            log('ERROR', 'panzer', error)
        if self.style:
            log('INFO', 'panzer', 'style')
            log('INFO', 'panzer', '    %s' % ", ".join(self.style))
        self.expand_style()
        log('INFO', 'panzer', 'full hierarchy')
        log('INFO', 'panzer', '    %s' % ", ".join(self.style))
        # - check: remove styles lacking definitions
        missing = [ key for key in self.style
                    if key not in self.styledef ]
        for key in missing:
            log('ERROR', 'panzer', 'style definition for "%s" not found'
                '---ignoring style' % key)
        self.style = [ key for key in self.style
                       if key not in missing ]

    def expand_style(self):
        """ expand style field to include all parent styles """
        pass

    def purge_styles(self):
        """ remove metadata fields specific to panzer """
        kill_list = ADDITIVE_FIELDS
        kill_list += 'style'
        kill_list += 'styledef'
        kill_list += 'template'
        metadata = self.get_metadata()
        new_metadata = { key: metadata[key]
                         for key in metadata
                         if key not in kill_list }
        self.set_metadata(new_metadata)

    def get_metadata(self):
        """ return metadata branch """
        return get_metadata(self.ast)

    def set_metadata(self, new_metadata):
        """ set metadata branch to new_metadata """
        try:
            self.ast[0]['unMeta'] = new_metadata
        except (IndexError, KeyError):
            self.ast = [{'unMeta': new_metadata}, []]

    def transform(self, options):
        """ transform using style """
        writer = options['pandoc']['write']
        log('INFO', 'panzer', 'writer "%s"' % writer)
        # - quit if no style
        if not self.style:
            return
        # 1. Do transform
        # - start with blank metadata
        # - add styles one by one
        # - then add metadata specified in document
        new_metadata = {}
        for style in self.style:
            new_metadata = update_metadata(new_metadata, 
                                           get_nested_content(self.styledef, [style, 'default'], 'MetaMap'))
            new_metadata = update_metadata(new_metadata, 
                                           get_nested_content(self.styledef, [style, writer], 'MetaMap'))
        # - finally, add raw metadata settings of new_metadata
        new_metadata.update(self.get_metadata())
        # 2. Apply kill rules to trim lists
        for field in ADDITIVE_FIELDS:
            try:
                original_list = get_content(new_metadata, field, 'MetaList')
                trimmed_list = apply_kill_rules(original_list)
                if trimmed_list:
                    set_content(new_metadata, field, trimmed_list, 'MetaList')
                else:
                    # if all items killed, delete field
                    del new_metadata[field]
            except PanzerKeyError:
                continue
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
        # 4. Update document
        # - ast
        self.set_metadata(new_metadata)
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
            self.template = resolve_path(template_str, 'template', options)
        except (PanzerKeyError, PanzerTypeError) as error:
            log('DEBUG', 'panzer', error)
        if self.template:
            log('INFO', 'panzer', 'template "%s"' % self.template)

    def inject_panzer_reserved_field(self, json_message):
        """ add panzer_reserved field to document """
        # - check if already exists
        metadata = self.get_metadata()
        try:
            get_content(metadata, 'panzer_reserved')
            log('ERROR',
                'panzer',
                'special field "panzer_reserved" already in metadata'
                '---overwriting it')
        except PanzerKeyError:
            pass
        # - add it
        field_content = [{"t": "CodeBlock",
                          "c": [["", [], []], json_message]}]
        set_content(metadata, 'panzer_reserved', field_content, 'MetaBlocks')
        # - update document
        self.set_metadata(metadata)

    def pipe_through(self, kind, run_lists):
        """ pipe through external command """
        # - if no run list of this kind to run, then return
        if kind not in run_lists or not run_lists[kind]:
            return
        log('INFO', 'panzer', '-- %s --' % kind)
        # 1. Set up incoming pipe
        if kind == 'filter':
            in_pipe = json.dumps(self.ast)
        elif kind == 'postprocess':
            in_pipe = self.output
        else:
            raise PanzerInternalError('illegal invocation of '
                                      '"pipe" in panzer.py')
        # 2. Set up outgoing pipe in case of failure
        out_pipe = in_pipe
        # 3. Run commands
        for command in run_lists[kind]:
            # - add debugging info
            command_name = os.path.basename(command[0])
            command_path = ' '.join(command).replace(os.path.expanduser('~'),
                                                     '~')
            log('INFO', 'panzer', 'run "%s"' % command_path)
            # - run the command and log any errors
            stderr = ''
            try:
                p = subprocess.Popen(command,
                                     stderr=subprocess.PIPE,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
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

    def pandoc(self, options):
        """ run pandoc on document

        Normally, input to pandoc is passed via stdin and output received via
        stout. Exception is when the output file has .pdf extension. Then,
        output is simply pdf file that panzer does not process further, and
        internal document not updated by pandoc.
        """
        # 1. Build pandoc command
        command = ['pandoc']
        command += ['-']
        command += ['--read', 'json']
        command += ['--write', options['pandoc']['write']]
        if options['pandoc']['pdf_output']:
            command += ['--output', options['pandoc']['output']]
        else:
            command += ['--output', '-']
        # - template specified on cli has precedence
        if options['pandoc']['template']:
            command += ['--template=%s' % options['pandoc']['template']]
        elif self.template:
            command += ['--template=%s' % self.template]
        # - remaining options
        command += options['pandoc']['options']
        # 2. Prefill input and output pipes
        in_pipe = json.dumps(self.ast)
        out_pipe = ''
        stderr = ''
        # 3. Run pandoc command
        log('INFO', 'panzer', '-- pandoc --')
        log('INFO', 'panzer', 'run "%s"' % ' '.join(command))
        try:
            p = subprocess.Popen(command,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
            in_pipe_bytes = in_pipe.encode(ENCODING)
            out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
            out_pipe = out_pipe_bytes.decode(ENCODING)
            stderr = stderr_bytes.decode(ENCODING)
        except OSError as error:
            log('ERROR', 'pandoc', error)
        finally:
            log_stderr(stderr)
        # 4. Deal with output of pandoc
        if options['pandoc']['pdf_output']:
            # do nothing with a pdf
            pass
        else:
            self.output = out_pipe

    def write(self, options):
        """ write document """
        # case 1: pdf as output file
        if options['pandoc']['pdf_output']:
            return
        # case 2: stdout as output
        if options['pandoc']['output'] == '-':
            sys.stdout.buffer.write(self.output.encode(ENCODING))
            sys.stdout.flush()
        # case 3: any other file as output
        else:
            with open(options['pandoc']['output'], 'w',
                      encoding=ENCODING) as output_file:
                output_file.write(self.output)
                output_file.flush()
            log('INFO',
                'panzer',
                'output written to "%s"' % options['pandoc']['output'])

# Functions for manipulating metadata

def update_metadata(old, new):
    """ return old updated with new metadata """
    # 1. Update with values in 'metadata' field
    try:
        old.update(get_content(new, 'metadata', 'MetaMap'))
        del new['metadata']
    except (PanzerKeyError, KeyError):
        pass
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
    # 2. Update with values in fields for additive lists
    for field in ADDITIVE_FIELDS:
        try:
            try:
                new_list = get_content(new, field, 'MetaList')
            except PanzerKeyError:
                # field not in incoming metadata, move to next list
                continue
            try:
                old_list = get_content(old, field, 'MetaList')
            except PanzerKeyError:
                # field not in old metadata, start with an empty list
                old_list = []
        except PanzerTypeError as error:
            # wrong type of value under field, skip to next list
            log('WARNING', 'panzer', error)
            continue
        old_list.extend(new_list)
        set_content(old, field, old_list, 'MetaList')
        del new[field]
    # 3. Update with values of all remaining fields
    # - includes 'template' field
    old.update(new)
    return old

def apply_kill_rules(old_list):
    """ return old_list after applying kill rules """
    new_list = []
    for item in old_list:
        # 1. Sanity checks
        check_c_and_t_exist(item)
        item_content = item[C]
        item_type = item[T]
        if item_type != 'MetaMap':
            log('ERROR',
                'panzer',
                'fields "' + '", "'.join(ADDITIVE_FIELDS) + '" '
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
            if get_type(item_content, 'run') != 'MetaInlines':
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
            new_list = [new_item for new_item in new_list if
                        get_content(new_item[C], 'run', 'MetaInlines') !=
                        to_be_killed]
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

def get_nested_content(metadata, fields, expected_type_of_leaf=None):
    """ return content of field by traversing a list of MetaMaps

    args:
        metadata : dictionary to traverse
        fields       : list of fields to traverse in dictionary from
        shallowest to deepest. Content of every field, except the last,
        must be type 'MetaMap' (otherwise fields could not be traversed).
        The content of final field in the list is returned.
        expected_type_of_leaf : (optional) expected type of final field's
        content

    Returns:
        content of final field in list, or the empty dict ({}) if field of
        expected type is not found
    """
    current_field = fields.pop(0)
    try:
        # If on a branch...
        if fields:
            next_content = get_content(metadata, current_field, 'MetaMap')
            return get_nested_content(next_content,
                                      fields,
                                      expected_type_of_leaf)
        # Else on a leaf...
        else:
            return get_content(metadata, current_field, expected_type_of_leaf)
    except PanzerKeyError:
        # current_field not found, return {}: nothing to update
        return {}
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
        # wrong type found, return {}: nothing to update
        return {}

def get_content(metadata, field, expected_type=None):
    """ return content of field """
    if field not in metadata:
        raise PanzerKeyError('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    if expected_type:
        found_type = metadata[field][T]
        if found_type != expected_type:
            raise PanzerTypeError('value of "%s": expecting type "%s", '
                                  'but found type "%s"'
                                  % (field, expected_type, found_type))
    return metadata[field][C]

def get_type(metadata, field):
    """ return type of field """
    if field not in metadata:
        raise PanzerKeyError('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    return metadata[field][T]

def set_content(metadata, field, content, content_type):
    """ set content and type of field in metadata """
    metadata[field] = {C: content, T: content_type}

def get_list_or_inline(metadata, field):
    """ return content of MetaList or MetaInlines item as a list """
    field_type = get_type(metadata, field)
    if field_type == 'MetaInlines':
        content_raw = get_content(metadata, field, 'MetaInlines')
        content = [ pandocfilters.stringify(content_raw) ]
        return content
    elif field_type == 'MetaList':
        content = []
        for content_raw in get_content(metadata, field, 'MetaList'):
            content.append(pandocfilters.stringify(content_raw))
        return content
    else:
        raise PanzerTypeError('"%s" value must be of type "MetaInlines" or "MetaList"'
                              % field)

def get_metadata(ast):
    """ returns metadata branch of ast or {} if not present """
    try:
        metadata = ast[0]['unMeta']
    except KeyError:
        metadata = {}
    return metadata

def check_c_and_t_exist(item):
    """ check item contains both C and T fields """
    if C not in item:
        message = 'Value of "%s" corrupt: "C" field missing' % repr(item)
        raise PanzerBadASTError(message)
    if T not in item:
        message = 'Value of "%s" corrupt: "T" field missing' % repr(item)
        raise PanzerBadASTError(message)

def make_json_message(document, run_lists, options):
    """ return json message to pass to executables """
    data = [{'metadata' : document.get_metadata(),
             'styledef' : document.styledef,
             'template' : document.template,
             'style' : document.style,
             'run_lists' : run_lists,
             'cli_options' : options}]
    json_message = json.dumps(data)
    return json_message


# Load documents

def load(options):
    """ return ast from running pandoc on input documents """
    # 1. Build pandoc command
    command = options['pandoc']['input'].copy()
    if options['pandoc']['read']:
        command += ['--read', options['pandoc']['read']]
    command += ['--write', 'json', '--output', '-']
    command += options['pandoc']['options']
    log('DEBUG', 'panzer', 'run pandoc "%s"' % ' '.join(command))
    command = ['pandoc'] + command
    out_pipe = ''
    stderr = ''
    ast = None
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
        raise PanzerBadASTError('failed to receive valid '
                                'json object from pandoc')
    return ast

def load_yaml_styledef(options):
    """ return metadata branch of styles.yaml as dict """
    filename = os.path.join(options['panzer']['support'], 'styles.yaml')
    if not os.path.exists(filename):
        log('ERROR', 'panzer', 'default styles file not found: %s' % filename)
        return Document()
    # - slurp styles.yaml
    data = []
    with open(filename, 'r', encoding=ENCODING) as styles_file:
        data = styles_file.readlines()
    # - top and tail with metadata markings
    data.insert(0, "---\n")
    data.append("...\n")
    data_string = ''.join(data)
    log('DEBUG', 'panzer', debug_lined('STYLES METADATA'))
    log('DEBUG', 'panzer', data_string)
    # - build pandoc command
    command = ['pandoc']
    command += ['-']
    command += ['--write', 'json']
    command += ['--output', '-']
    log('DEBUG', 'panzer', 'run pandoc "%s"' % ' '.join(command))
    # - send to pandoc to convert to json
    in_pipe = data_string
    out_pipe = ''
    stderr = ''
    try:
        p = subprocess.Popen(command,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
        in_pipe_bytes = in_pipe.encode(ENCODING)
        out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
        out_pipe = out_pipe_bytes.decode(ENCODING)
        stderr = stderr_bytes.decode(ENCODING)
    except OSError as error:
        log('ERROR', 'pandoc', error)
    finally:
        log_stderr(stderr)
    # - convert json to python dict
    ast = None
    try:
        ast = json.loads(out_pipe)
    except ValueError:
        raise PanzerBadASTError('failed to receive valid '
                                'json object from pandoc')
    # - return metadata branch of dict
    if not ast:
        return {}
    else:
        return get_metadata(ast)

# Filters and pre/post-flight scripts

def run_scripts(kind, run_lists, json_message, force_run=False):
    """ execute commands of kind listed in run_lists """
    # - if no run list to run, then return
    if kind not in run_lists or not run_lists[kind]:
        return
    log('INFO', 'panzer', '-- %s --' % kind)
    for command in run_lists[kind]:
        filename = os.path.basename(command[0])
        fullpath = ' '.join(command).replace(os.path.expanduser('~'), '~')
        log('INFO', 'panzer', 'run "%s"' % fullpath)
        stderr = out_pipe = str()
        try:
            p = subprocess.Popen(command,
                                 stdin=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            # send panzer's json message to scripts via stdin
            in_pipe = json_message
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

def build_run_lists(metadata, run_lists, options):
    """ return run lists updated with metadata """
    for field in ADDITIVE_FIELDS:
        run_list = run_lists[field]
        # - if 'filter', add filter list specified on command line
        if field == 'filter' and options['pandoc']['filter']:
            run_list = [list(f) for f in options['pandoc']['filter']]
        #  - add commands specified in metadata
        if field in metadata:
            run_list.extend(build_run_list(metadata, field, options))
        # pdf output: skip postprocess
        if options['pandoc']['pdf_output'] \
           and field == 'postprocess' \
           and run_list:
            log('INFO', 'panzer', 'postprocess skipped --- since output is PDF')
            run_lists[field] = []
            continue
        # - filter be passed writer as 1st argument
        if field == 'filter':
            for command in run_list:
                command.insert(1, options['pandoc']['write'])
        run_lists[field] = run_list
        for (i, command) in enumerate(run_list):
            log('INFO',
                'panzer',
                '%s %d "%s"' % (field, i+1, " ".join(command)))
    return run_lists

def build_run_list(metadata, field, options):
    """ return run list for field of metadata """
    run_list = []
    try:
        metadata_list = get_content(metadata, field, 'MetaList')
    except (PanzerTypeError, PanzerKeyError) as error:
        log('WARNING', 'panzer', error)
        return run_list
    for item in metadata_list:
        check_c_and_t_exist(item)
        item_content = item[C]
        # command name
        command_raw = get_content(item_content, 'run', 'MetaInlines')
        command_str = pandocfilters.stringify(command_raw)
        command = [resolve_path(command_str, field, options)]
        # arguments
        arguments = []
        if 'args' in item_content:
            if get_type(item_content, 'args') == 'MetaInlines':
                # arguments are raw string
                arguments_raw = get_content(item_content, 'args', 'MetaInlines')
                arguments_str = pandocfilters.stringify(arguments_raw)
                arguments = shlex.split(arguments_str)
            elif get_type(item_content, 'args') == 'MetaList':
                # arguments specified as MetaList
                arguments_list = get_content(item_content, 'args', 'MetaList')
                arguments = parse_args_metalist(arguments_list)
            command.extend(arguments)
        run_list.append(command)
    return run_list

def parse_args_metalist(arguments_list):
    """ return list of arguments from metadata list """
    arguments = []
    for item in arguments_list:
        if item[T] != 'MetaMap':
            log('ERROR',
                'panzer',
                '"args" list should have fields of type "MetaMap"')
            continue
        fields = item[C]
        if len(fields) != 1:
            log('ERROR',
                'panzer',
                '"args" list should have exactly one field per item')
            continue
        field_name = "".join(fields.keys())
        field_type = get_type(fields, field_name)
        field_value = get_content(fields, field_name, field_type)
        if field_type == 'MetaBool':
            arguments.append('--' + field_name)
        elif field_type == 'MetaInlines':
            value_str = pandocfilters.stringify(field_value)
            arguments.append('--%s="%s"' % (field_name, value_str))
        else:
            log('ERROR',
                'panzer',
                'arguments of type "%s" not' 'supported---"%s" ignored'
                % (field_type, field_name))
    return arguments

def resolve_path(filename, field, options):
    """ return path to filename of kind field """
    basename = os.path.splitext(filename)[0]
    paths = []
    paths.append(filename)
    paths.append(os.path.join('panzer',
                              field,
                              filename))
    paths.append(os.path.join('panzer',
                              field,
                              basename,
                              filename))
    paths.append(os.path.join(options['panzer']['support'],
                              field,
                              filename))
    paths.append(os.path.join(options['panzer']['support'],
                              field,
                              basename,
                              filename))
    for path in paths:
        if os.path.exists(path):
            return path
    return filename


# Support functions for non-core operations

def start_logger(options):
    """ start the logger """
    config = {
        'version'                  : 1,
        'disable_existing_loggers' : False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(message)s'
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
                'handlers'   : ['console', 'log_file_handler'],
                'level'      : 'DEBUG',
                'propagate'  : True
            }
        }
    }
    # - check debug flag
    if not options['panzer']['debug']:
        config['loggers'][__name__]['handlers'].remove('log_file_handler')
        del config['handlers']['log_file_handler']
    # - set verbosity level
    verbosity = ['CRITICAL', 'WARNING', 'INFO']
    index = options['panzer'].get('verbose', 1)
    try:
        verbosity_level = verbosity[index]
    except IndexError:
        print('error: unknown setting for verbosity level', file=sys.stderr)
        verbosity_level = 'INFO'
    config['handlers']['console']['level'] = verbosity_level
    # - send configuration to logger
    logging.config.dictConfig(config)
    log('DEBUG', 'panzer', '>>>>> panzer starts <<<<<')
    log('DEBUG', 'panzer', debug_lined('OPTIONS'))
    log('DEBUG', 'panzer', debug_json_dump(options))

def log(level_str, sender, message):
    """ send a log message """
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
        'CRITICAL' : 'FATAL:   ',
        'ERROR'    : 'ERROR:   ',
        'WARNING'  : 'WARNING: ',
        'INFO'     : '         ',
        'DEBUG'    : '         ',
        'NOTSET'   : '         '
    }
    message = str(message)
    sender_str = ''
    message_str = ''
    level = levels.get(level_str, levels['ERROR'])
    # -- level
    pretty_level_str = pretty_levels.get(level_str, pretty_levels['ERROR'])
    # -- sender - right justify name if less than 8 chars long
    if sender != 'panzer':
        sender_str = sender + ': '
    # -- message
    message_str = message
    output = ''
    output += pretty_level_str
    output += sender_str
    output += message_str
    my_logger.log(level, output)

def log_stderr(stderr, sender=str()):
    """ send a log from external executable """
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
        incoming = {}
        try:
            incoming = json.loads(line)
        except ValueError:
            # - if json cannot be decoded, just log as ERROR prefixed by '!'
            log('DEBUG',
                'panzer',
                'failed to decode json message from %s: "%s"' % (sender, line))
            incoming = [{'error_msg': {'level': 'ERROR',
                                       'message': '!' + line}}]
        for item in incoming:
            level = item['error_msg']['level']
            message = item['error_msg']['message']
            log(level, sender, message)

def debug_pretty_keys(dictionary):
    """ return pretty printed list of dictionary keys """
    # - number of keys printed per line
    N = 5
    # - turn into sorted list
    keys = list(dictionary.keys())
    keys.sort()
    # - fill with blank elements to width N
    missing = N - (len(keys) % N)
    keys.extend([''] * missing)
    # - turn into 2D matrix
    matrix = [ [ keys[i+j] for i in range(0, N) ] 
               for j in range(0, len(keys), N) ] 
    # - calculate max width for each column
    len_matrix = [ [ len(col) for col in row ] for row in matrix ]
    max_len_col = [ max([ row[j] for row in len_matrix ]) 
                    for j in range(0, N) ]
    # - pad with spaces 
    matrix = [ [ row[j].ljust(max_len_col[j]) for j in range(0, N) ] 
               for row in matrix ]
    # - return list of lines to print
    matrix = [ "    ".join(row) for row in matrix ]
    return matrix

def debug_json_dump(json_data):
    """ return pretty printed json_data """
    return json.dumps(json_data, sort_keys=True, indent=1)

def debug_lined(title):
    """ return pretty printed title """
    output = '-' * 20 + title + '-' * 20
    return output

def check_pandoc_exists():
    """ check pandoc exists """
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
    """ return tuple of version_string """
    return tuple(map(int, (version_string.split("."))))

def check_support_directory(options):
    """ check support directory exists """
    if options['panzer']['support'] != DEFAULT_SUPPORT_DIR:
        if not os.path.exists(options['panzer']['support']):
            log('ERROR',
                'panzer',
                'panzer support directory "%s" not found'
                % options['panzer']['support'])
            log('WARNING',
                'panzer',
                'using default panzer support directory: %s'
                % DEFAULT_SUPPORT_DIR)
            options['panzer']['support'] = DEFAULT_SUPPORT_DIR

    if not os.path.exists(DEFAULT_SUPPORT_DIR):
        log('WARNING',
            'panzer',
            'default panzer support directory "%s" not found'
            % DEFAULT_SUPPORT_DIR)
    os.environ['PANZER_SHARED'] = os.path.join(options['panzer']['support'],
                                               'shared')

def default_options():
    """ return default options """
    options = {
        'panzer': {
            'support'         : DEFAULT_SUPPORT_DIR,
            'debug'           : False,
            'verbose'         : 1,
            'stdin_temp_file' : ''
        },
        'pandoc': {
            'input'      : [],
            'output'     : '-',
            'pdf_output' : False,
            'read'       : '',
            'write'      : '',
            'template'   : '',
            'filter'     : [],
            'options'    : []
        }
    }
    return options

def default_run_lists():
    """ return default run lists """
    run_lists = {
        'preflight'   : [],
        'filter'      : [],
        'postprocess' : [],
        'postflight'  : [],
        'cleanup'     : []
    }
    return run_lists

def parse_cli_options(options):
    """ parse command line options """
    panzer_description = '''
    Panzer-specific arguments are prefixed by triple dashes ('---').
    All other arguments are passed to pandoc.

    Default support directory: "%s"
    ''' % DEFAULT_SUPPORT_DIR
    panzer_epilog = '''
    Copyright (C) 2014 Mark Sprevak
    Web:  http://sites.google.com/site/msprevak
    This is free software; see the source for copying conditions. There is no
    warranty, not even for merchantability or fitness for a particular purpose.
    '''
    # Adapted from https://github.com/jgm/pandoc/blob/master/pandoc.hs#L841
    pandoc_writer_mapping = {
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
    panzer_parser = argparse.ArgumentParser(description=panzer_description,
                                            epilog=panzer_epilog,
                                            formatter_class=argparse.RawTextHelpFormatter)
    panzer_parser.add_argument("---panzer-support",
                               help='location of directory of support files')
    panzer_parser.add_argument("---debug",
                               action="store_true",
                               help='write debug info to panzer.log')
    panzer_parser.add_argument("---verbose",
                               type=int,
                               help='verbosity of console messages\n'
                               ' 0: silent\n'
                               ' 1: only errors and warnings\n'
                               ' 2: full info (default)')
    panzer_parser.add_argument('---version',
                               action='version',
                               version=('%(prog)s ' + __version__))
    panzer_known_raw, unknown = panzer_parser.parse_known_args()
    panzer_known = vars(panzer_known_raw)
    # 2. Update options with panzer-specific values
    for field in panzer_known:
        value = panzer_known[field]
        if value:
            options['panzer'][field] = value
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
    # 2. Update options with pandoc-specific values
    for field in pandoc_known:
        value = pandoc_known[field]
        if value:
            options['pandoc'][field] = value
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
        implicit_writer = pandoc_writer_mapping.get(ext)
        if implicit_writer is not None:
            options['pandoc']['write'] = implicit_writer
        else:
            # - html is default writer for unrecognised extensions
            options['pandoc']['write'] = 'html'
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
            options['panzer']['stdin_temp_file'] = temp_filename
            temp_file.write(stdin_bytes)
            temp_file.flush()
        # Replace all reference to stdin in pandoc cli with temp file
        for index, value in enumerate(unknown):
            if value == '-':
                unknown[index] = options['panzer']['stdin_temp_file']
    # 6. Other input files
    # - detect input files by using `pandoc --dump-args`
    command = ['pandoc', '--dump-args'] + unknown
    stdout_bytes = subprocess.check_output(command)
    stdout = stdout_bytes.decode(ENCODING)
    stdout_list = stdout.splitlines()
    # - first line is output file, ignore it
    options['pandoc']['input'] = stdout_list[1:]
    # - remove input files from unknown
    unknown = [arg for arg in unknown
               if arg not in options['pandoc']['input']]
    # 7. Remaining options for pandoc
    options['pandoc']['options'] = unknown
    return options

# Exception classes

class PanzerError(Exception):
    """ base class for all panzer exceptions """
    pass

class PanzerSetupError(PanzerError):
    """ error in the setup phase """
    pass

class PanzerBadASTError(PanzerError):
    """ malformatted AST encountered (e.g. C or T fields missing) """
    pass

class PanzerKeyError(PanzerError):
    """ looked for metadata field, did not find it """
    pass

class PanzerTypeError(PanzerError):
    """ looked for value of a type, encountered different type """
    pass

class PanzerInternalError(PanzerError):
    """ function invoked with invalid parameters """
    pass


# Main function

def main():
    """ the main function """
    options = default_options()
    run_lists = default_run_lists()
    json_message = make_json_message(Document(), run_lists, options)
    try:
        check_pandoc_exists()
        options = parse_cli_options(options)
        start_logger(options)
        check_support_directory(options)
        ast = load(options)
        global_styledef = load_yaml_styledef(options)
        doc = Document()
        doc.populate(ast, global_styledef)
        doc.transform(options)
        run_lists = build_run_lists(doc.get_metadata(), run_lists, options)
        doc.purge_styles()
        json_message = make_json_message(doc, run_lists, options)
        doc.inject_panzer_reserved_field(json_message)
        run_scripts('preflight', run_lists, json_message)
        doc.pipe_through('filter', run_lists)
        doc.pandoc(options)
        doc.pipe_through('postprocess', run_lists)
        doc.write(options)
        run_scripts('postflight', run_lists, json_message)
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
        run_scripts('cleanup', run_lists, json_message, force_run=True)
        # - if temp file created in setup, remove it
        if options['panzer']['stdin_temp_file']:
            os.remove(options['panzer']['stdin_temp_file'])
            log('DEBUG',
                'panzer',
                'deleted temp file: %s'
                % options['panzer']['stdin_temp_file'])
        log('DEBUG', 'panzer', '>>>>> panzer quits <<<<<')
    # - successful exit
    sys.exit(0)

if __name__ == '__main__':
    main()
