#!/usr/bin/env python3

import os
import re
import subprocess
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools


def print_log(filepath):
    """docstring for print_log"""
    target = panzertools.FileInfo(filepath)
    mangled_target = target.mangle()
    mangled_target.set_extension('.log')
    command = [ '/usr/local/bin/pplatex', '--input', mangled_target.fullpath() ]
    panzertools.log('DEBUG', 'running %s' % command)
    stdout_list = list()
    try:
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = p.communicate()
        if stdout_bytes:
            stdout = stdout_bytes.decode(panzertools.ENCODING, errors='ignore')
            for line in stdout.splitlines():
                level = parse_level(line)
                panzertools.log(level, line)
        if stderr_bytes:
            stderr = stderr_bytes.decode(panzertools.ENCODING, errors='ignore')
            for line in stderr.splitlines():
                panzertools.log('ERROR', line)
            panzertools.log('ERROR', 'failed to parse latex log file')
            panzertools.log('INFO', 'consult the log file "%s" for more information' % mangled_target.fullpath())
    except subprocess.CalledProcessError:
        panzertools.log('ERROR', 'pplatex failed')
    for line in stdout_list:
        panzertools.log('INFO', line)


def parse_level(line):
    """docstring for parse_level"""
    level = 'INFO'
    if re.search('^\*\* Warning', line):
        level = 'WARNING'
    elif re.search('^\*\* Error', line):
        level = 'ERROR'
    return level


def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    filepath = OPTIONS['pandoc']['output']
    if filepath != '-' and not OPTIONS['pandoc']['pdf_output']:
        print_log(filepath)
    else:
        panzertools.log('DEBUG', 'pplatex skipped')


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
