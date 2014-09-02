#!/usr/bin/env python3
""" panzer: pandoc with styles

for more info: <https://github.com/msprev/panzer>

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
"""

import os
import subprocess
import sys
from . import document
from . import error
from . import info
from . import load
from . import util
from . import cli
from . import version

__version__ = version.VERSION

# Main function

def main():
    """ the main function """
    doc = document.Document()
    try:
        util.check_pandoc_exists()
        doc.options = cli.parse_cli_options(doc.options)
        info.start_logger(doc.options)
        util.check_support_directory(doc.options)
        global_styledef = load.load_styledef(doc.options)
        ast = load.load(doc.options)
        doc.populate(ast, global_styledef)
        doc.transform()
        doc.build_runlist()
        doc.purge_style_fields()
        doc.run_scripts('preflight')
        doc.pipe_through('filter')
        doc.pandoc()
        doc.pipe_through('postprocess')
        doc.write()
        doc.run_scripts('postflight')
    except error.SetupError as err:
        # - errors that occur before logging starts
        print(err, file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        info.log('CRITICAL', 'panzer',
                 'cannot continue because of fatal error')
        sys.exit(1)
    except (KeyError,
            error.MissingField,
            error.BadASTError,
            error.WrongType,
            error.InternalError) as err:
        # - panzer exceptions not caught elsewhere, should have been
        info.log('CRITICAL', 'panzer', err)
        sys.exit(1)
    finally:
        doc.run_scripts('cleanup', do_not_stop=True)
        # - if temp file created in setup, remove it
        if doc.options['panzer']['stdin_temp_file']:
            os.remove(doc.options['panzer']['stdin_temp_file'])
            info.log('DEBUG', 'panzer', 'deleted temp file: %s'
                     % doc.options['panzer']['stdin_temp_file'])
        info.log('DEBUG', 'panzer', '>>>>> panzer quits <<<<<')
    # - successful exit
    sys.exit(0)

if __name__ == '__main__':
    main()
