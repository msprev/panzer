""" Support functions for non-core operations """
import os
import subprocess
from . import const
from . import error
from . import info

def check_pandoc_exists():
    """ check pandoc exists """
    try:
        stdout_bytes = subprocess.check_output(["pandoc", "--version"])
        stdout = stdout_bytes.decode(const.ENCODING)
    except OSError as err:
        if err.errno == os.errno.ENOENT:
            raise error.SetupError('pandoc not found')
        else:
            raise error.SetupError(err)
    stdout_list = stdout.splitlines()
    pandoc_ver = stdout_list[0].split(' ')[1]
    if versiontuple(pandoc_ver) < versiontuple(const.REQUIRE_PANDOC_ATLEAST):
        raise error.SetupError('pandoc %s or greater required'
                               '---found pandoc version %s'
                               % (const.REQUIRE_PANDOC_ATLEAST, pandoc_ver))

def versiontuple(version_string):
    """ return tuple of version_string """
    # pylint: disable=W0141
    # disable warning for using builtin 'map'
    return tuple(map(int, (version_string.split("."))))

def check_support_directory(options):
    """ check support directory exists """
    if options['panzer']['panzer_support'] != const.DEFAULT_SUPPORT_DIR:
        if not os.path.exists(options['panzer']['panzer_support']):
            info.log('ERROR', 'panzer',
                     'panzer support directory "%s" not found'
                     % options['panzer']['panzer_support'])
            info.log('WARNING', 'panzer',
                     'using default panzer support directory: %s'
                     % const.DEFAULT_SUPPORT_DIR)
            options['panzer']['panzer_support'] = const.DEFAULT_SUPPORT_DIR
    if not os.path.exists(const.DEFAULT_SUPPORT_DIR):
        info.log('WARNING', 'panzer',
                 'default panzer support directory "%s" not found'
                 % const.DEFAULT_SUPPORT_DIR)
    os.environ['PANZER_SHARED'] = \
        os.path.join(options['panzer']['panzer_support'], 'shared')

def resolve_path(filename, kind, options):
    """ return path to filename of kind field """
    basename = os.path.splitext(filename)[0]
    paths = list()
    paths.append(filename)
    paths.append(os.path.join('panzer', kind, filename))
    paths.append(os.path.join('panzer', kind, basename, filename))
    paths.append(os.path.join(options['panzer']['panzer_support'], kind,
                              filename))
    paths.append(os.path.join(options['panzer']['panzer_support'], kind,
                              basename,
                              filename))
    for path in paths:
        if os.path.exists(path):
            return path
    return filename
