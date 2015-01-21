""" panzer document class and its methods """
import json
import os
import pandocfilters
import subprocess
import sys
from . import error
from . import meta
from . import util
from . import info
from . import const

class Document(object):
    """ representation of pandoc/panzer documents
    - ast       : pandoc abstract syntax tree of document
    - style     : list of styles for document
    - stylefull : full list of styles including all parents
    - styledef  : style definitions
    - runlist   : run list for document
    - options   : cli options for document
    - template  : template for document
    - output    : string filled with output when processing complete
    """
    #
    # disable pylint warnings:
    #     + Too many instance attributes
    # pylint: disable=R0902
    #
    def __init__(self):
        """ new blank document """
        # - defaults
        self.ast = const.EMPTY_DOCUMENT
        self.style = list()
        self.stylefull = list()
        self.styledef = dict()
        self.runlist = list()
        self.options = {
            'panzer': {
                'panzer_support'  : const.DEFAULT_SUPPORT_DIR,
                'debug'           : str(),
                'silent'          : False,
                'stdin_temp_file' : str()
            },
            'pandoc': {
                'input'      : list(),
                'output'     : '-',
                'pdf_output' : False,
                'read'       : str(),
                'write'      : str(),
                'template'   : str(),
                'filter'     : list(),
                'options'    : list()
            }
        }
        self.template = None
        self.output = None

    def populate(self, ast, global_styledef):
        """ populate document with data """
        # - self.template : set after 'transform' applied
        # - self.output   : set after 'pandoc' applied
        # - set self.ast:
        if ast:
            self.ast = ast
        else:
            info.log('DEBUG', 'panzer', 'source document(s) empty')
        # - check if panzer_reserved key already exists in metadata
        metadata = self.get_metadata()
        try:
            meta.get_content(metadata, 'panzer_reserved')
            info.log('ERROR', 'panzer',
                     'special field "panzer_reserved" already in metadata'
                     '---will be overwritten')
        except error.MissingField:
            pass
        # - set self.styledef
        self.populate_styledef(global_styledef)
        # - set self.style and self.stylefull
        self.populate_style()
        # - remove any styledef not used in doc
        self.styledef = {key: self.styledef[key]
                         for key in self.styledef
                         if key in self.stylefull}

    def populate_styledef(self, global_styledef):
        """ populate self.styledef applying global_styledef defaults """
        info.log('INFO', 'panzer', info.pretty_title('style definitions'))
        # - add global style definitions
        if global_styledef:
            info.log('INFO', 'panzer', 'global:')
            for line in info.pretty_keys(global_styledef):
                info.log('INFO', 'panzer', '  ' + line)
            self.styledef = dict(global_styledef)
        else:
            info.log('INFO', 'panzer', 'no global definitions loaded')
        # - add local style definitions in doc
        local_styledef = dict()
        try:
            local_styledef = meta.get_content(self.get_metadata(),
                                              'styledef',
                                              'MetaMap')
            info.log('INFO', 'panzer', 'local:')
            for line in info.pretty_keys(local_styledef):
                info.log('INFO', 'panzer', '  ' + line)
            overridden = [key for key in local_styledef
                          if key in global_styledef]
            for key in overridden:
                info.log('INFO', 'panzer',
                         'local definition "%s" overrides global' % key)
            (self.styledef).update(local_styledef)
        except error.MissingField as err:
            info.log('DEBUG', 'panzer', err)
        except error.WrongType as err:
            info.log('ERROR', 'panzer', err)

    def populate_style(self):
        """ populate self.style and stylefull, expanding style hierarchy """
        info.log('INFO', 'panzer', info.pretty_title('document style'))
        # - try to extract value of style field
        try:
            self.style = meta.get_list_or_inline(self.get_metadata(), 'style')
        except error.MissingField:
            info.log('INFO', 'panzer',
                     'no "style" field found, run only pandoc')
            return
        except error.WrongType as err:
            info.log('ERROR', 'panzer', err)
            return
        info.log('INFO', 'panzer', 'style:')
        info.log('INFO', 'panzer', info.pretty_list(self.style))
        # - expand the style hierarchy
        self.stylefull = meta.expand_style_hierarchy(self.style, self.styledef)
        info.log('INFO', 'panzer', 'full hierarchy:')
        info.log('INFO', 'panzer', info.pretty_list(self.stylefull))

    def build_runlist(self):
        """ populate runlist with metadata """
        info.log('INFO', 'panzer', info.pretty_title('run list'))
        metadata = self.get_metadata()
        runlist = self.runlist
        for kind in const.RUNLIST_KIND:
            # - sanity check
            try:
                field_type = meta.get_type(metadata, kind)
                if field_type != 'MetaList':
                    info.log('ERROR', 'panzer',
                             'value of field "%s" should be of type "MetaList"'
                             '---found value of type "%s", ignoring it'
                             % (kind, field_type))
                    continue
            except error.MissingField:
                pass
            # - if 'filter', add filter list specified on command line first
            if kind == 'filter':
                for cmd in self.options['pandoc']['filter']:
                    entry = dict()
                    entry['kind'] = 'filter'
                    entry['status'] = const.QUEUED
                    entry['command'] = cmd[0]
                    entry['arguments'] = list()
                    runlist.append(entry)
            #  - add commands specified in metadata
            if kind in metadata:
                entries = meta.get_runlist(metadata, kind, self.options)
                runlist.extend(entries)
        # - now some cleanup:
        # -- filters: add writer as first argument
        for entry in runlist:
            if entry['kind'] == 'filter':
                entry['arguments'].insert(0, self.options['pandoc']['write'])
        # -- postprocessors: remove them if output kind is pdf
        # .. or if a binary writer is selected
        if self.options['pandoc']['pdf_output'] \
        or self.options['pandoc']['write'] in const.BINARY_WRITERS:
            new_runlist = list()
            for entry in runlist:
                if entry['kind'] == 'postprocess':
                    info.log('INFO', 'panzer',
                             'postprocess "%s" skipped --- output of pandoc is binary file'
                             % entry['command'])
                    continue
                new_runlist.append(entry)
            runlist = new_runlist
        msg = info.pretty_runlist(runlist)
        for line in msg:
            info.log('INFO', 'panzer', line)
        self.runlist = runlist

    def json_message(self):
        """ return json message to pass to executables
            and inject json message into `panzer_reserved` field """
        metadata = self.get_metadata()
        # - delete old 'panzer_reserved' key
        if 'panzer_reserved' in metadata:
            del metadata['panzer_reserved']
        # - build new json_message
        data = [{'metadata':  metadata,
                 'template':  self.template,
                 'style':     self.style,
                 'stylefull': self.stylefull,
                 'styledef':  self.styledef,
                 'runlist':   self.runlist,
                 'options':   self.options}]
        json_message = json.dumps(data)
        # - inject into metadata
        content = [{"t": "CodeBlock",
                    "c": [["", [], []], json_message]}]
        meta.set_content(metadata, 'panzer_reserved', content, 'MetaBlocks')
        self.set_metadata(metadata)
        # - return json_message
        return json_message

    def purge_style_fields(self):
        """ remove metadata fields specific to panzer """
        kill_list = const.RUNLIST_KIND
        kill_list += ['style']
        kill_list += ['styledef']
        kill_list += ['template']
        metadata = self.get_metadata()
        new_metadata = {key: metadata[key]
                        for key in metadata
                        if key not in kill_list}
        self.set_metadata(new_metadata)

    def get_metadata(self):
        """ return metadata of ast """
        return meta.get_metadata(self.ast)

    def set_metadata(self, new_metadata):
        """ set metadata branch to new_metadata """
        try:
            self.ast[0]['unMeta'] = new_metadata
        except (IndexError, KeyError):
            self.ast = [{'unMeta': new_metadata}, []]

    def transform(self):
        """ transform using style """
        writer = self.options['pandoc']['write']
        info.log('INFO', 'panzer', 'writer:')
        info.log('INFO', 'panzer', '  %s' % writer)
        # 1. Do transform
        # - start with blank metadata
        new_metadata = dict()
        # - add styles one by one
        for style in self.stylefull:
            new_metadata = meta.update_metadata(new_metadata,
                                                meta.get_nested_content(
                                                    self.styledef,
                                                    [style, 'all'],
                                                    'MetaMap'))
            new_metadata = meta.update_metadata(new_metadata,
                                                meta.get_nested_content(
                                                    self.styledef,
                                                    [style, writer],
                                                    'MetaMap'))
        # - add local metadata in document
        local_data = self.get_metadata()
        # -- add items from additive fields in local metadata
        new_metadata = meta.update_additive_lists(new_metadata, local_data)
        # -- delete those fields
        local_data = {key: local_data[key]
                      for key in local_data
                      if key not in const.RUNLIST_KIND}
        # -- add all other (non-additive) fields in
        new_metadata.update(local_data)
        # 2. Apply kill rules to trim lists
        for field in const.RUNLIST_KIND:
            try:
                original_list = meta.get_content(new_metadata,
                                                 field, 'MetaList')
                trimmed_list = meta.apply_kill_rules(original_list)
                if trimmed_list:
                    meta.set_content(new_metadata, field,
                                     trimmed_list, 'MetaList')
                else:
                    # if all items killed, delete field
                    del new_metadata[field]
            except error.MissingField:
                continue
            except error.WrongType as err:
                info.log('WARNING', 'panzer', err)
                continue
        # 3. Set template
        try:
            template_raw = meta.get_content(new_metadata, 'template',
                                            'MetaInlines')
            template_str = pandocfilters.stringify(template_raw)
            self.template = util.resolve_path(template_str, 'template',
                                              self.options)
        except (error.MissingField, error.WrongType) as err:
            info.log('DEBUG', 'panzer', err)
        if self.template:

            info.log('INFO', 'panzer', info.pretty_title('template'))
            info.log('INFO', 'panzer', '  %s' % info.pretty_path(self.template))
        # 4. Update document
        self.set_metadata(new_metadata)

    def run_scripts(self, kind, do_not_stop=False):
        """ execute commands of kind listed in runlist """
        # - check if no run list to run
        to_run = [entry for entry in self.runlist if entry['kind'] == kind]
        if not to_run:
            return
        info.log('INFO', 'panzer', info.pretty_title(kind))
        # - maximum number of executables to run
        for i, entry in enumerate(self.runlist):
            # - skip entries that are not of the right kind
            if entry['kind'] != kind:
                continue
            # - build the command to run
            command = [entry['command']] + entry['arguments']
            filename = os.path.basename(command[0])
            info.log('INFO', 'panzer',
                     info.pretty_runlist_entry(i,
                                               len(self.runlist),
                                               ' '.join(command)))
            info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
            # - run the command
            stderr = str()
            try:
                entry['status'] = const.RUNNING
                process = subprocess.Popen(command,
                                           stdin=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                # send panzer's json message to scripts via stdin
                in_pipe = self.json_message()
                in_pipe_bytes = in_pipe.encode(const.ENCODING)
                stderr_bytes = process.communicate(input=in_pipe_bytes)[1]
                entry['status'] = const.DONE
                stderr = stderr_bytes.decode(const.ENCODING)
                if stderr:
                    entry['stderr'] = info.decode_stderr_json(stderr)
            except OSError as err:
                entry['status'] = const.FAILED
                info.log('ERROR', filename, err)
                continue
            except Exception as err:        # pylint: disable=W0703
                # if do_not_stop: always run next script
                # disable pylint warnings:
                #     + Catching too general exception
                entry['status'] = const.FAILED
                if do_not_stop:
                    info.log('ERROR', filename, err)
                    continue
                else:
                    raise
            finally:
                info.log_stderr(stderr, filename)

    def pipe_through(self, kind):
        """ pipe through external command listed in runlist """
        to_run = [entry for entry in self.runlist if entry['kind'] == kind]
        if not to_run:
            return
        info.log('INFO', 'panzer', info.pretty_title(kind))
        # 1. Set up incoming pipe
        if kind == 'filter':
            in_pipe = json.dumps(self.ast)
        elif kind == 'postprocess':
            in_pipe = self.output
        else:
            raise error.InternalError('illegal invocation of '
                                      '"pipe" in panzer.py')
        # 2. Set up outgoing pipe in case of failure
        out_pipe = in_pipe
        # 3. Run commands
        for i, entry in enumerate(self.runlist):
            if entry['kind'] != kind:
                continue
            # - add debugging info
            command = [entry['command']] + entry['arguments']
            filename = os.path.basename(command[0])
            info.log('INFO', 'panzer',
                     info.pretty_runlist_entry(i,
                                               len(self.runlist),
                                               ' '.join(command)))
            info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
            # - run the command and log any errors
            stderr = str()
            try:
                entry['status'] = const.RUNNING
                self.json_message()
                process = subprocess.Popen(command,
                                           stderr=subprocess.PIPE,
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE)
                in_pipe_bytes = in_pipe.encode(const.ENCODING)
                out_pipe_bytes, stderr_bytes = \
                    process.communicate(input=in_pipe_bytes)
                entry['status'] = const.DONE
                out_pipe = out_pipe_bytes.decode(const.ENCODING)
                stderr = stderr_bytes.decode(const.ENCODING)
                if stderr:
                    entry['stderr'] = info.decode_stderr_json(stderr)
                in_pipe = out_pipe
            except OSError as err:
                entry['status'] = const.FAILED
                info.log('ERROR', filename, err)
                continue
            except Exception:
                entry['status'] = const.FAILED
                raise
            finally:
                info.log_stderr(stderr, filename)
        # 4. Update document's data with output from commands
        if kind == 'filter':
            try:
                self.ast = json.loads(out_pipe)
            except ValueError:
                info.log('ERROR', 'panzer',
                         'failed to receive json object from filters'
                         '---ignoring all filters')
                return
        elif kind == 'postprocess':
            self.output = out_pipe

    def pandoc(self):
        """ run pandoc on document

        Normally, input to pandoc is passed via stdin and output received via
        stout. Exception is when the output file has .pdf extension or a binary
        writer selected. Then, output is simply the binary file that panzer
        does not process further, and internal document not updated by pandoc.
        """
        # 1. Build pandoc command
        command = ['pandoc']
        command += ['-']
        command += ['--read', 'json']
        command += ['--write', self.options['pandoc']['write']]
        if self.options['pandoc']['pdf_output'] \
        or self.options['pandoc']['write'] in const.BINARY_WRITERS:
            command += ['--output', self.options['pandoc']['output']]
        else:
            command += ['--output', '-']
        # - template specified on cli has precedence
        if self.options['pandoc']['template']:
            command += ['--template=%s' % self.options['pandoc']['template']]
        elif self.template:
            command += ['--template=%s' % self.template]
        # - remaining options
        command += self.options['pandoc']['options']
        # 2. Prefill input and output pipes
        in_pipe = json.dumps(self.ast)
        out_pipe = str()
        stderr = str()
        # 3. Run pandoc command
        info.log('INFO', 'panzer', info.pretty_title('pandoc'))
        if self.options['pandoc']['options']:
            info.log('INFO', 'panzer', 'running with options:')
            info.log('INFO', 'panzer',
                     info.pretty_list(self.options['pandoc']['options'],
                                      separator=' '))
        else:
            info.log('INFO', 'panzer', 'running')
        info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
        try:
            process = subprocess.Popen(command,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
            in_pipe_bytes = in_pipe.encode(const.ENCODING)
            out_pipe_bytes, stderr_bytes = \
                process.communicate(input=in_pipe_bytes)
            out_pipe = out_pipe_bytes.decode(const.ENCODING)
            stderr = stderr_bytes.decode(const.ENCODING)
        except OSError as err:
            info.log('ERROR', 'pandoc', err)
        finally:
            info.log_stderr(stderr)
        # 4. Deal with output of pandoc
        if self.options['pandoc']['pdf_output'] \
        or self.options['pandoc']['write'] in const.BINARY_WRITERS:
            # do nothing with a binary output
            pass
        else:
            self.output = out_pipe

    def write(self):
        """ write document """
        # case 1: pdf or binary file as output
        if self.options['pandoc']['pdf_output'] \
        or self.options['pandoc']['write'] in const.BINARY_WRITERS:
            info.log('DEBUG', 'panzer', 'output to binary file by pandoc')
            return
        # case 2: no output generated
        if not self.output and self.options['pandoc']['write'] != 'rtf':
            # hack for rtf writer to get around issue:
            # https://github.com/jgm/pandoc/issues/1732
            # probably no longer needed as now fixed in pandoc 1.13.2
            info.log('DEBUG', 'panzer', 'no output to write')
            return
        # case 3: stdout as output
        if self.options['pandoc']['output'] == '-':
            sys.stdout.buffer.write(self.output.encode(const.ENCODING))
            sys.stdout.flush()
            info.log('DEBUG', 'panzer', 'output written stdout by panzer')
        # case 4: output to file
        else:
            with open(self.options['pandoc']['output'], 'w',
                      encoding=const.ENCODING) as output_file:
                output_file.write(self.output)
                output_file.flush()
            info.log('INFO', 'panzer', 'output written to "%s"'
                     % self.options['pandoc']['output'])

