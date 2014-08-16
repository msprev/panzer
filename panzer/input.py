import argparse
import os
import subprocess
import tempfile
import exception

# Load documents

def load(options):
    """ return ast from running pandoc on input documents """
    # 1. Build pandoc command
    command = options['pandoc']['input'].copy()
    if options['pandoc']['read']:
        command += ['--read', options['pandoc']['read']]
    command += ['--write', 'json', '--output', '-']
    command += options['pandoc']['options']
    log('DEBUG', 'panzer', 'pandoc %s' % ' '.join(command))
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
        raise exception.BadASTError('failed to receive valid '
                                'json object from pandoc')
    return ast

def load_styledef(options):
    """ return metadata branch of styles.yaml as dict """
    filename = os.path.join(options['panzer']['panzer_support'], 'styles.yaml')
    if not os.path.exists(filename):
        log('ERROR', 'panzer', 'default styles file not found: %s' % filename)
        return {}
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
    log('DEBUG', 'panzer', 'pandoc %s' % ' '.join(command))
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
        raise exception.BadASTError('failed to receive valid '
                                'json object from pandoc')
    # - return metadata branch of dict
    if not ast:
        return {}
    else:
        return get_metadata(ast)

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
