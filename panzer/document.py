""" panzer document class and its methods """
import json
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
    - fullstyle : full list of styles including all parents
    - styledef  : style definitions
    - runlist   : run list for document
    - options   : cli options for document
    - template  : template for document
    - output    : string filled with output when processing complete
    """
    def __init__(self):
        """ new blank document """
        # - defaults
        self.ast = const.EMPTY_DOCUMENT
        self.style = list()
        self.fullstyle = list()
        self.styledef = dict()
        self.run_list = list()
        self.options = {
            'panzer': {
                'panzer_support'  : const.DEFAULT_SUPPORT_DIR,
                'debug'           : False,
                'verbose'         : 1,
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
        log('DEBUG', 'panzer', info.pretty_lined('Original Metadata'))
        log('DEBUG', 'panzer', info.json_dump(metadata))
        try:
            meta.get_content(metadata, 'panzer_reserved')
            info.log('ERROR', 'panzer',
                     'special field "panzer_reserved" already in metadata'
                     '---will be overwritten')
        except error.MissingField:
            pass
        # - set self.styledef
        self.populate_styledef(global_styledef)
        # - set self.style
        self.populate_style()
        # - remove any styledef not used in doc
        self.styledef = {key: self.styledef[key]
                         for key in self.styledef
                         if key not in self.fullstyle}

    def populate_styledef(self, global_styledef):
        log('INFO', 'panzer', '-- style definition --')
        # - add global style definitions
        if global_styledef:
            log('INFO', 'panzer', 'global definitions:')
            for line in info.pretty_keys(global_styledef):
                log('INFO', 'panzer', '    ' + line)
            self.styledef = dict(global_styledef)
        else:
            log('INFO', 'panzer', 'no global definitions loaded')
        # - add local style definitions in doc
        local_styledef = dict()
        try:
            local_styledef = meta.get_content(self.get_metadata(),
                                             'styledef', 'MetaMap')
            log('INFO', 'panzer', 'local definitions:')
            for line in debug_pretty_keys(local_styledef):
                log('INFO', 'panzer', '    ' + line)
            overridden = [key for key in local_styledef
                          if key in global_styledef]
            for key in overridden:
                log('INFO', 'panzer', 'local definition "%s" overrides global'
                    % key)
            (self.styledef).update(local_styledef)
        except error.MissingField as err:
            log('DEBUG', 'panzer', err)
        except error.WrongType as err:
            log('ERROR', 'panzer', err)

    def populate_style(self):
        log('INFO', 'panzer', '-- document style --')
        # - try to extract value of style field
        try:
            self.style = get_list_or_inline(self.get_metadata(), 'style')
        except error.MissingField:
            log('INFO', 'panzer', 'no "style" field found, will just run pandoc')
            return
        except error.WrongType as err:
            log('ERROR', 'panzer', err)
            return
        log('INFO', 'panzer', 'style')
        log('INFO', 'panzer', info.pretty_list(self.style)
        # - expand the style hierarchy
        self.fullstyle = self.expand_style_hierarchy()
        log('INFO', 'panzer', 'full hierarchy')
        log('INFO', 'panzer', info.pretty_list(self.fullstyle)
        # - check for, and remove, styles missing definitions
        missing = [key for key in self.style
                   if key not in self.styledef]
        for key in missing:
            log('ERROR', 'panzer', 'style definition for "%s" not found'
                '---ignoring style' % key)
        self.style = [key for key in self.style
                      if key not in missing]

    def build_run_list(self):
        """ populate run_list with metadata """
        info.log('INFO', 'panzer', '-- run list --')
        metadata = self.get_metadata()
        run_list = self.run_list
        for kind in const.RUNLIST_KIND:
            # - if 'filter', add filter list specified on command line first
            if kind == 'filter':
                for cmd in self.options['pandoc']['filter']:
                    entry = dict()
                    entry['kind'] = 'filter'
                    entry['status'] = const.QUEUED
                    entry['command'] = cmd
                    entry['arguments'] = list()
                    run_list.append(entry)
            #  - add commands specified in metadata
            if kind in metadata:
                entries = get_run_list(metadata, kind, self.options)
                run_list.extend(entries)
        # - now some cleanup:
        # -- filters: add writer as first argument
        for entry in run_list:
            if entry['kind'] == 'filter':
                entry['arguments'].insert(0, self.options['pandoc']['write'])
        # -- postprocessors: remove them if output kind is pdf
        if self.options['pandoc']['pdf_output']:
            new_runlist = list()
            for entry in run_list:
                if entry['kind'] == 'postprocess':
                    log('INFO', 'panzer',
                        'postprocess "%s" skipped --- output set to PDF'
                        % entry['command'])
                    continue
                new_runlist.append(entry)
            runlist = new_runlist
        # - pretty print run lists
        for i, entry in enumerate(run_list):
            info.log('INFO', 'panzer',
                     '%s %s "%s"'
                     % (str(i).rjust(2),
                        entry['kind'].ljust(11),
                        entry['command']))
        self.run_list = run_list

    def get_json_message(self):
        """ return json message to pass to executables """
        metadata = self.get_metadata()
        # - delete old 'panzer_reserved' key
        if 'panzer_reserved' in metadata:
            del metadata['panzer_reserved']
        # - build new json_message
        data = [{'metadata'    : metadata,
                 'template'    : self.template,
                 'style'       : self.style,
                 'fullstyle'   : self.fullstyle,
                 'styledef'    : self.styledef,
                 'run_list'    : self.run_list,
                 'cli_options' : self.options}]
        json_message = json.dumps(data)
        # - inject into metadata
        content = [{"t": "CodeBlock",
                    "c": [["", [], []], json_message]}]
        set_content(metadata, 'panzer_reserved', content, 'MetaBlocks')
        self.set_metadata(metadata)
        # - return json_message
        return json_message

    def expand_style_hierarchy(self):
        """ expand style field to include all parent styles """
        pass

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
        return get_metadata(self.ast)

    def set_metadata(self, new_metadata):
        """ set metadata branch to new_metadata """
        try:
            self.ast[0]['unMeta'] = new_metadata
        except (IndexError, KeyError):
            self.ast = [{'unMeta': new_metadata}, []]

    def transform(self):
        """ transform using style """
        writer = self.options['pandoc']['write']
        log('INFO', 'panzer', 'writer "%s"' % writer)
        # 1. Do transform
        # - start with blank metadata
        new_metadata = dict()
        # - add styles one by one
        for style in self.style:
            new_metadata = update_metadata(new_metadata,
                                           get_nested_content(self.styledef, [style, 'default'], 'MetaMap'))
            new_metadata = update_metadata(new_metadata,
                                           get_nested_content(self.styledef, [style, writer], 'MetaMap'))
        # - add metadata specified in document
        new_metadata.update(self.get_metadata())
        # 2. Apply kill rules to trim lists
        for field in const.RUNLIST_KIND:
            try:
                original_list = ast.get_content(new_metadata, field, 'MetaList')
                trimmed_list = apply_kill_rules(original_list)
                if trimmed_list:
                    set_content(new_metadata, field, trimmed_list, 'MetaList')
                else:
                    # if all items killed, delete field
                    del new_metadata[field]
            except error.MissingField:
                continue
            except error.WrongType as err:
                log('WARNING', 'panzer', err)
                continue
        # 3. Set template
        try:
            template_raw = ast.get_content(new_metadata, 'template', 'MetaInlines')
            template_str = pandocfilters.stringify(template_raw)
            self.template = resolve_path(template_str, 'template', self.options)
        except (error.MissingField, error.WrongType) as err:
            log('DEBUG', 'panzer', err)
        if self.template:
            log('INFO', 'panzer', 'template "%s"' % self.template)
        # 4. Update document
        self.set_metadata(new_metadata)

    def run_scripts(self, kind, do_not_stop=False):
        """ execute commands of kind listed in run_list """
        # - check if no run list to run
        to_run = [entry for entry in self.run_list if entry['kind'] == kind]
        if not to_run:
            return
        log('INFO', 'panzer', '-- %s --' % kind)
        # - maximum number of executables to run
        for i, entry in enumerate(self.run_list):
            # - skip entries that are not of the right kind
            if entry['kind'] != kind:
                continue
            # - build the command to run
            command = [entry['command']] + entry['arguments']
            filename = os.path.basename(command[0])
            fullpath = ' '.join(command).replace(os.path.expanduser('~'), '~')
            log('INFO', 'panzer',
                '[%d/%d] "%s"' % (i, len(self.run_list), fullpath))
            # - run the command
            stderr = out_pipe = str()
            try:
                entry['status'] = const.RUNNING
                p = subprocess.Popen(command,
                                     stdin=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                # send panzer's json message to scripts via stdin
                in_pipe = self.get_json_message()
                in_pipe_bytes = in_pipe.encode(ENCODING)
                out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
                entry['status'] = const.DONE
                if out_pipe_bytes:
                    out_pipe = out_pipe_bytes.decode(ENCODING)
                if stderr_bytes:
                    stderr = stderr_bytes.decode(ENCODING)
            except OSError as e:
                entry['status'] = const.FAILED
                log('ERROR', filename, e)
                continue
            except Exception as e:
                # if do_not_stop: always run next script
                entry['status'] = const.FAILED
                if do_not_stop:
                    log('ERROR', filename, e)
                    continue
                else:
                    raise
            finally:
                log_stderr(stderr, filename)

    def pipe_through(self, kind):
        """ pipe through external command listed in run_list """
        to_run = [entry for entry in self.run_list if entry['kind'] == kind]
        if not to_run:
            return
        log('INFO', 'panzer', '-- %s --' % kind)
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
        for i, entry in enumerate(self.run_list):
            # - add debugging info
            command = [entry['command']] + entry['arguments']
            filename = os.path.basename(command[0])
            fullpath = ' '.join(command).replace(os.path.expanduser('~'), '~')
            log('INFO', 'panzer',
                '[%d/%d] "%s"' % (i, len(self.run_list), fullpath))
            # - run the command and log any errors
            stderr = str()
            try:
                entry['status'] = const.RUNNING
                self.get_json_message()
                p = subprocess.Popen(command,
                                     stderr=subprocess.PIPE,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
                in_pipe_bytes = in_pipe.encode(ENCODING)
                out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
                entry['status'] = const.DONE
                out_pipe = out_pipe_bytes.decode(ENCODING)
                stderr = stderr_bytes.decode(ENCODING)
                in_pipe = out_pipe
            except OSError as e:
                entry['status'] = const.FAILED
                log('ERROR', filename, e)
                continue
            except Exception:
                entry['status'] = const.FAILED
                raise
            finally:
                log_stderr(stderr, filename)
        # 4. Update document's data with output from commands
        if kind == 'filter':
            try:
                self.ast = json.loads(out_pipe)
            except ValueError:
                log('ERROR', 'panzer',
                    'failed to receive json object from filters'
                    '---ignoring all filters')
                return
        elif kind == 'postprocess':
            self.output = out_pipe

    def pandoc(self):
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
        command += ['--write', self.options['pandoc']['write']]
        if self.options['pandoc']['pdf_output']:
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
        log('INFO', 'panzer', '-- pandoc --')
        log('INFO', 'panzer', '"%s"' % ' '.join(command))
        try:
            p = subprocess.Popen(command,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE)
            in_pipe_bytes = in_pipe.encode(ENCODING)
            out_pipe_bytes, stderr_bytes = p.communicate(input=in_pipe_bytes)
            out_pipe = out_pipe_bytes.decode(ENCODING)
            stderr = stderr_bytes.decode(ENCODING)
        except OSError as e:
            log('ERROR', 'pandoc', e)
        finally:
            log_stderr(stderr)
        # 4. Deal with output of pandoc
        if self.options['pandoc']['pdf_output']:
            # do nothing with a pdf
            pass
        else:
            self.output = out_pipe

    def write(self):
        """ write document """
        # case 1: pdf as output file
        if self.options['pandoc']['pdf_output']:
            return
        # case 2: stdout as output
        if self.options['pandoc']['output'] == '-':
            sys.stdout.buffer.write(self.output.encode(ENCODING))
            sys.stdout.flush()
        # case 3: any other file as output
        else:
            with open(self.options['pandoc']['output'], 'w',
                      encoding=ENCODING) as output_file:
                output_file.write(self.output)
                output_file.flush()
            log('INFO',
                'panzer',
                'output written to "%s"' % self.options['pandoc']['output'])
