""" specs of tests to run """

# matrix of tests to run on source files
TEST = {
    'writer' : [
        '',
        'asciidoc',
        'beamer',
        'context',
        'docbook',
        'docx',
        'dokuwiki',
        'dzslides',
        'epub',
        'epub3',
        'fb2',
        'haddock',
        'html',
        'html5',
        'icml',
        'json',
        'latex',
        'man',
        'markdown',
        'markdown_github',
        'markdown_mmd',
        'markdown_phpextra',
        'markdown_strict',
        'mediawiki',
        'native',
        'odt',
        'opendocument',
        'opml',
        'org',
        'plain',
        'revealjs',
        'rst',
        'rtf',
        's5',
        'slideous',
        'slidy',
        'texinfo',
        'textile'],
    'pandoc_options' : [
        '--standalone',
        '--smart'
    ]
}

# blacklist of tests not to run
BLACKLIST = []

# extra tests, in addition to the matrix, to run
EXTRA_TESTS = [
    {'writer': 'latex', 'pandoc_options': '', 'extension': '.pdf'},
    {'writer': 'beamer', 'pandoc_options': '', 'extension': '.pdf'}
]

# file extensions for each writer
DEFAULT_EXTENSION = {
    '':             '.html',
    'beamer':       '.tex',
    'docx':         '.docx',
    'html':         '.html',
    'html5':        '.html',
    'json':         '.json',
    'latex':        '.tex',
    'markdown':     '.md',
    'native':       '.native',
    'odt':          '.odt',
    'opendocument': '.odt',
    'org':          '.org',
    'plain':        '.txt',
    'revealjs':     '.html',
    's5':           '.s5',
    'slideous':     '.html',
    'slidy':        '.html'
}


