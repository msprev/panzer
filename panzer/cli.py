""" command line options for panzer """
import argparse
import os
import shutil
import sys
import tempfile
from . import const
from . import version

PANZER_DESCRIPTION = '''
Panzer-specific arguments are prefixed by triple dashes ('---').
Other arguments are passed to pandoc.

  panzer default user data directory: "%s"
  pandoc executable: "%s"
''' % (const.DEFAULT_SUPPORT_DIR, shutil.which('pandoc'))

PANZER_EPILOG = '''
Copyright (C) 2015 Mark Sprevak
Web:  http://sites.google.com/site/msprevak
This is free software; see the source for copying conditions. There is no
warranty, not even for merchantability or fitness for a particular purpose.
'''

def parse_cli_options(options):
    """ parse command line options """
    #
    # disable pylint warnings:
    #     + Too many local variables (too-many-locals)
    #     + Too many branches (too-many-branches)
    # pylint: disable=R0912
    # pylint: disable=R0914
    #
    # 1. Parse options specific to panzer
    panzer_known, unknown = panzer_parse()
    # 2. Update options with panzer-specific values
    for field in panzer_known:
        val = panzer_known[field]
        if val:
            options['panzer'][field] = val
    # 3. Parse options specific to pandoc
    pandoc_known, unknown = pandoc_parse(unknown)
    # 2. Update options with pandoc-specific values
    for field in pandoc_known:
        val = pandoc_known[field]
        if val:
            options['pandoc'][field] = val
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
        implicit_writer = const.PANDOC_WRITER_MAPPING.get(ext)
        if implicit_writer is not None:
            options['pandoc']['write'] = implicit_writer
        else:
            # - html is default writer for unrecognised extensions
            options['pandoc']['write'] = 'html'
    # 5. Input from stdin
    # - if one of the inputs is stdin then read from stdin now into
    # - temp file, then replace '-'s in input filelist with reference to file
    if '-' in options['pandoc']['input']:
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
        for index, val in enumerate(options['pandoc']['input']):
            if val == '-':
                options['pandoc']['input'][index] = options['panzer']['stdin_temp_file']
    # 6. Remaining options for pandoc
    opt_known, unknown = pandoc_opt_parse(unknown)
    # - sort them into reader and writer phase options
    for opt in opt_known:
        # undo weird transform that argparse does to match option name
        # https://docs.python.org/dev/library/argparse.html#dest
        opt_name = str(opt).replace('_', '-')
        if opt_name not in const.PANDOC_OPT_TYPE:
            print('ERROR:   do not know reader/writer type of command line option "--%s"' % opt_name)
            continue
        opt_type = const.PANDOC_OPT_TYPE[opt_name]
        if opt_type == 'rw':
            # in both reader and writer phases
            options['pandoc']['options']['r'][opt_name] = opt_known[opt]
            options['pandoc']['options']['w'][opt_name] = opt_known[opt]
        else:
            options['pandoc']['options'][opt_type][opt_name] = opt_known[opt]
    options['pandoc'] = set_quirky_dependencies(options['pandoc'])
    # 7. print error messages for unknown options
    for opt in unknown:
        if opt in const.PANDOC_BAD_OPTS:
            print('ERROR:   pandoc command line option "%s" not supported by panzer' % opt)
        else:
            print('ERROR:   do not recognize command line option "%s"' % opt)
    return options

def panzer_parse():
    """ return list of arguments recognised by panzer + unknowns """
    panzer_parser = argparse.ArgumentParser(
        description=PANZER_DESCRIPTION,
        epilog=PANZER_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False)
    panzer_parser.add_argument("-h", "--help", '---help', '---h',
                               action="help",
                               help="show this help message and exit")
    panzer_parser.add_argument('-v', '--version', '---version', '---v',
                               action='version',
                               version=('%(prog)s ' + version.VERSION))
    panzer_parser.add_argument("---quiet",
                               action='store_true',
                               help='only print errors and warnings')
    panzer_parser.add_argument("---panzer-support",
                               help='.panzer directory')
    panzer_parser.add_argument("---debug",
                               help='filename to write .log and .json debug files')
    panzer_known_raw, unknown = panzer_parser.parse_known_args()
    panzer_known = vars(panzer_known_raw)
    return (panzer_known, unknown)

def pandoc_parse(args):
    """ return list of arguments recognised by pandoc + unknowns """
    pandoc_parser = argparse.ArgumentParser(prog='pandoc')
    pandoc_parser.add_argument('input', nargs='*')
    pandoc_parser.add_argument("--read", "-r", "--from", "-f")
    pandoc_parser.add_argument("--write", "-w", "--to", "-t")
    pandoc_parser.add_argument("--output", "-o")
    pandoc_parser.add_argument("--template")
    pandoc_parser.add_argument("--filter", nargs=1, action='append')
    pandoc_known_raw, unknown = pandoc_parser.parse_known_args(args)
    pandoc_known = vars(pandoc_known_raw)
    return (pandoc_known, unknown)

