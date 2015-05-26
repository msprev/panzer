#!/usr/bin/env python3
""" panzer: pandoc with styles

for more info: <https://github.com/msprev/panzer>

Author    : Mark Sprevak <mark.sprevak@ed.ac.uk>
Copyright : Copyright 2014, Mark Sprevak
License   : BSD3
"""

import json
import os
import subprocess
import sys
from . import cli
from . import document
from . import error
from . import info
from . import load
from . import util
from . import version

__version__ = version.VERSION

# Main function

def main():
    """ the main function """
    info.time_stamp('panzer started')
    doc = document.Document()
    try:
        # util.check_pandoc_exists()
        ## don't do this as it takes too long
        info.time_stamp('checked pandoc exists')
        doc.options = cli.parse_cli_options(doc.options)
        info.time_stamp('cli options parsed')
        info.start_logger(doc.options)
        info.time_stamp('logger started')
        util.check_support_directory(doc.options)
        info.time_stamp('support directory checked')

        global_styledef = load.load_styledef(doc.options)
        info.time_stamp('global styledef loaded')
        ast = load.load(doc.options)
        info.time_stamp('document loaded')
        doc.populate(ast, global_styledef)
        doc.transform()
        doc.build_commandline()
        # check if commandline contains any reader options, if so, then re-read document!

        doc.build_runlist()
        doc.purge_style_fields()
        info.time_stamp('document transformed')
        doc.run_scripts('preflight')
        info.time_stamp('preflight scripts done')
        doc.pipe_through('filter')
        info.time_stamp('filters done')
        doc.pandoc()
        info.time_stamp('pandoc done')
        doc.pipe_through('postprocess')
        info.time_stamp('postprocess done')
        doc.write()
        info.time_stamp('output written')
        doc.run_scripts('postflight')
        info.time_stamp('postflight scripts done')
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
        # - write json message to file if ---debug set
        if doc.options['panzer']['debug']:
            filename = doc.options['panzer']['debug'] + '.json'
            content = info.pretty_json_repr(json.loads(doc.json_message()))
            with open(filename, 'w', encoding='utf8') as output_file:
                output_file.write(content)
                output_file.flush()
        info.log('DEBUG', 'panzer', info.pretty_end_log('panzer quits'))

    # - successful exit
    info.time_stamp('finished')
    sys.exit(0)

if __name__ == '__main__':
    main()
