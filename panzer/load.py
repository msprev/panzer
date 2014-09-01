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
    except OSError as e:
        log('ERROR', 'pandoc', e)
    finally:
        log_stderr(stderr)
    try:
        ast = json.loads(out_pipe)
    except ValueError:
        raise error.BadASTError('failed to receive valid '
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
    except OSError as e:
        log('ERROR', 'pandoc', e)
    finally:
        log_stderr(stderr)
    # - convert json to python dict
    ast = None
    try:
        ast = json.loads(out_pipe)
    except ValueError:
        raise error.BadASTError('failed to receive valid '
                                'json object from pandoc')
    # - return metadata branch of dict
    if not ast:
        return {}
    else:
        return get_metadata(ast)

