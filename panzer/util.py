# disk

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
