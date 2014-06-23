Introduction
============

`pandoc <http://johnmacfarlane.net/pandoc/index.html>`__ is a powerful
and flexible document processing tool. pandoc presents a huge range of
options for customisation of document output. Millions of dials can be
twiddled, and it is not easy to know which combinations to choose to
quickly achieve your desired result. Often you want to produce output
with a defined look, and this may involve the coordination of many
elements, scripts and filters.

`panzer <https://github.com/msprev>`__ can help. panzer adds *styles* to
pandoc. Styles are metadata fields that govern the look and feel of your
document in a convenient and reusable way. Styles are combinations of
templates, metadata settings, filters, post-processors, and pre- and
post-flight scripts. panzer remembers the options for a style so that
you don't have to. Styles are written and selected using YAML metadata.
Styles can be customised on a per document and per writer basis.

Instead of running ``pandoc``, you run ``panzer`` on your document.
panzer will run pandoc plus any associated scripts, and it will pass on
information based on your style. To select a style in your document, add
the field ``style`` to its metadata. By convention, styles take
capitalized values. For example:

::

    style: Notes

This would select the ``Notes`` style. This style should be defined in
panzer's ``defaults.md`` file or inside your document itself using the
YAML syntax below.

panzer can be used as a lightweight alternative to makefiles, or in
conjunction with makefiles.

Installation
============

*Requirements:*

-  `pandoc <http://johnmacfarlane.net/pandoc/index.html>`__
-  `Python 3 <https://www.python.org/download/releases/3.0>`__

Why is Python 3 required? Python 3 provides sane unicode handling.

*Installation:*

Command line use
================

``panzer`` takes the same command line arguments and options as
``pandoc``. panzer passes these arguments and options to the underlying
instance of pandoc. ``panzer`` can be used as a drop-in replacement for
the ``pandoc`` command.

panzer also has a few of its own command line options. These
panzer-specific options are prefixed by triple dashes (``---``). Run the
command ``panzer -h`` to see a list of these options.

Like pandoc, panzer expects all I/O to be encoded in utf-8. This applies
to interaction between panzer and processes that it spawns (scripts,
etc.).

Styles
======

A style consists of the following elements, which can be set on a per
writer basis:

1. Default metadata fields
2. Template
3. Pre-flight scripts
4. Filters
5. Postprocessors
6. Post-flight scripts
7. Cleanup scripts

A style definition is a metadata block:

::

    Style:
        writer:
            ...

Style definitions are structured by *style name* and *writer*. Both are
fields are of type ``MetaMap``. Style names by convention are
capitalized (``Notes``). Writer names are the same as corresponding
pandoc writers (e.g. ``latex``, ``html``, ``docx``, etc.) There is a
special style name, ``All``, whose settings applies to all styles. The
``All`` style applies also to documents that omit a ``style`` field.
There is special writer, ``all``, whose settings apply to all writers of
the style.

Under a writer field, the following metadata fields may appear:

+-------------------+------------------------------------------------------------------+-------------------+
| field             | value                                                            | value type        |
+===================+==================================================================+===================+
| ``metadata``      | default metadata fields                                          | ``MetaMap``       |
+-------------------+------------------------------------------------------------------+-------------------+
| ``template``      | pandoc template                                                  | ``MetaInlines``   |
+-------------------+------------------------------------------------------------------+-------------------+
| ``preflight``     | list of executables to run/kill before input doc is processed    | ``MetaList``      |
+-------------------+------------------------------------------------------------------+-------------------+
| ``filter``        | list of pandoc json filters to run/kill                          | ``MetaList``      |
+-------------------+------------------------------------------------------------------+-------------------+
| ``postprocess``   | list of executables to run/kill to postprocess pandoc's output   | ``MetaList``      |
+-------------------+------------------------------------------------------------------+-------------------+
| ``postflight``    | list of executables to run/kill after output file written        | ``MetaList``      |
+-------------------+------------------------------------------------------------------+-------------------+
| ``cleanup``       | list of executables to run/kill on exit irrespective of errors   | ``MetaList``      |
+-------------------+------------------------------------------------------------------+-------------------+

