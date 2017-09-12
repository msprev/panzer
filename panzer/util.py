""" Support functions for non-core operations """
import os
import subprocess
import sys
from . import const
from . import error
from . import info

def check_pandoc_exists(options):
    """ check pandoc exists """
    try:
        stdout_bytes = subprocess.check_output([options['panzer']['pandoc'],
                                                "--version"])
        stdout = stdout_bytes.decode(const.ENCODING)
    except PermissionError as err:
        raise error.SetupError('%s cannot be executed as pandoc executable' %
                                options['panzer']['pandoc'])
    except OSError as err:
        if err.errno == os.errno.ENOENT:
            raise error.SetupError('%s not found as pandoc executable' %
                                   options['panzer']['pandoc'])
        else:
            raise error.SetupError(err)
    stdout_list = stdout.splitlines()
    pandoc_ver = stdout_list[0].split(' ')[1]
    # print('pandoc version: %s' % pandoc_ver, file=sys.stderr)
    if versiontuple(pandoc_ver) < versiontuple(const.REQUIRE_PANDOC_ATLEAST):
        raise error.SetupError('pandoc %s or greater required'
                               '---found pandoc version %s'
                               % (const.REQUIRE_PANDOC_ATLEAST, pandoc_ver))
    # check whether to use the new >=1.18 pandoc API or old (<1.18) one
    NEW_PANDOC_API = "1.18"
    if versiontuple(pandoc_ver) < versiontuple(NEW_PANDOC_API):
        const.USE_OLD_API = True
        # print('using old (<1.18) pandoc API')
    # else:
        # print('using new (>=1.18) pandoc API')

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
        info.log('WARNING', 'panzer',
                 'create empty support directory "%s"?'
                 % const.DEFAULT_SUPPORT_DIR)
        input("    Press Enter to continue...")
        create_default_support_dir()
    os.environ['PANZER_SHARED'] = \
        os.path.join(options['panzer']['panzer_support'], 'shared')

def create_default_support_dir():
    """ create a empty panzer support directory """
    # - create .panzer
    os.mkdir(const.DEFAULT_SUPPORT_DIR)
    info.log('INFO', 'panzer', 'created "%s"' % const.DEFAULT_SUPPORT_DIR)
    # - create subdirectories of .panzer
    subdirs = ['preflight',
               'filter',
               'postprocess',
               'postflight',
               'cleanup',
               'template',
               'styles']
    for subdir in subdirs:
        target = os.path.join(const.DEFAULT_SUPPORT_DIR, subdir)
        os.mkdir(target)
        info.log('INFO', 'panzer', 'created "%s"' % target)
    # - create styles.yaml
    style_definitions = os.path.join(const.DEFAULT_SUPPORT_DIR,
                                     'styles',
                                     'styles.yaml')
    open(style_definitions, 'w').close()
    info.log('INFO', 'panzer', 'created empty "styles/styles.yaml"')

def resolve_path(filename, kind, options):
    """ return path to filename of kind field """
    basename = os.path.splitext(filename)[0]
    paths = list()
    paths.append(filename)
    paths.append(os.path.join(kind, filename))
    paths.append(os.path.join(kind, basename, filename))
    paths.append(os.path.join(options['panzer']['panzer_support'], kind,
                              filename))
    paths.append(os.path.join(options['panzer']['panzer_support'], kind,
                              basename,
                              filename))
    for path in paths:
        if os.path.exists(path):
            return path
    return filename

