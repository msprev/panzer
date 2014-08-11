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
import pandocfilters
import shlex
import subprocess
import sys
import tempfile

import os
import subprocess
import sys
from .version import VERSION
import .document
import .exception
from .info import log
__version__ = VERSION

# Main function

def main():
    """ the main function """
    # - create a blank document
    doc = document.Document()
    try:
        check_pandoc_exists()
        doc.options = parse_cli_options(options)
        info.start_logger(doc.options)
        util.check_support_directory(doc.options)
        global_styledef = load.load_styledef(doc.options)
        ast = load.load(doc.options)
        doc.populate(ast, global_styledef)
        doc.transform()
        doc.build_run_list()
        doc.purge_styles()
        doc.run_scripts('preflight')
        doc.pipe_through('filter')
        doc.pandoc()
        doc.pipe_through('postprocess')
        doc.write()
        doc.run_scripts('postflight')
    except exception.SetupError as error:
        # - errors that occur before logging starts
        print(error, file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        log('CRITICAL', 'panzer',
            'cannot continue because of fatal error')
        sys.exit(1)
    except (KeyError,
            exception.KeyError,
            exception.BadASTError,
            exception.TypeError,
            exception.InternalError) as error:
        # - panzer exceptions not caught elsewhere, should have been
        log('CRITICAL', 'panzer', error)
        sys.exit(1)
    finally:
        doc.run_scripts('cleanup', force_run=True)
        # - if temp file created in setup, remove it
        if doc.options['panzer']['stdin_temp_file']:
            os.remove(doc.options['panzer']['stdin_temp_file'])
            log('DEBUG', 'panzer',
                'deleted temp file: %s'
                % doc.options['panzer']['stdin_temp_file'])
        log('DEBUG', 'panzer', '>>>>> panzer quits <<<<<')
    # - successful exit
    sys.exit(0)

if __name__ == '__main__':
    main()
