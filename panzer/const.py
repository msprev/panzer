""" constants for panzer code """
import os

DEBUG_TIMING = False

REQUIRE_PANDOC_ATLEAST = "1.12.1"
USE_OLD_API = False

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
EMPTY_DOCUMENT = {"blocks":[],"pandoc-api-version":[1,17,0,4],"meta":{}}
EMPTY_DOCUMENT_OLDAPI = [{'unMeta': {}}, []]

# writers that give binary outputs
# these cannot be written to stdout
BINARY_WRITERS = ['odt', 'docx', 'epub', 'epub3']

# forbidden options for panzer command line
PANDOC_BAD_OPTS = [
    '--bash-completion',
    '--dump-args',
    '--ignore-args',
    '--list-extensions',
    '--list-highlight-languages',
    '--list-highlight-styles',
    '--list-input-formats',
    '--list-output-formats',
    '--print-default-data-file',
    '--print-default-template',
    '-D'
]

# forbidden options for 'commandline' metadata field
PANDOC_BAD_COMMANDLINE = [
    'bash-completion',
    'dump-args',
    'filter',
    'from',
    'help',
    'ignore-args',
    'metadata',
    'output',
    'list-extensions',
    'list-highlight-languages',
    'list-highlight-styles',
    'list-input-formats',
    'list-output-formats',
    'print-default-data-file',
    'print-default-template',
    'read',
    'template',
    'to',
    'variable',
    'version',
    'write'
]

# additive command line options
PANDOC_OPT_ADDITIVE = ['metadata',
                       'variable',
                       'bibliography',
                       'include-in-header',
                       'include-before-body',
                       'include-after-body',
                       'css',
                       'latex-engine-opt']

# pandoc's command line options, divided by reader or writer
PANDOC_OPT_PHASE = {
    # general options
    'data-dir':                'rw',
    # reader options
    'base-header-level':       'r',
    'default-image-extension': 'r',
    'extract-media':           'r',
    'file-scope':              'r',
    'indented-code-classes':   'r',
    'metadata':                'r',
    'normalize':               'r',
    'old-dashes':              'r',
    'parse-raw':               'r',
    'preserve-tabs':           'r',
    'smart':                   'r',
    'tab-stop':                'r',
    'track-changes':           'r',
    # writer options
    'ascii':                   'w',
    'atx-headers':             'w',
    'biblatex':                'w',
    'bibliography':            'w',
    'chapters':                'w',
    'citation-abbreviations':  'w',
    'columns':                 'w',
    'csl':                     'w',
    'css':                     'w',
    'dpi':                     'w',
    'email-obfuscation':       'w',
    'epub-chapter-level':      'w',
    'epub-cover-image':        'w',
    'epub-embed-font':         'w',
    'epub-metadata':           'w',
    'epub-stylesheet':         'w',
    'gladtex':                 'w',
    'highlight-style':         'w',
    'html-q-tags':             'w',
    'id-prefix':               'w',
    'include-after-body':      'w',
    'include-before-body':     'w',
    'include-in-header':       'w',
    'incremental':             'w',
    'jsmath':                  'w',
    'katex':                   'w',
    'katex-stylesheet':        'w',
    'latex-engine':            'w',
    'latex-engine-opt':        'w',
    'latexmathml':             'w',
    'listings':                'w',
    'mathjax':                 'w',
    'mathml':                  'w',
    'mimetex':                 'w',
    'natbib':                  'w',
    'no-highlight':            'w',
    'no-tex-ligatures':        'w',
    'no-wrap':                 'w',
    'number-offset':           'w',
    'number-sections':         'w',
    'reference-docx':          'w',
    'reference-links':         'w',
    'reference-location':      'w',
    'reference-odt':           'w',
    'section-divs':            'w',
    'self-contained':          'w',
    'slide-level':             'w',
    'standalone':              'w',
    'table-of-contents':       'w',
    'title-prefix':            'w',
    'toc-depth':               'w',
    'top-level-division':      'w',
    'variable':                'w',
    'verbose':                 'w',
    'webtex':                  'w',
    'wrap':                    'w'
}

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
    ".adoc"     : "asciidoc",
    ".pdf"      : "latex",
    ".fb2"      : "fb2",
    ".opml"     : "opml",
    ".icml"     : "icml",
    ".tei.xml"  : "tei",
    ".tei"      : "tei",
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