**Default metadata** can be set by the style. Any metadata field that
can appear in a pandoc document can be defined as default metadata. This
includes standard pandoc metadata fields, e.g. ``numbersections``,
``toc``. However, panzer comes into its own when one defines new default
metadata fields for a style. New default fields allow the style's
templates to employ new variables, the values of which can be overriden
by the user on a per document basis.

**Templates** are pandoc
`templates <http://johnmacfarlane.net/pandoc/demo/example9/templates.html>`__.
Templates typically are more useful in panzer than in vanilla pandoc
because templates can safely employ new variables defined in the style's
default metadata. For example, if a style defines ``copyright_notice``
in default metadata, then the style's templates can safely use
``$copyright_notice$``.

**Preflight scripts** are executables that are run before any other
scripts or filters. Preflight scripts are run after panzer reads the
source documents, but before panzer runs pandoc to convert this data to
the output format. Note that this means that if preflight scripts modify
the input document files this will not be reflected in panzer's output.

**Filters** are pandoc `json
filters <http://johnmacfarlane.net/pandoc/scripting.html>`__. Filters
gain two news powers from panzer. First, filters can be passed `more
than one <#cli_options_executables>`__ command line argument. The first
command line argument is still reserved for the writer's name to
maintain backwards compatibility with pandoc's filters. Second, panzer
injects a special metadata field, ``panzer_reserved``, into the document
which filters see. This field contains a json string that exposes
`useful information <#passing_messages_exes>`__ to filters, including
information about all command line arguments with which panzer was
invoked. See section below on `compatibility <#pandoc_compatibility>`__
with pandoc.

**Postprocessors** are text-processing pipes that take pandoc's output
document, do some further text processing, and give an output. Standard
unix executables (``sed``, ``tr``, etc.) may be used as postprocessors
with arbitrary arguments. Or you can write your own. Postprocessors
operate on text-based output from pandoc. Postprocessors are not run if
the ``pdf`` writer is selected.

**Postflight scripts** are executables that are run after the output
file has been written. If output is stdout, postflight scripts are run
after output to stdout has been flushed. Postflight scripts are not run
if a fatal error occurs earlier in the processing chain.

**Cleanup scripts** are executables that are run before panzer exits.
Cleanup scripts run irrespective of whether an error has occurred
earlier. Cleanup scripts are run after postflight scripts.

Style definition locations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Styles can be defined either in:

1. The ``defaults.md`` file in panzer's support directory (normally,
   ``~/.panzer/``)
2. The metadata of the input document(s).

Run lists
~~~~~~~~~

Executables (scripts, filters, postprocessors) are specified using a
*run list*. The run list is populated by the metadata list for the
relevant executables (``preflight``, ``cleanup``, ``filter``,
``postprocess``). These metadata lists consist of items that are parsed
as commands to add or remove executables from the relevant run list. If
an item contains a ``run`` field, then an executable whose name is the
value of that field is added to the run list (``run: ...``). Executables
will be run in the order that they are listed: from first to last. If an
item contains a ``kill`` field, then an executable whose name is the
value of that field is removed from the run list if present
(``kill: ...``). Killing does not prevent a later item from adding the
executable again. The run list is emptied by adding an item
``killall: true``. Arguments can be passed to executables by listing
them as the value of the ``args`` field of an item that has a ``run``
field.

+---------------+-----------------------------------------+-------------------+
| field         | value                                   | value type        |
+===============+=========================================+===================+
| ``run``       | add to run list                         | ``MetaInlines``   |
+---------------+-----------------------------------------+-------------------+
| ``kill``      | remove from run list                    | ``MetaInlines``   |
+---------------+-----------------------------------------+-------------------+
| ``killall``   | if true, empty run list at this point   | ``MetaBool``      |
+---------------+-----------------------------------------+-------------------+

::

        [preflight|filter|postprocess|postflight|cleanup]:
            - run: ...
              args: ...
            - kill: ...
            - killall: [true|false] 

