#!/usr/bin/env python3
"""
return unchanged stdin and print arguments
"""

import json
import sys

ENCODING = 'utf8'

def main():
    """docstring for main"""
    args = sys.argv[1:]
    log('DEBUG', repr(args))
    incoming = sys.stdin.read()
    sys.stdout.write(incoming)
    sys.stdout.flush()
    exit(0)

def log(level, message):
    """docstring for log"""
    # outgoing = [ { 'error_msg': { 'level': level, 'message': message } } ]
    outgoing = {'level': level, 'message': message}
    outgoing_json = json.dumps(outgoing) + '\n'
    outgoing_bytes = outgoing_json.encode(ENCODING)
    sys.stderr.buffer.write(outgoing_bytes)
    sys.stderr.flush()

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
