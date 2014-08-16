import os

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