Passing command line arguments to executables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``args`` field allows one to specify command line arguments in two
ways. If ``args`` is a string, then that string is used as the command
line arguments to the external process. If ``args`` is a list, then the
items in that list are used to construct the command line arguments.
Boolean values set double-dashed flags of the same name, and other
values set double-dashed key--value command line arguments of the same
name as the field. The command line arguments are constructed from first
to last.

+------------+----------------------------------------------+-------------------+
| field      | value                                        | value type        |
+============+==============================================+===================+
| ``args``   | verbatim command line arguments              | ``MetaInlines``   |
+------------+----------------------------------------------+-------------------+
| ``args``   | list of key--value pairs:                    | ``MetaList``      |
+------------+----------------------------------------------+-------------------+
|            | ``flag: true`` argument is ``--flag``        | ``MetaBool``      |
+------------+----------------------------------------------+-------------------+
|            | ``key: value`` argument is ``--key=value``   | ``MetaInlines``   |
+------------+----------------------------------------------+-------------------+

The following are equivalent:

::

    - run: ...
      args: --verbose --bibliography="mybib.bib"

::

    - run: ...
      args:
          - verbose: true
          - bibliography: mybib.bib

Either style for the ``args`` field may be used in the same file.

Example style
-------------

Here is a definition for the ``Notes`` style:

::

    Notes:
        all:                 
            metadata:
                numbersections: false
        latex:
            metadata:
                numbersections: true
                fontsize: 12pt
            preflight:
                - run: tmp_out.py
                  args:
                    - directory: mytmp
                    - create: true
            filter:
                 - run: optimise_bib.py
            postprocess:
                 - run: smallcaps.py
                   args: --verbose --skip-names
            postflight:
                - run: latexmk.py
                - run: open_pdf.py
            cleanup:
                - run: tmp_back.py

If panzer is run on the following document:

::

    ---
    title: "My document"
    author: Mark Sprevak
    style: Notes
    ...

panzer would run pandoc with the following document:

::

    ---
    title: "My document"
    author: Mark Sprevak
    style: Notes
    numbersections: true
    fontsize: 12pt
    preflight:
        - run: tmp_out.py
    filter:
        - run: smallcaps.py
        - run: optimise_bib.py
    postprocess:
        - run: smallcaps.py
    postflight:
        - run: latexmk.py
        - run: pplatex.py
        - run: open_pdf.py
    cleanup:
        - run: tmp_back.py
        - run: rmlatex.py
    ...

Applying styles to documents
----------------------------

Individual items in styles are combined with a union biased to the most
specific named settings. Items in the global scope take highest
precedence (say, you place ``template: new_one`` in your document's
metadata, this would override any setting by the style). Items in the
style definitions that appear inside the document take precedence over
items that appear in the style definitions in ``defaults.md`` Items in
the currently selected style take precedence over items in ``All`` and
``all``. This allows for a flexible and commonsensical way for style
fields to be overrided.

Items in styles are combined with a union biased to the highest ranked
items below:

1. Metadata fields in document
2. Style definitions in document:

   a. Current style, current writer
   b. Current style, ``all`` writer
   c. ``All`` style, current writer
   d. ``All`` style, ``all`` writer

3. Style definitions in ``defaults.md``:

   a. Current style, current writer
   b. Current style, ``all`` writer
   c. ``All`` style, current writer
   d. ``All`` style, ``all`` writer

Non-additive fields
~~~~~~~~~~~~~~~~~~~

If two fields take different values (say, two different settings for
``numbersections``), then the item with the highest precedence wins.

Additive fields
~~~~~~~~~~~~~~~

Exceptions are lists of filters, post-processors, and scripts. These are
additive fields and the union is non-destructive. Items lower in
precedence are appended to the list after higher precedence items. To
remove a filter or script from the list, add it as the value of a
``kill`` field:

::

    filter:
        - kill: smallcap.py

