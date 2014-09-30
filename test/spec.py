""" specs of tests to run """

# matrix of tests to run on source files
TEST = {
    'writer' : [
        '',
        'asciidoc',
        'beamer',
        'context',
        'docbook',
        # 'docx',
        'dokuwiki',
        'dzslides',
        # 'epub',
        # 'epub3',
        # 'fb2',
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
        # 'odt',
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
    # {'writer': 'latex', 'pandoc_options': '', 'extension': '.pdf'},
    # {'writer': 'beamer', 'pandoc_options': '', 'extension': '.pdf'}
]

# default file extensions for each writer
DEFAULT_EXTENSION = {
    '':                  '.html',
    'asciidoc':          '.txt',
    'beamer':            '.tex',
    'context':           '.tex',
    'docbook':           '.xml',
    'docx':              '.docx',
    'dokuwiki':          '.dokuwiki',
    'dzslides':          '.html',
    'epub':              '.epub',
    'epub3':             '.epub',
    'fb2':               '.fb2',
    'haddock':           '.haddock',
    'html':              '.html',
    'html5':             '.html',
    'icml':              '.icml',
    'json':              '.json',
    'latex':             '.tex',
    'man':               '.1',
    'markdown':          '.md',
    'markdown_github':   '.md',
    'markdown_mmd':      '.md',
    'markdown_phpextra': '.md',
    'markdown_strict':   '.md',
    'mediawiki':         '.wiki',
    'native':            '.native',
    'odt':               '.odt',
    'opendocument':      '.odt',
    'opml':              '.opml',
    'org':               '.org',
    'plain':             '.txt',
    'revealjs':          '.html',
    'rst':               '.rst',
    'rtf':               '.rft',
    's5':                '.s5',
    'slideous':          '.html',
    'slidy':             '.html',
    'texinfo':           '.texinfo',
    'textile':           '.textile'
}


