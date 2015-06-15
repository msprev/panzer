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
    - ast:         pandoc abstract syntax tree of document
    - style:       list of styles for document
    - stylefull:   full list of styles including all parents
    - styledef:    style definitions
    - runlist:     run list for document
    - options:     panzer and pandoc command line options
    - template:    template for document
    - output:      string filled with output when processing complete
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
        self.template = None
        self.output = None
        self.options = {
            'panzer': {
                'panzer_support'  : const.DEFAULT_SUPPORT_DIR,
                'debug'           : str(),
                'quiet'           : False,
                'strict'          : False,
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
                'options'    : {'r': dict(), 'w': dict()},
                'mutable'    : {'r': dict(), 'w': dict()}
            }
        }

    def empty(self):
        """
        empty document of all its content but `self.options`
        (used when re-reading from input with new reader command line options)
        """
        # - defaults
        self.ast = const.EMPTY_DOCUMENT
        self.style = list()
        self.stylefull = list()
        self.styledef = dict()
        self.runlist = list()
        self.template = None
        self.output = None

    def populate(self, ast, global_styledef, local_styledef):
        """
        populate document's:
            `self.ast`,
            `self.styledef`,
            `self.style`,
            `self.stylefull`
        remaining fields:
            `self.template` - set after 'transform' applied
            `self.runlist`  - set after 'transform' applied
            `self.output`   - set after 'pandoc' applied
        """
        # - set self.ast:
        if ast:
            self.ast = ast
        else:
            info.log('ERROR', 'panzer', 'source document(s) empty')
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
        self.populate_styledef(global_styledef, local_styledef)
        # - set self.style and self.stylefull
        self.populate_style()
        # - remove any styledef not used in doc
        self.styledef = {key: self.styledef[key]
                         for key in self.styledef
                         if key in self.stylefull}

    def populate_styledef(self, global_styledef, local_styledef):
        """
        populate `self.styledef` from
            `global_styledef`
            `local_styledef`
            document style definition inside `styledef` metadata field
        """
        info.log('INFO', 'panzer', info.pretty_title('style definitions'))
        # - print global style definitions
        if global_styledef:
            info.log('INFO', 'panzer', 'global:')
            for line in info.pretty_keys(global_styledef):
                info.log('INFO', 'panzer', '  ' + line)
        else:
            info.log('INFO', 'panzer', 'no global definitions loaded')
        # - print local style definitions
        overridden = dict()
        if local_styledef:
            info.log('INFO', 'panzer', 'local:')
            for line in info.pretty_keys(local_styledef):
                info.log('INFO', 'panzer', '  ' + line)
        # - extract and print document style definitions
        indoc_styledef = dict()
        try:
            indoc_styledef = meta.get_content(self.get_metadata(), 'styledef', 'MetaMap')
            info.log('INFO', 'panzer', 'document:')
            for line in info.pretty_keys(indoc_styledef):
                info.log('INFO', 'panzer', '  ' + line)
        except error.MissingField as err:
            info.log('DEBUG', 'panzer', err)
        except error.WrongType as err:
            info.log('ERROR', 'panzer', err)
        # - update the style definitions
        (self.styledef).update(global_styledef)
        (self.styledef).update(local_styledef)
        (self.styledef).update(indoc_styledef)
        # - print messages about overriding
        messages = list()
        messages += ['local document definition of "%s" overrides global definition of "%s"'
                     % (key, key)
                     for key in self.styledef
                     if key in local_styledef
                     and key in global_styledef]
        messages += ['document definition of "%s" overrides local definition of "%s"'
                     % (key, key)
                     for key in self.styledef
                     if key in indoc_styledef
                     and key in local_styledef]
        messages += ['document definition of "%s" overrides global definition of "%s"'
                     % (key, key)
                     for key in self.styledef
                     if key in indoc_styledef
                     and key in global_styledef
                     and key not in local_styledef]
        for m in messages:
            info.log('INFO', 'panzer', m)

    def populate_style(self):
        """
        populate `self.style` and `self.stylefull`
        """
        info.log('INFO', 'panzer', info.pretty_title('document style'))
        # - try to extract value of style field
        try:
            self.style = meta.get_list_or_inline(self.get_metadata(), 'style')
            if self.style == ['']:
                raise error.MissingField
        except error.MissingField:
            info.log('INFO', 'panzer', 'no "style" field found, run only pandoc')
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
        """ populate `self.runlist` using `self.ast`'s metadata """
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

    def apply_commandline(self, metadata):
        """
        1. parse `self.ast`'s `commandline` field
        2. apply result to update self.options['pandoc']['options']
        (the result are the options used for calling pandoc)
        """
        if 'commandline' not in metadata:
            return
        commandline = meta.parse_commandline(metadata)
        if not commandline:
            return
        self.options['pandoc']['options'] = \
            meta.update_pandoc_options(self.options['pandoc']['options'],
                                       commandline,
                                       self.options['pandoc']['mutable'])

    def lock_commandline(self):
        """
        make the commandline line options all immutable
        """
        for phase in self.options['pandoc']['mutable']:
            for opt in self.options['pandoc']['mutable'][phase]:
                self.options['pandoc']['mutable'][phase][opt] = False

    def json_message(self):
        """
        create json message to pass to executables. This method does 2 things:

        1. injects json message into `panzer_reserved` field of `self.ast`
        2. returns json message as a string
        """
        metadata = self.get_metadata()
        # - delete old 'panzer_reserved' key
        if 'panzer_reserved' in metadata:
            del metadata['panzer_reserved']
        # - create a decrapified version of self.options
        # - remove stuff only of internal use to panzer
        options = dict()
        options['panzer'] = dict(self.options['panzer'])
        options['pandoc'] = dict(self.options['pandoc'])
        del options['pandoc']['template']
        del options['pandoc']['filter']
        del options['pandoc']['mutable']
        # - build new json_message
        data = [{'metadata':    metadata,
                 'template':    self.template,
                 'style':       self.style,
                 'stylefull':   self.stylefull,
                 'styledef':    self.styledef,
                 'runlist':     self.runlist,
                 'options':     options}]
        json_message = json.dumps(data)
        # - inject into metadata
        content = {"json_message": {
            "t": "MetaBlocks",
            "c": [{"t": "CodeBlock", "c": [["", ["json"], []], json_message]}]}}
        meta.set_content(metadata, 'panzer_reserved', content, 'MetaMap')
        self.set_metadata(metadata)
        # - return json_message
        return json_message

    def purge_style_fields(self):
        """ remove metadata fields from `self.ast` used to call panzer """
        kill_list = const.RUNLIST_KIND
        kill_list += ['style']
        kill_list += ['styledef']
        kill_list += ['template']
        kill_list += ['commandline']
        metadata = self.get_metadata()
        new_metadata = {key: metadata[key]
                        for key in metadata
                        if key not in kill_list}
        self.set_metadata(new_metadata)

    def get_metadata(self):
        """ return metadata branch of `self.ast` """
        return meta.get_metadata(self.ast)

    def set_metadata(self, new_metadata):
        """ set metadata branch of `self.ast` to `new_metadata` """
        try:
            self.ast[0]['unMeta'] = new_metadata
        except (IndexError, KeyError):
            self.ast = [{'unMeta': new_metadata}, []]

    def transform(self):
        """ transform `self` by applying styles listed in `self.stylefull` """
        writer = self.options['pandoc']['write']
        info.log('INFO', 'panzer', 'writer:')
        info.log('INFO', 'panzer', '  %s' % writer)
        # 1. Do transform
        # - start with blank metadata
        new_metadata = dict()
        # - apply styles, first to last
        for style in self.stylefull:
            all_s = meta.get_nested_content(self.styledef, [style, 'all'], 'MetaMap')
            new_metadata = meta.update_metadata(new_metadata, all_s)
            self.apply_commandline(all_s)
            cur_s = meta.get_nested_content(self.styledef, [style, writer], 'MetaMap')
            new_metadata = meta.update_metadata(new_metadata, cur_s)
            self.apply_commandline(cur_s)
        # - add in document metadata in document
        indoc_data = self.get_metadata()
        # -- add items from additive fields in indoc metadata
        new_metadata = meta.update_additive_lists(new_metadata, indoc_data)
        # -- add all other (non-additive) fields in
        new_metadata.update(indoc_data)
        # -- apply items from indoc `commandline` field
        self.apply_commandline(indoc_data)
        # 2. Apply kill rules to trim run lists
        for field in const.RUNLIST_KIND:
            try:
                original_list = meta.get_content(new_metadata, field, 'MetaList')
                trimmed_list = meta.apply_kill_rules(original_list)
                if trimmed_list:
                    meta.set_content(new_metadata, field, trimmed_list, 'MetaList')
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
            if meta.get_type(new_metadata, 'template') == 'MetaInlines':
                template_raw = meta.get_content(new_metadata, 'template', 'MetaInlines')
                template_str = pandocfilters.stringify(template_raw)
            elif meta.get_type(new_metadata, 'template') == 'MetaString':
                template_str = meta.get_content(new_metadata, 'template', 'MetaString')
                if template_str == '':
                    raise error.MissingField
            else:
                raise error.WrongType
            self.template = util.resolve_path(template_str, 'template', self.options)
        except (error.MissingField, error.WrongType) as err:
            info.log('DEBUG', 'panzer', err)
        if self.template:
            info.log('INFO', 'panzer', info.pretty_title('template'))
            info.log('INFO', 'panzer', '  %s' % info.pretty_path(self.template))
        # 4. Update document's metadata
        self.set_metadata(new_metadata)

    def run_scripts(self, kind, do_not_stop=False):
        """
        execute commands of type `kind` listed in `self.runlist`
        `do_not_stop`:  runlist executed no matter what errors occur
                        (used by cleanup scripts)
        """
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
            filename = os.path.basename(entry['command'])
            info.log('INFO', 'panzer',
                     info.pretty_runlist_entry(i,
                                               len(self.runlist),
                                               entry['command'],
                                               entry['arguments']))
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
        """
        pipe through external command listed in `self.runlist`
        (`kind` could be 'filter' or 'postprocess')
        """
        if kind != 'filter' and kind != 'postprocess':
            raise error.InternalError('illegal invocation of '
                                      '"pipe" in panzer.py')
        to_run = [entry for entry in self.runlist if entry['kind'] == kind]
        if not to_run:
            return
        info.log('INFO', 'panzer', info.pretty_title(kind))
        # Run commands
        for i, entry in enumerate(self.runlist):
            if entry['kind'] != kind:
                continue
            # - add debugging info
            command = [entry['command']] + entry['arguments']
            filename = os.path.basename(entry['command'])
            info.log('INFO', 'panzer',
                     info.pretty_runlist_entry(i,
                                               len(self.runlist),
                                               entry['command'],
                                               entry['arguments']))
            info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
            # - run the command and log any errors
            stderr = str()
            try:
                entry['status'] = const.RUNNING
                self.json_message()
                # Set up incoming pipe
                if kind == 'filter':
                    in_pipe = json.dumps(self.ast)
                elif kind == 'postprocess':
                    in_pipe = self.output
                # Set up outgoing pipe in case of failure
                out_pipe = in_pipe
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
                             'failed to receive json object from filter'
                             '---skipping filter')
                    continue
            elif kind == 'postprocess':
                self.output = out_pipe

    def pandoc(self):
        """
        run pandoc on document

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
        opts = meta.build_cli_options(self.options['pandoc']['options']['w'])
        command += opts
        # 2. Prefill input and output pipes
        in_pipe = json.dumps(self.ast)
        out_pipe = str()
        stderr = str()
        # 3. Run pandoc command
        info.log('INFO', 'panzer', info.pretty_title('pandoc write'))
        if opts:
            info.log('INFO', 'panzer', 'pandoc writing with options:')
            info.log('INFO', 'panzer', info.pretty_list(opts, separator=' '))
        else:
            info.log('INFO', 'panzer', 'running')
        info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
        try:
            info.time_stamp('ready to do popen')
            process = subprocess.Popen(command,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE)
            info.time_stamp('popen done')
            in_pipe_bytes = in_pipe.encode(const.ENCODING)
            out_pipe_bytes, stderr_bytes = \
                process.communicate(input=in_pipe_bytes)
            info.time_stamp('communicate done')
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
        """
        writes `self.output` to disk or stdout
        used to write document's output
        """
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

