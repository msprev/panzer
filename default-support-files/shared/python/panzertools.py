# this should be run with Python 3
import json
import os
import sys

ENCODING = 'utf8'

class FileInfo(object):

    def __init__(self, fullpath):
        self.i_fullpath = fullpath
        self.i_parents = os.path.split(fullpath)[0]
        if not self.i_parents:
            self.i_parents = '.'
        self.i_filename = os.path.split(fullpath)[1]
        self.i_basename = os.path.splitext(self.i_filename)[0]
        self.i_extension = os.path.splitext(self.i_filename)[1]

    def mangle(self):
        """Creates names for temporary files

        Args:
            basename: A string with the name (without extension) to be mangled

        Returns:
            A string (input of 'this basefile name' returns '_this-basefile-name_')
        """
        old_basename = self.i_basename
        mangled_basename = '_' + old_basename.replace(' ','-') + '_'
        mangled_filename = mangled_basename + self.i_extension
        mangled_fullpath = os.path.join(self.i_parents, mangled_filename)
        return FileInfo(mangled_fullpath)

    def fullpath(self):
        return self.i_fullpath

    def parents(self):
        return self.i_parents

    def filename(self):
        return self.i_filename

    def basename(self):
        return self.i_basename

    def extension(self):
        return self.i_extension

    def set_fullpath(self, fullpath):
        self.i_fullpath = fullpath
        self.i_parents = os.path.split(fullpath)[0]
        self.i_filename = os.path.split(fullpath)[1]
        self.i_basename = os.path.splitext(self.i_filename)[0]
        self.i_extension = os.path.splitext(self.i_filename)[1]

    def set_parents(self, parents):
        self.i_parents = parents
        self.i_fullpath = os.path.join(self.i_parents, self.i_filename)

    def set_filename(self, filename):
        self.i_filename = filename
        self.i_basename = os.path.splitext(self.i_filename)[0]
        self.i_extension = os.path.splitext(self.i_filename)[1]
        self.i_fullpath = os.path.join(self.i_parents, self.i_filename)

    def set_basename(self, basename):
        self.i_basename = basename
        self.i_filename = self.i_basename + self.i_extension
        self.i_fullpath = os.path.join(self.i_parents, self.i_filename)

    def set_extension(self, extension):
        self.i_extension = extension
        self.i_filename = self.i_basename + self.i_extension
        self.i_fullpath = os.path.join(self.i_parents, self.i_filename)


def log(level, message):
    """docstring for log"""
    outgoing = [ { 'error_msg': { 'level': level, 'message': message } } ]
    outgoing_json = json.dumps(outgoing) + '\n'
    outgoing_bytes = outgoing_json.encode(ENCODING)
    sys.stderr.buffer.write(outgoing_bytes)
    sys.stderr.flush()


def read_options():
    stdin_bytes = sys.stdin.buffer.read()
    stdin = stdin_bytes.decode(ENCODING)
    message_in = json.loads(stdin)
    options = message_in[0]['cli_options']
    return options
