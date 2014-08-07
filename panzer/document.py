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

