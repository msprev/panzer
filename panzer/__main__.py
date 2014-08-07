#!/usr/bin/env python3
""" panzer: pandoc with styles

for more info: <https://github.com/msprev/panzer>

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
"""

import argparse
import json
import logging
import logging.config
import os
import pandocfilters
import shlex
import subprocess
import sys
import tempfile

from .version import VERSION
from .util import *
from .metadata import *
from .disk import *
from .document import *
__version__ = VERSION

REQUIRE_PANDOC_ATLEAST = "1.12.1"
DEFAULT_SUPPORT_DIR = os.path.join(os.path.expanduser('~'), '.panzer')
ENCODING = 'utf8'
T = 't'
C = 'c'
ADDITIVE_FIELDS = ['preflight',
                   'filter',
                   'postprocess',
                   'postflight',
                   'cleanup']

# Main function

def main():
    """ the main function """
    options = default_options()
    run_lists = default_run_lists()
    json_message = make_json_message(Document(), run_lists, options)
    try:
        check_pandoc_exists()
        options = parse_cli_options(options)
        start_logger(options)
        check_support_directory(options)
        ast = load(options)
        global_styledef = load_yaml_styledef(options)
        doc = Document()
        doc.populate(ast, global_styledef)
        doc.transform(options)
        run_lists = build_run_lists(doc.get_metadata(), run_lists, options)
        doc.purge_styles()
        json_message = make_json_message(doc, run_lists, options)
        doc.inject_panzer_reserved_field(json_message)
        run_scripts('preflight', run_lists, json_message)
        doc.pipe_through('filter', run_lists)
        doc.pandoc(options)
        doc.pipe_through('postprocess', run_lists)
        doc.write(options)
        run_scripts('postflight', run_lists, json_message)
    except PanzerSetupError as error:
        # - errors that occur before logging starts
        print(error, file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        log('CRITICAL',
            'panzer',
            'cannot continue because of fatal error')
        sys.exit(1)
    except (KeyError,
            PanzerKeyError,
            PanzerBadASTError,
            PanzerTypeError,
            PanzerInternalError) as error:
        # - panzer exceptions not caught elsewhere, should have been
        log('CRITICAL', 'panzer', error)
        sys.exit(1)
    finally:
        run_scripts('cleanup', run_lists, json_message, force_run=True)
        # - if temp file created in setup, remove it
        if options['panzer']['stdin_temp_file']:
            os.remove(options['panzer']['stdin_temp_file'])
            log('DEBUG',
                'panzer',
                'deleted temp file: %s'
                % options['panzer']['stdin_temp_file'])
        log('DEBUG', 'panzer', '>>>>> panzer quits <<<<<')
    # - successful exit
    sys.exit(0)

if __name__ == '__main__':
    main()

