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
    command = ['pandoc']
    command += options['pandoc']['input'].copy()
    if options['pandoc']['read']:
        command += ['--read', options['pandoc']['read']]
    command += ['--write', 'json', '--output', '-']
    opts =  meta.build_cli_options(options['pandoc']['options']['r'])
    command += opts
    info.log('INFO', 'panzer', info.pretty_title('pandoc read'))
    info.log('DEBUG', 'panzer', 'loading source document(s)')
    info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
    if opts:
        info.log('INFO', 'panzer', 'pandoc reading with options:')
        info.log('INFO', 'panzer', info.pretty_list(opts, separator=' '))
    else:
        info.log('INFO', 'panzer', 'running')
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

def load_all_styledefs(options):
    """
        return global, local styledef pair
        finds global styledef from `.panzer/styles/*.{yaml,yml}`
        finds local styledef from `./styles/*.{yaml,yml}`
    """
    support_dir = doc.options['panzer']['panzer_support']
    info.log('DEBUG', 'panzer', 'loading global style definitions file')
    global_styledef = load_styledef(support_dir, doc.options)
    if global_styledef == {}:
        info.log('WARNING', 'panzer', 'no global style definitions found')
    info.log('DEBUG', 'panzer', 'loading local style definitions file')
    local_styledef = load.load_styledef('.', doc.options)
    return global_styledef, local_styledef

def load_styledef(path, options):
    """
        return metadata branch as dict of styledef file at `path`
        reads from `path/styles/*.{yaml,yaml}`
        (if this fails, checks `path/styles.yaml` as legacy option)
        returns {} if no metadata found
    """
    # - read in style definition data from yaml files
    styles_dir = os.path.join(path, 'styles')
    filenames = list()
    # - read from .panzer/styles/*.{yaml,yml}
    if os.path.exists(styles_dir):
        filenames = [os.path.join(path, 'styles', f)
                     for f in os.listdir(styles_dir)
                     if f.endswith('.yaml')
                     or f.endswith('.yml')]
    # - read .panzer/style.yaml -- legacy option
    elif os.path.exists(os.path.join(path, 'styles.yaml')):
        filenames = [os.path.join(path, 'styles.yaml')]
    data = list()
    for f in filenames:
        with open(f, 'r', encoding=const.ENCODING) as styles_file:
            data += styles_file.readlines()
    if data == []:
        return dict()
    # - top and tail with metadata markings
    data.insert(0, "---\n")
    data.append("...\n")
    data_string = ''.join(data)
    # - build pandoc command
    command = ['pandoc']
    command += ['-']
    command += ['--write', 'json']
    command += ['--output', '-']
    opts =  meta.build_cli_options(options['pandoc']['options']['r'])
    # - remove inappropriate options for styles.yaml
    BAD_OPTS = ['metadata', 'track-changes', 'extract-media']
    opts = [x for x in opts if x not in BAD_OPTS]
    command += opts
    info.log('DEBUG', 'panzer', 'run "%s"' % ' '.join(command))
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