``kill`` removes a filter/script if it is already present.
``- killall: true`` empties the entire list and starts from scratch.
Note that ``kill`` or ``killall`` only affect items of lower precedence.
They do not prevent a filter or script being added afterwards. A killed
filter will be enabled again if a higher-precedence item invokes it
again with ``run``. If you want to be sure to kill a filter, place the
relevant ``kill`` as the last item in the list in your document's
metadata.

Any text outside the metadata block in ``defaults.md`` is ignored.

Command line options
~~~~~~~~~~~~~~~~~~~~

Command line options override settings in the metadata, and they cannot
be disable by a metadata setting.

Filters specified on the command line (as a value of ``--filter``) are
always run first: they will be treated as appearing at the start of the
list. Filters specified on the command line cannot be killed by a
``kill`` or ``killall`` command.

Templates specified on the command line (as a value of ``--template``)
will override any template selected in the metadata.

Input files
~~~~~~~~~~~

If multiple input files are given to panzer on the command line,
panzer's uses pandoc to join those files into a single document.
Metadata fields (including style definitions and items in global scope)
are merged using pandoc's rules (left-biased union). Note that this
means that if fields in multiple files have fields with the same name
(e.g. ``filter``) they will clobber each other, rather than follow the
rules on additive union above.

If panzer is passed input via stdin, it stores this in a temporary file
in the current working directory. This is necessary because scripts may
wish to inspect and modify this data. See section on `passing messages
to scripts <#passing_messages>`__ to see how they can access this
information. The temporary file is always removed when panzer exits,
irrespective of whether any errors have occurred.

Writing your own style
======================

Styles can be defined in your document's metadata or in panzer's
``defaults.md`` file.

panzer support directory
------------------------

panzer's style definition file ``defaults.md`` lives in panzer's support
directory (default: ``~/.panzer``).

::

    .panzer/
        defaults.md
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        template/

``defaults.md`` is the file that contains all default style definitions.
Templates, scripts and filters live in their own subdirectories with
corresponding names.

A recommended structure for each executable's directory:

::

    postflight/
        latexmk/
            latexmk.py

Finding scripts and filters
---------------------------

When panzer is looking for an executable, say a filter with name
``foo``, it will search in the following places in the order from first
to last (the current working directory is ``.``; panzer's support
directory is ``~/.panzer``):

1. ``./foo``
2. ``./panzer/filter/foo``
3. ``./panzer/filter/foo/foo``
4. ``~/.panzer/filter/foo``
5. ``~/.panzer/filter/foo/foo``
6. ``foo`` in system's path as exported via shell

The same rules apply for templates.

Passing messages to executables
-------------------------------

+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| subprocess      | arguments               | stdin                     | stdout                    | stderr           |
+=================+=========================+===========================+===========================+==================+
| preflight       | set by ``args`` field   | json string               | to screen                 | error messages   |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| postflight      | "                       | "                         | "                         | "                |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| postflight      | "                       | "                         | "                         | "                |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| cleanup         | "                       | "                         | "                         | "                |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| postprocessor   | "                       | output text               | output text               | "                |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+
| filter          | 1st arg is writer       | json string of document   | json string of document   | "                |
+-----------------+-------------------------+---------------------------+---------------------------+------------------+

Passing messages to scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Scripts need to know about the command line options passed to panzer. A
script, for example, may need to know what files are being used as input
to panzer, which file is the target output, and options being used for
the document processing (e.g. the writer). Scripts are passed this
information via stdin by a utf8-encoded json message. The json message
received on stdin by scripts is as follows:

::

    [ { 'cli_options': OPTIONS } ]

``OPTIONS`` is a json dictionary with the relevant information. It is
divided into two dictionaries that concern ``panzer`` and ``pandoc``
respectively.

::

    OPTIONS = {
        'panzer': {
            'support'         : DEFAULT_SUPPORT_DIR,   # panzer support directory
            'debug'           : False,                 # panzer ---debug option
            'verbose'         : 2,                     # panzer ---verbose option
            'html'            : False,                 # panzer ---html option
            'stdin_temp_file' : ''                     # name of temporary file used to store stdin input
        },
        'pandoc': {
            'input'      : [],                         # list of input files
            'output'     : '-',                        # name of output file ('-' means stdout)
            'pdf_output' : False,                      # pandoc to write pdf directly
            'read'       : '',                         # name of pandoc reader
            'write'      : '',                         # name of pandoc writer
            'template'   : '',                         # name of template set on command line
            'filter'     : [],                         # list of filters set on command line
            'options'    : []                          # list of remaining pandoc command line options
        }
    }

