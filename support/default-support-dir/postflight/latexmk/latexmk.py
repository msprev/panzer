#!/usr/bin/env python3

import filecmp
import os
import subprocess
import shutil
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools

# -f: force processing, don't stop for errors
LATEXMK_OPTS = ['-f', '-silent']

def run_latexmk(filepath):
    """docstring for run_latexmk"""
    target = panzertools.FileInfo(filepath)
    os.chdir(target.parents())
    panzertools.log('INFO', 'changed working directory to "%s"' % os.getcwd())

    target_mangled = target.mangle()
    panzertools.log('DEBUG', 'copying %s to %s' % (target.filename(), target_mangled.filename()))
    shutil.copy(target.filename(), target_mangled.filename())

    command = [ 'latexmk' ]
    command.extend(LATEXMK_OPTS)
    command.extend([ target_mangled.filename() ])
    panzertools.log('DEBUG', 'running command "%s"' % ' '.join(command))

    pdf = panzertools.FileInfo(target.filename())
    pdf.set_extension('.pdf')
    pdf_mangled = pdf.mangle()

    before_pdf_ = -1
    if os.path.exists(pdf_mangled.filename()):
        before_pdf_ = os.path.getmtime(pdf_mangled.filename())

    try:
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_bytes, stderr_bytes = p.communicate()
        if stdout_bytes:
            stdout = stdout_bytes.decode(panzertools.ENCODING, errors='ignore')
            for line in stdout.splitlines():
                panzertools.log('INFO', line)
        if stderr_bytes:
            stderr = stderr_bytes.decode(panzertools.ENCODING, errors='ignore')
            for line in stderr.splitlines():
                panzertools.log('INFO', line)
    except OSError as error:
        panzertools.log('ERROR', error)

    after_pdf_ = -1
    if os.path.exists(pdf_mangled.filename()):
        after_pdf_ = os.path.getmtime(pdf_mangled.filename())

    # no output file exists
    if not os.path.exists(pdf_mangled.filename()):
        panzertools.log('ERROR', 'no output written')
    # output file exists, but is unchanged
    elif before_pdf_ == after_pdf_:
        if os.path.exists(pdf.filename()) and \
           os.path.getsize(pdf.filename()) == os.path.getsize(pdf_mangled.filename()) and \
           filecmp.cmp(pdf.filename(), pdf_mangled.filename(), shallow=False):
            panzertools.log('INFO', 'target already up to date "%s"' % pdf.filename())
        else:
            panzertools.log('ERROR', 'no output written')
    else:
        shutil.copy(pdf_mangled.filename(), pdf.filename())
        panzertools.log('INFO', 'output written to "%s"' % pdf.filename())


def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    filepath = OPTIONS['pandoc']['output']
    if filepath != '-' and not OPTIONS['pandoc']['pdf_output'] and os.path.exists(filepath):
        old_cwd = os.getcwd()
        try:
            run_latexmk(filepath)
        finally:
            os.chdir(old_cwd)
            panzertools.log('INFO', 'restored working directory to "%s"' % old_cwd)
    else:
        panzertools.log('DEBUG', 'latexmk skipped')


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()

