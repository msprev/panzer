""" constants for panzer code """
import os

DEBUG_TIMING = False

USE_OLD_API = False
REQUIRE_PANDOC_ATLEAST = "2.0"

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
BINARY_WRITERS = ['odt', 'docx', 'epub', 'epub3', 'pptx']

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
    '--print-highlight-style',
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
    'list-extensions',
    'list-highlight-languages',
    'list-highlight-styles',
    'list-input-formats',
    'list-output-formats',
    'lua-filter',
    'metadata',
    'output',
    'print-default-data-file',
    'print-default-template',
    'print-highlight-style',
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
                       'pdf-engine-opt']

# pandoc's command line options, divided by reader or writer
PANDOC_OPT_PHASE = {
    # general options
    'data-dir':                'rw',
    'log':                     'rw',
    # reader options
    'abbreviations':           'r',
    'base-header-level':       'r',
    'bibliography':            'r',
    'citation-abbreviations':  'r',
    'csl':                     'r',
    'default-image-extension': 'r',
    'extract-media':           'r',
    'file-scope':              'r',
    'indented-code-classes':   'r',
    'metadata':                'r',
    'old-dashes':              'r',
    'preserve-tabs':           'r',
    'strip-empty-paragraphs':  'r',
    'tab-stop':                'r',
    'track-changes':           'r',
    # writer options
    'ascii':                   'w',
    'atx-headers':             'w',
    'biblatex':                'w',
    'chapters':                'w',
    'columns':                 'w',
    'css':                     'w',
    'dpi':                     'w',
    'email-obfuscation':       'w',
    'eol':                     'w',
    'epub-chapter-level':      'w',
    'epub-cover-image':        'w',
    'epub-embed-font':         'w',
    'epub-metadata':           'w',
    'epub-subdirectory':       'w',
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
    'pdf-engine':              'w',
    'pdf-engine-opt':          'w',
    'reference-doc':           'w',
    'reference-links':         'w',
    'reference-location':      'w',
    'request-header':          'w',
    'resource-path':           'w',
    'section-divs':            'w',
    'self-contained':          'w',
    'slide-level':             'w',
    'standalone':              'w',
    'syntax-definition':       'w',
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
    ".fb2"      : "fb2",
    ".opml"     : "opml",
    ".icml"     : "icml",
    ".tei.xml"  : "tei",
    ".tei"      : "tei",
    ".ms"       : "ms",
    ".roff"     : "ms",
    ".pptx"     : "pptx",
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