The ``filter`` and ``template`` fields above specify filters and
templates set on the command line (via the command line ``--filter`` and
``--template`` options) These fields do *not* contain any filters or the
template specified in the metadata or style.

Passing messages to filters
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The method above will not work for filters, since they receive the
document as an AST via stdin. Nevertheless, it is conceivable that a
filter may need to access information about panzer's command line
options (for example, if it is going to create a temporary file to used
by a later script). Filters can access the same information as scripts
via a special metadata field that panzer injects into the document,
``panzer_reserved``. The value of ``panzer_reserved`` is a json string
identical to that received by the scripts via stdin.

::

    panzer_reserved: |
        ```
        JSON_MESSAGE
        ```

Filters can retrieve the json message by extracting the following item
from the document's AST:

::

    "panzer_reserved": {
      "t": "MetaBlocks",
      "c": [
        {
          "t": "CodeBlock",
          "c": [
            ["",[],[]],
            "JSON_MESSAGE"
          ]
        }
      ]
    }

Why not encode every item of ``OPTIONS`` individually as a pandoc
metadata field? This would be more work for both panzer and the filters.
It is quicker and simpler to retrieve/encode the value of just one field
and run a json (de)serialisation operation. The point of pandoc metadata
fields is to be easily human readable and editable. This concern does
not apply if a field is never seen by the user and used only for
inter-process communication.

Passing messages to postprocessors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is currently no mechanism for passing a similar json message to
postprocessors.

Error messages
--------------

panzer captures stderr output from all scripts and filters and it
attempts to parse. Scripts/filters that are aware of panzer should send
correctly formatted info and error messages to stderr for pretty
printing according to panzer's preferences. If a message is sent to
stderr that is not correctly formatted, panzer will forward it print it
verbatim prefixed by a '!'. This means that panzer can be used with
generic (non-panzer-aware) scripts and filters. However, if you
frequently use a non-panzer-aware script/filter, you may wish to
consider writing a thin wrapper that will provide pretty panzer-style
error messages.

The message format for stderr that panzer expects is a newline-separated
sequence of utf-8 encoded json strings, each with the following
structure:

::

    [ { 'error_msg': { 'level': LEVEL, 'message': MESSAGE } } ]

``LEVEL`` is a string that sets the error level; it can take one of the
following values:

::

    'CRITICAL'
    'ERROR'   
    'WARNING' 
    'INFO'    
    'DEBUG'   
    'NOTSET'  

``MESSAGE`` is your error message.

The Python module ``panzertools`` provides a ``log`` function to
scripts/filters to send error messages to panzer using this format.

Reserved metadata fields
========================

The following metadata fields are reserved for use by panzer and should
be avoided. Using these fields in ways other than described above in
your document will result in unpredictable results.

-  ``panzer_reserved``
-  ``All``
-  ``style``
-  Field with name same as the value of ``style`` field. Style names
   should be capitalized (``Notes``) to prevent name collision with
   other fields of the same name (``notes``).

Compatibility with pandoc
=========================

panzer works will all pandoc filters. Note that not all filters that
work with panzer will work with pandoc's vanilla ``--filter`` option.

panzer extends pandoc's existing use of filters by:

1. Allowing filters to take more than one command line argument (first
   argument still reserved for the writer).
2. Injecting a special ``panzer_reserved`` metadata field into document
   that allows filters to see ``OPTIONS`` data. This is useful if, say,
   filters are to write auxiliary files that will be picked up by
   subsequent processing.

Known issues
============

-  Calls to subprocesses (scripts, filters, etc.) are blocking
-  Run lists are not passed to executables.
-  panzer is not the fastest; a Haskell version is in the works and it
   should be much faster.

