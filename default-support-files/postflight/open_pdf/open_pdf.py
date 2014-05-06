#!/usr/bin/env python3

import os
import subprocess
import sys
sys.path.append(os.path.join(os.environ['PANZER_SHARED'], 'python'))
import panzertools


def open_pdf(filepath):
    """Use AppleScript to open View.app"""
    fullpath = os.path.abspath(filepath)
    command = """
    set theFile to POSIX file "%s" as alias
    set thePath to POSIX path of theFile
    tell application "Skim"
      activate
      set theDocs to get documents whose path is thePath
      try
        if (count of theDocs) > 0 then revert theDocs
      end try
      open theFile
    end tell
    """ % fullpath
    asrun(command)


def asrun(ascript):
    "Run the given AppleScript and return the standard output and error."
    osa = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    stdin_bytes = ascript.encode(panzertools.ENCODING)
    stdout_bytes = osa.communicate(stdin_bytes)[0]
    stdout = str()
    if stdout_bytes:
        stdout = stdout_bytes.decode(panzertools.ENCODING)
    return stdout



def main():
    """docstring for main"""
    OPTIONS = panzertools.read_options()
    filepath = OPTIONS['pandoc']['output']
    if filepath == '-':
        return
    target = panzertools.FileInfo(filepath)
    target.set_extension('.pdf')
    pdfpath = target.fullpath()
    if os.path.exists(pdfpath):
        open_pdf(pdfpath)


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