def pandoc_opt_parse(args):
    """ return list of pandoc command line options """
    opt_parser = argparse.ArgumentParser(prog='pandoc')
    # general options
    opt_parser.add_argument("--data-dir")
    # reader options
    opt_parser.add_argument('--parse-raw', '-R', action='store_true')
    opt_parser.add_argument('--smart', '-S', action='store_true')
    opt_parser.add_argument('--old-dashes', action='store_true')
    opt_parser.add_argument('--base-header-level')
    opt_parser.add_argument('--indented-code-classes')
    opt_parser.add_argument('--default-image-extension')
    opt_parser.add_argument('--metadata', '-M', nargs=1, action='append')
    opt_parser.add_argument('--normalize', action='store_true')
    opt_parser.add_argument('--preserve-tabs', '-p', action='store_true')
    opt_parser.add_argument('--tab-stop')
    opt_parser.add_argument('--track-changes')
    opt_parser.add_argument('--extract-media')
    # writer options
    opt_parser.add_argument('--standalone', '-s', action='store_true')
    opt_parser.add_argument('--variable', '-V', nargs=1, action='append')
    opt_parser.add_argument('--no-wrap', action='store_true')
    opt_parser.add_argument('--columns')
    opt_parser.add_argument('--table-of-contents', '--toc', action='store_true')
    opt_parser.add_argument('--toc-depth')
    opt_parser.add_argument('--no-highlight', action='store_true')
    opt_parser.add_argument('--highlight-style')
    opt_parser.add_argument('--include-in-header', '-H', nargs=1, action='append')
    opt_parser.add_argument('--include-before-body', '-B', nargs=1, action='append')
    opt_parser.add_argument('--include-after-body', '-A', nargs=1, action='append')
    opt_parser.add_argument('--self-contained', action='store_true')
    opt_parser.add_argument('--offline', action='store_true')
    opt_parser.add_argument('--html5', '-5', action='store_true')
    opt_parser.add_argument('--html-q-tags', action='store_true')
    opt_parser.add_argument('--ascii', action='store_true')
    opt_parser.add_argument('--reference-links', action='store_true')
    opt_parser.add_argument('--atx-headers', action='store_true')
    opt_parser.add_argument('--chapters', action='store_true')
    opt_parser.add_argument('--number-sections', '-N', action='store_true')
    opt_parser.add_argument('--number-offset')
    opt_parser.add_argument('--no-tex-ligatures', action='store_true')
    opt_parser.add_argument('--listings', action='store_true')
    opt_parser.add_argument('--incremental', '-i', action='store_true')
    opt_parser.add_argument('--slide-level')
    opt_parser.add_argument('--section-divs', action='store_true')
    opt_parser.add_argument('--email-obfuscation')
    opt_parser.add_argument('--id-prefix')
    opt_parser.add_argument('--title-prefix', '-T')
    opt_parser.add_argument('--css', '-c', nargs=1, action='append')
    opt_parser.add_argument('--reference-odt')
    opt_parser.add_argument('--reference-docx')
    opt_parser.add_argument('--epub-stylesheet')
    opt_parser.add_argument('--epub-cover-image')
    opt_parser.add_argument('--epub-metadata')
    opt_parser.add_argument('--epub-embed-font')
    opt_parser.add_argument('--epub-chapter-level')
    opt_parser.add_argument('--latex-engine')
    opt_parser.add_argument('--latex-engine-opt', '-B', nargs=1, action='append')
    opt_parser.add_argument('--bibliography')
    opt_parser.add_argument('--csl')
    opt_parser.add_argument('--citation-abbreviations')
    opt_parser.add_argument('--natbib', action='store_true')
    opt_parser.add_argument('--biblatex', action='store_true')
    opt_parser.add_argument('--latexmathml', '-m')
    opt_parser.add_argument('--mathml')
    opt_parser.add_argument('--jsmath')
    opt_parser.add_argument('--mathjax')
    opt_parser.add_argument('--gladtex', action='store_true')
    opt_parser.add_argument('--mimetex')
    opt_parser.add_argument('--webtex')
    opt_parser.add_argument('--katex')
    opt_parser.add_argument('--katex-stylesheet')
    opt_known_raw, unknown = opt_parser.parse_known_args(args)
    opt_known = vars(opt_known_raw)
    return (opt_known, unknown)

def set_quirky_dependencies(pandoc):
    """ Set defaults for pandoc options that are dependent in a quirky way,
        and that panzer route via json would disrupt.
        Quirky here means that pandoc would have to know the writer to
        set the reader to the correct defaults or vice versa """
    # --smart: reader setting
    # True when the output format is latex or context, unless --no-tex-ligatures
    # is used.
    if (pandoc['write'] == 'latex' or pandoc['write'] == 'context') \
            and pandoc['options']['w']['no-tex-ligatures'] == False:
        pandoc['options']['r']['smart'] = True
    return pandoc

