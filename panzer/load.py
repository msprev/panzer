""" loading documents into panzer """

import os
import json
import subprocess
from . import error
from . import info
from . import const
from . import meta

def load(options):
    """ return ast from running pandoc on input documents """
    # 1. Build pandoc command
    command = options['pandoc']['input'].copy()
    if options['pandoc']['read']:
        command += ['--read', options['pandoc']['read']]
    command += ['--write', 'json', '--output', '-']
    command += options['pandoc']['options']
    info.log('DEBUG', 'panzer', 'pandoc %s' % ' '.join(command))
    command = ['pandoc'] + command
    out_pipe = str()
    stderr = str()
    ast = None
    try:
        process = subprocess.Popen(command,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        out_pipe_bytes, stderr_bytes = process.communicate()
        out_pipe = out_pipe_bytes.decode(const.ENCODING)
        stderr = stderr_bytes.decode(const.ENCODING)
    except OSError as err:
        info.log('ERROR', 'pandoc', err)
    finally:
        info.log_stderr(stderr)
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
        info.log('ERROR', 'panzer',
                 'default styles file not found: %s' % filename)
        return dict()
    # - slurp styles.yaml
    data = []
    with open(filename, 'r', encoding=const.ENCODING) as styles_file:
        data = styles_file.readlines()
    # - top and tail with metadata markings
    data.insert(0, "---\n")
    data.append("...\n")
    data_string = ''.join(data)
    info.log('DEBUG', 'panzer', info.pretty_lined('STYLES METADATA'))
    info.log('DEBUG', 'panzer', data_string)
    # - build pandoc command
    command = ['pandoc']
    command += ['-']
    command += ['--write', 'json']
    command += ['--output', '-']
    info.log('DEBUG', 'panzer', 'pandoc %s' % ' '.join(command))
    # - send to pandoc to convert to json
    in_pipe = data_string
    out_pipe = ''
    stderr = ''
    try:
        process = subprocess.Popen(command,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        in_pipe_bytes = in_pipe.encode(const.ENCODING)
        out_pipe_bytes, stderr_bytes = process.communicate(input=in_pipe_bytes)
        out_pipe = out_pipe_bytes.decode(const.ENCODING)
        stderr = stderr_bytes.decode(const.ENCODING)
    except OSError as err:
        info.log('ERROR', 'pandoc', err)
    finally:
        info.log_stderr(stderr)
    # - convert json to python dict
    ast = None
    try:
        ast = json.loads(out_pipe)
    except ValueError:
        raise error.BadASTError('failed to receive valid '
                                'json object from pandoc')
    # - return metadata branch of dict
    if not ast:
        return dict()
    else:
        return meta.get_metadata(ast)

