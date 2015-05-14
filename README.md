panzer
======

panzer adds 'styles' to [pandoc](http://johnmacfarlane.net/pandoc/index.html). Styles change the look of a document in a reusable way. Styles are combinations of templates, metadata settings, filters, postprocessors, preflight and postflight scripts. These can be set on a per document or per writer basis. Styles bear inheritance relations to each other.

To use a style, add a field with your style name to the yaml metadata block of your document:

``` yaml
style: Notes
```

Multiple styles can be supplied as a list:

``` yaml
style: 
    - Notes
    - BoldHeadings
```

Styles are defined in a `style.yaml` file ([example](https://github.com/msprev/dot-panzer/blob/master/styles.yaml)). The style definition file, plus associated executables, are placed in the `.panzer` directory in the user's home folder ([example](https://github.com/msprev/dot-panzer)).

Styles can also be defined locally inside the document:

``` yaml
styledef:
    Notes:
        all:
            metadata:
                numbersections: false
        latex:
            metadata:
                numbersections: true
                fontsize: 12pt
            postflight:
                - run: latexmk.py
```

Style settings can be overridden inside a document by adding the appropriate field outside a style definition:

``` yaml
postflight:
    - run: open_pdf.py
```

Installation
============

        git clone https://github.com/msprev/panzer
        cd panzer
        python3 setup.py develop

*Requirements:*

-   [pandoc](http://johnmacfarlane.net/pandoc/index.html)
-   [Python 3](https://www.python.org/downloads/)

Use
===

Run `panzer` on your document as you would have done `pandoc`. If the document lacks a `style` field, this is equivalent to running `pandoc`. If the document has a `style` field, panzer will invoke pandoc plus any associated scripts, filters, and set the appropriate metadata fields.

`panzer` accepts the same command line options as `pandoc`. These options are passed to the underlying instance of pandoc.

panzer has additional command line options. These are prefixed by triple dashes (`---`). Run the command `panzer -h` to see them:

      -h, --help, ---help, ---h
                            show this help message and exit
      ---version            show program's version number and exit
      ---silent             only print errors and warnings
      ---panzer-support PANZER_SUPPORT
                            directory of support files
      ---debug DEBUG        filename to write .log and .json debug files

Panzer expects all input and output to be utf-8.

Style definition
================

A style definition may consist of:

| field         | value                              | value type                  |
|:--------------|:-----------------------------------|:----------------------------|
| `parent`      | parent(s) of style                 | `MetaList` or `MetaInlines` |
| `metadata`    | default metadata fields            | `MetaMap`                   |
| `template`    | pandoc template                    | `MetaInlines`               |
| `preflight`   | run before input doc is processed  | `MetaList`                  |
| `filter`      | pandoc filters                     | `MetaList`                  |
| `postprocess` | run on pandoc's output             | `MetaList`                  |
| `postflight`  | run after output file written      | `MetaList`                  |
| `cleanup`     | run on exit irrespective of errors | `MetaList`                  |

Style definitions are hierarchically structured by *name* and *writer*. Style names by convention should be MixedCase (`MyNotes`). Writer names are the same as those of the relevant pandoc writer (e.g. `latex`, `html`, `docx`, etc.) A special writer, `all`, matches every writer.

`parent` takes a list or single style. Children inherit the properties of their parents. Children may have multiple parents.

`metadata` contains default metadata set by the style. Any metadata field that can appear in a pandoc document can appear here.

`template` specifies a pandoc [template](http://johnmacfarlane.net/pandoc/demo/example9/templates.html) for the document.

`preflight` specifies executables run before the document is processed. Preflight scripts are run after panzer reads the input documents, but before pandoc is run to convert to the output.

`filter` specifies pandoc [json filters](http://johnmacfarlane.net/pandoc/scripting.html). Filters gain two new properties from panzer. For more info, see section below on [compatibility](#pandoc_compatibility) with pandoc.

`postprocessor` specifies executable to pipe pandoc's output through. Standard unix executables (`sed`, `tr`, etc.) are examples of possible use. Postprocessors are skipped if a binary writer (e.g. `.docx`) is selected.

`postflight` specifies executables run after the output file has been written. If output is stdout, postflight scripts are run after output has been flushed.

`cleanup` specifies executables that are run before panzer exits and after postflight scripts. Cleanup scripts run irrespective of whether a fatal error has occurred earlier.

Example:

``` yaml
Notes:
    all:
        metadata:
            numbersections: false
    latex:
        metadata:
            numbersections: true
            fontsize: 12pt
        postflight:
            - run: latexmk.py
```

If panzer were run on the following document with the latex writer selected,

``` yaml
---
title: "My document"
author: John Smith
style: Notes
...
```

it would run pandoc on the following input, and then execute `latexmk.py`.

``` yaml
---
title: "My document"
author: John Smith
numbersections: true
fontsize: 12pt
...
```

Styles are defined:

-   'Globally' in the `styles.yaml` file (normally in `~/.panzer/`)
-   'Locally' in a `styledef` field inside the document

Overriding among styles:

| \#  | rule for overriding                                                               |
|:----|:----------------------------------------------------------------------------------|
| 1   | Fields set outside a style definition override a style's setting                  |
| 2   | Local definitions inside a `styledef` override global definitions in `style.yaml` |
| 3   | Later styles in list override earlier ones                                        |
| 4   | Children override their parents                                                   |
| 5   | Writer-specific settings override settings for `all`                              |

For fields that pertain to scripts/filters, overriding is *additive*; for other fields, it is *non-additive*:

-   For `metadata` and `template` fields, if one style setting overrides another (say, a parent and child set `numbersections` to different values), then inheritance is non-additive, and only one (the child) wins.

-   For lists `preflight`, `filter`, `postflight` and `cleanup` if one style setting overrides another, then the 'winner' adds its items after the 'loser'. For example, if the parent adds `latexmk.py` as a postflight script, and the child adds `printlog.py` as a postflight script, then both are run and `printlog.py` is run after `latexmk.py`

-   To remove an item from an additive list, set it as the value a `kill` field, instead of a `run` field.

Command line options trump any style settings, and cannot be overridden by a metadata setting. Filters specified on the command line (via `--filter`) are always run first, and cannot be removed by `kill`.

Multiple input files are joined according to pandoc's rules. Metadata are merged using left-biased union. This means overriding behaviour when merging multiple input files is always non-additive.

panzer buffers stdin input, if present, to a temporary file in the current working directory. This allows preflight scripts to access the data. The temporary file is removed when panzer exits.

Executables (scripts, filters, postprocessors) are specified by a list. The list determines what gets run when. Executables are run from first to last. If an item appears as the value of a `run` field in the list, then it is added to the list of processes to be run (the 'run list'). If an item appears as the value of a `kill` field, then any previous use is removed from the run list. Killing items does not prevent them being added later. A run list can be emptied entirely by adding the special item `- killall: true`.

Arguments can be passed to executables by listing them as the value of the `args` field of that item. The value of the `args` field is passed as the command line argument to the external process. Note that filters always receive the writer name as their first argument.

Example:

``` yaml
- filter:
    - run: setbaseheader.py
      args: "2"
- postflight:
    - kill: open_pdf.py
- cleanup:
    - killall: true
```

The filter `setbaseheader.py` receives the writer name as its first argument and "2" as its second argument.

When panzer is searching for an executable `foo.py`, it will look in:

| \#  | searching in...                                 |
|:----|:------------------------------------------------|
| 1   | `./foo.py`                                      |
| 2   | `./filter/foo.py`                               |
| 3   | `./filter/foo/foo.py`                           |
| 4   | `~/.panzer/filter/foo.py`                       |
| 5   | `~/.panzer/filter/foo/foo.py`                   |
| 6   | `foo.py` in PATH defined by current environment |

The typical structure for the support directory `.panzer` is:

    .panzer/
        styles.yaml
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        template/
        shared/

Within each directory, each executable has its named subdirectory:

    postflight/
        latexmk/
            latexmk.py

Passing messages to external processes
======================================

panzer sends information to external processes via a json message. This message is sent over stdin to scripts (preflight, postflight, cleanup scripts), and embedded in the AST for filters. Postprocessors do not receive a json message (if you need the message, you should probably be using a filter).

    JSON_MESSAGE = [{'metadata':  METADATA,
                     'template':  TEMPLATE,
                     'style':     STYLE,
                     'stylefull': STYLEFULL,
                     'styledef':  STYLEDEF,
                     'runlist':   RUNLIST,
                     'options':   OPTIONS}]

-   `METADATA` is a copy of the metadata branch of the document's AST (useful for scripts, not useful for filters)

-   `TEMPLATE` is a string with full path to the current template

-   `STYLE` is a list of current style(s)

-   `STYLEFULL` is a list of current style(s) including all parents, grandparents, etc.

-   `STYLEDEF` is a copy of the metadata branch with all used style definitions

-   `RUNLIST` is a list with the current state of the run list:

        RUNLIST = [{'kind': 'preflight'|
                            'filter'|
                            'postprocess'|
                            'postflight'|
                            'cleanup',
                    'command':   'my command',
                    'arguments': ['argument1', 'argument2', ...]
                    'status':    'queued'|'running'|'failed'|'done'},
                    ...
                    ...
                ]

-   `OPTIONS` is a dictionary containing panzer's command line options:

        OPTIONS = {
            'panzer': {
                'panzer_support':  const.DEFAULT_SUPPORT_DIR,
                'debug':           str(),
                'silent':          False,
                'stdin_temp_file': str()
            },
            'pandoc': {
                'input':      list(),
                'output':     '-',
                'pdf_output': False,
                'read':       str(),
                'write':      str(),
                'template':   str(),
                'filter':     list(),
                'options':    list()
            }
        }

    `filter` and `template` only include the filters and template, if any, set on the command line (via `--filter` and `--template` command line options).

Scripts read the json message above by deserialising json input on stdin.

Filters can read the json message by extracting a special metadata field, `panzer_reserved`, from the AST:

``` yaml
panzer_reserved:
    json_message: |
        ``` {.json}
        JSON_MESSAGE
        ```
```

which appears to filters as the following structure:

      "panzer_reserved": {
        "t": "MetaMap",
        "c": {
          "json_message": {
            "t": "MetaBlocks",
            "c": [
              {
                "t": "CodeBlock",
                "c": [ [ "", [ "json" ], [] ], "JSON_MESSAGE" ] } ] } } }

Receiving messages from external processes
==========================================

panzer captures stderr output from all executables. This is for pretty printing of error messages. Scripts and filters should send json messages to panzer via stderr. If a message is sent to stderr that is not correctly formatted, panzer will print it verbatim prefixed by a '!'.

The json message that panzer expects is a newline-separated sequence of utf-8 encoded json dictionaries, each with the following structure:

    { 'level': LEVEL, 'message': MESSAGE }

-   `LEVEL` is a string that sets the error level; it can take one of the following values:

        'CRITICAL'
        'ERROR'
        'WARNING'
        'INFO'
        'DEBUG'
        'NOTSET'

-   `MESSAGE` is a string with your message

Compatibility
=============

panzer accepts pandoc filters. panzer allows filters to behave in two new ways:

1.  Filters can take more than one command line argument (first argument still reserved for the writer).
2.  A `panzer_reserved` field is added to the AST metadata branch with goodies for filters to mine.

Reserved fields
===============

The following metadata fields are reserved by panzer.

-   `styledef`
-   `style`
-   `template`
-   `preflight`
-   `filter`
-   `postflight`
-   `postprocess`
-   `cleanup`
-   `panzer_reserved`

The pandoc writer name `all` is also occupied.

Known issues
============

Pull requests welcome:

-   Slow (calls to subprocess slow in Python)
-   Calls to subprocesses (scripts, filters, etc.) are blocking
-   No Python 2 support
