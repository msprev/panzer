""" constants for panzer code """
import os

DEBUG_TIMING = False

REQUIRE_PANDOC_ATLEAST = "1.12.1"

DEFAULT_SUPPORT_DIR = os.path.join(os.path.expanduser('~'), '.panzer')

ENCODING = 'utf8'

# keys to access type and content of metadata fields
T = 't'
C = 'c'

# list of 'kind' of items on runlist, in order they should run
RUNLIST_KIND = ['preflight', 'filter', 'postprocess', 'postflight', 'cleanup']

# 'status' of items on runlist
QUEUED = 'queued'
RUNNING = 'running'
FAILED = 'failed'
DONE = 'done'

# ast of an empty pandoc document
EMPTY_DOCUMENT = [{'unMeta': {}}, []]

# writers that give binary outputs
# these cannot be written to stdout
BINARY_WRITERS = ['odt', 'docx', 'epub', 'epub3']


# forbidden options for 'commandline' metadata field
PANDOC_BAD_COMMANDLINE = ['write',
                          'read',
                          'from',
                          'to',
                          'filter',
                          'template',
                          'output',
                          'help',
                          'version',
                          'dump-args',
                          'ignore-args']

PANDOC_BAD_OPTS = [['--dump-args'],
                   ['--ignore-args']]

# pandoc's possible command line options
PANDOC_OPTS = {'general': [['--data-dir']],
               'read': [['--parse-raw', '-R'],
                        ['--smart', '-S'],
                        ['--old-dashes'],
                        ['--base-header-level'],
                        ['--indented-code-classes'],
                        ['--default-image-extension'],
                        ['--metadata', '-M'],
                        ['--normalize'],
                        ['--preserve-tabs', '-p'],
                        ['--tab-stop'],
                        ['--track-changes'],
                        ['--extract-media']],
               'write': [['--standalone', '-s'],
                         ['--variable', '-V'],
                         ['--print-default-template', '-D'],
                         ['--print-default-data-file'],
                         ['--no-wrap'],
                         ['--columns'],
                         ['--table-of-contents', '--toc'],
                         ['--toc-depth'],
                         ['--no-highlight'],
                         ['--highlight-style'],
                         ['--include-in-header', '-H'],
                         ['--include-before-body', '-B'],
                         ['--include-after-body', '-A'],
                         ['--self-contained'],
                         ['--offline'],
                         ['--html5', '-5'],
                         ['--html-q-tags'],
                         ['--ascii'],
                         ['--reference-links'],
                         ['--atx-headers'],
                         ['--chapters'],
                         ['--number-sections', '-N'],
                         ['--number-offset'],
                         ['--no-tex-ligatures'],
                         ['--listings'],
                         ['--incremental', '-i'],
                         ['--slide-level'],
                         ['--section-divs'],
                         ['--email-obfuscation'],
                         ['--id-prefix'],
                         ['--title-prefix', '-T'],
                         ['--css', '-c'],
                         ['--reference-odt'],
                         ['--reference-docx'],
                         ['--epub-stylesheet'],
                         ['--epub-cover-image'],
                         ['--epub-metadata'],
                         ['--epub-embed-font'],
                         ['--epub-chapter-level'],
                         ['--latex-engine'],
                         ['--bibliography'],
                         ['--csl'],
                         ['--citation-abbreviations'],
                         ['--natbib'],
                         ['--biblatex'],
                         ['--latexmathml', '-m'],
                         ['--mathml'],
                         ['--jsmath'],
                         ['--mathjax'],
                         ['--gladtex'],
                         ['--mimetex'],
                         ['--webtex'],
                         ['--katex'],
                         ['--katex-stylesheet']]
                         }

# reverse dependencies for pandoc's command line options
# - workaround for a pandoc quirk:
#   - sometimes *reader* options are set conditional on a *writer* being selected
#   - see https://github.com/msprev/panzer/issues/1#issuecomment-105168125
PANDOC_REV_DEPS = [{'writer': ['latex', 'context'], 'reader': '*', 'opt_reader': ['--smart']}]


# Adapted from https://github.com/jgm/pandoc/blob/master/pandoc.hs#L841
PANDOC_WRITER_MAPPING = {
    ""          : "markdown",
    ".tex"      : "latex",
    ".latex"    : "latex",
    ".ltx"      : "latex",
    ".context"  : "context",
    ".ctx"      : "context",
    ".rtf"      : "rtf",
    ".rst"      : "rst",
    ".s5"       : "s5",
    ".native"   : "native",
    ".json"     : "json",
    ".txt"      : "markdown",
    ".text"     : "markdown",
    ".md"       : "markdown",
    ".markdown" : "markdown",
    ".textile"  : "textile",
    ".lhs"      : "markdown+lhs",
    ".texi"     : "texinfo",
    ".texinfo"  : "texinfo",
    ".db"       : "docbook",
    ".odt"      : "odt",
    ".docx"     : "docx",
    ".epub"     : "epub",
    ".org"      : "org",
    ".asciidoc" : "asciidoc",
    ".pdf"      : "latex",
    ".fb2"      : "fb2",
    ".opml"     : "opml",
    ".1"        : "man",
    ".2"        : "man",
    ".3"        : "man",
    ".4"        : "man",
    ".5"        : "man",
    ".6"        : "man",
    ".7"        : "man",
    ".8"        : "man",
    ".9"        : "man"
}

