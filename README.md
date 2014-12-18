Warning
=======

This documentation is a work in progress. Much of it is out of date. panzer's code is pretty much complete. Current focus is to:

1.  Write documentation
2.  Create full test suite

------------------------------------------------------------------------

Introduction
============

[pandoc](http://johnmacfarlane.net/pandoc/index.html) is an extremely flexible document processing tool. Yet often you want to produce output with a certain look, and this may involve the coordination of many elements, scripts and filters.

[panzer](https://github.com/msprev) can help. panzer adds *styles* to pandoc. Styles are metadata fields that govern the look and feel of your document in a convenient and reusable way. Styles are combinations of templates, metadata settings, filters, postprocessors, preflight and postflight scripts. Styles are written in YAML and can be cut and pasted into pandoc metadata blocks. Styles can be customised on a per document and per writer basis. You can think of styles as an alternative to bespoke makefiles.

Instead of running `pandoc`, you run `panzer` on your document. panzer will invoke pandoc plus any associated scripts, and it will pass on information based on your style. To select a style in your document, add the field `style` to its metadata.

By convention, styles have MixedCase names. For example:

``` yaml
style: MyNotes
```

If a document lacks a `style` metadata field, running `panzer` is equivalent to running `pandoc`.

Installation
============

*Requirements:*

-   [pandoc](http://johnmacfarlane.net/pandoc/index.html)
-   [Python 3](https://www.python.org/download/releases/3.0)

Why Python 3? It provides sane unicode handling.

*Quick installation:*

    pip3 install panzer

*Source files:*

Alternatively, if you want to hack panzer, the source is freely available: <https://github.com/msprev/panzer>

Command line use
================

`panzer` takes the same command line arguments and options as `pandoc`. panzer passes these arguments and options to a spawned instance of pandoc. `panzer` can be used as a drop-in replacement for the `pandoc` command.

panzer also has a few of its own command line options. These panzer-specific options are prefixed by triple dashes (`---`). Run the command `panzer -h` to see a list of these options:

      -h, --help, ---help, ---h
                            show this help message and exit
      ---version            show program's version number and exit
      ---verbose VERBOSE    verbosity of warnings
                             0: silent
                             1: only errors and warnings
                             2: full info (default)
      ---panzer-support PANZER_SUPPORT
                            directory of support files
      ---debug DEBUG        filename to write .log and .json debug files

Like pandoc, panzer expects input and output to be encoded in utf-8. This also applies to interaction between panzer and executables that it spawns (scripts, etc.).

Styles
======

A style definition consists of the following elements, all of which are optional but at least one of which must be present. All but the first of which can be set on a per writer basis:

1.  Parent style(s)
2.  Default metadata
3.  Template
4.  Pre-flight scripts
5.  Filters
6.  Postprocessors
7.  Post-flight scripts
8.  Cleanup scripts

A style definition is a YAML block:

``` yaml
MyStyle:
    writer: mywriter
        ...
```

Style definitions are hierarchically structured by *style name* and *writer*. Both take values of type `MetaMap`. Style names by convention are MixedCase (`MyNotes`). Writer names are the same as corresponding pandoc writers (e.g. `latex`, `html`, `docx`, etc.) There is special writer for each style, `all`, whose settings apply to all writers of the style.

`parent` takes a list of styles, or a single style, whose properties the current definition inherits. It takes values of type `MetaInlines` or `MetaList` A style definition may have multiple parents. The properties of children override those of their parents, parents override grandparents, and so on. See section below on [style inheritance](#style-inheritance) for more details on inheritance.

Under a writer field, any of the following, and at least one, may appear:

| field         | value                                                          | value type    |
|:--------------|:---------------------------------------------------------------|:--------------|
| `metadata`    | default metadata fields                                        | `MetaMap`     |
| `template`    | pandoc template                                                | `MetaInlines` |
| `preflight`   | list of executables to run/kill before input doc is processed  | `MetaList`    |
| `filter`      | list of pandoc json filters to run/kill                        | `MetaList`    |
| `postprocess` | list of executables to run/kill to postprocess pandoc's output | `MetaList`    |
| `postflight`  | list of executables to run/kill after output file written      | `MetaList`    |
| `cleanup`     | list of executables to run/kill on exit irrespective of errors | `MetaList`    |

`metadata` contains default metadata that can be set by the style. Any metadata field that can appear in a pandoc document can be defined as default metadata. This includes pandoc metadata fields that are used by the standard templates, e.g. `numbersections`, `toc`. However, panzer comes into its own when one defines default metadata for your own custom templates. New default fields allow the style's templates to employ new variables, the values of which can be overriden by the user on a per document basis.

`template` specifies a pandoc [templates](http://johnmacfarlane.net/pandoc/demo/example9/templates.html) for the document. Templates typically are more useful in panzer than in vanilla pandoc because templates can safely employ new variables defined in the style's default metadata. For example, if you know that a style defines `copyright_notice` in its default metadata, then the style's templates can safely use `$copyright_notice$`.

`preflight` specifies executables that are run before any other scripts or filters. Preflight scripts are run after panzer reads the source documents, but before panzer runs pandoc to convert this data to the output format. Note that this means that if preflight scripts modify the input document files this will not be reflected in panzer's output.

`filter` specifies pandoc [json filters](http://johnmacfarlane.net/pandoc/scripting.html) that should be run. Filters gain two news powers from panzer. First, filters can be passed [more than one](#cli_options_executables) command line argument. The first command line argument is still reserved for the writer's name. Second, panzer injects a special metadata field, `panzer_reserved`, into the document which filters see. This field contains a json string that exposes [useful information](#passing_messages_exes) to filters. For more info, see section below on [compatibility](#pandoc_compatibility) with pandoc.

`postprocessor` specifies text-processing pipes that take pandoc's output document, do something to it, and give an output. Standard unix executables (`sed`, `tr`, etc.) may be used as postprocessors with arbitrary arguments. Or you can write your own. Postprocessors operate on text-based output from pandoc. Postprocessors are not run if a writer that produces binary output files is selected.

`postflight` specifies executables that are run after the output file has been written. If output is stdout, postflight scripts are run after output to stdout has been flushed. Postflight scripts are not run if a fatal error occurs earlier in the processing chain.

`cleanup` specifies executables that are run before panzer exits. Cleanup scripts run irrespective of whether an error has occurred earlier. Cleanup scripts are run after postflight scripts.

Here is a simple definition:

``` yaml
Notes:
    all:
        metadata:
            numbersections: false
    latex:
        metadata:
            numbersections: true
            fontsize:       12pt
        postflight:
            - run:          latexmk.py
```

If panzer were run on the following document with the latex writer selected,

``` yaml
---
title:  "My document"
author: John Smith
style:  Notes
...
```

it would run pandoc on the following input, and then execute `latexmk.py`.

``` yaml
---
title:          "My document"
author:         John Smith
numbersections: true
fontsize:       12pt
...
```

Here are [example style definitions](https://github.com/msprev/dot-panzer) created for my own use. They are only to give an idea of what a style definition and related executables could look like.

Writing a style definition
==========================

Styles are defined in either:

-   'Globally' in the `styles.yaml` file in panzer's support directory (normally, `~/.panzer/`)
-   'Locally' in a `styledef` field inside the metadata block of the document

Local definitions take precedence over global definitions.

Parents and inheritance
-----------------------

Inheritance among style settings follows five rules.

|:----|:----------------------------------------------------------------------------------------|
| 1.  | Metadata fields set outside a style definition override any style's setting             |
| 2.  | Local definitions inside a `styledef` field override global definitions in `style.yaml` |
| 3.  | In a list of styles, later ones override earlier ones.                                  |
| 4.  | Children override their parents.                                                        |
| 5.  | Writer-specific settings override settings for `all`.                                   |

There are some intuitive wrinkles regarding what 'overrides' means for different style properties. Generally, fields that pertain to the run list overriding is *additive* while other fields it is *non-additive*.

### Non-additive fields

For `metadata` and `template` fields, if two fields take different values (say, a parent and child set `numbersections` to different values), then inheritance is non-additive, and only one (the child) wins.

### Additive fields

For lists specified under `preflight`, `filter`, `postflight` and `cleanup` the overriding is additive. The overriding definition adds its items *after* the overridden ones. For example, if the parent adds as a postflight script `latexmk.py`, and the child adds as a postflight script `printlog.py`, then both scripts are run and `printlog.py` is run after `latexmk.py`

This creates a puzzle about how to remove items from these 'run lists'. This is accomplished by a specific declaration (see below). To remove an item, add it as the value of a `kill` field, or use `killall`.

### Command line options

In line with pandoc, command line options override metadata, and cannot be overridden by a metadata setting. Filters specified on the command line (via `--filter`) are run first. Filters specified on the command line cannot be removed by a `kill` or `killall` command. Templates specified on the command line (via `--template`) override a template specified in the metadata.

### Multiple input files

panzer treats multiple input files as dose pandoc: it joins them into a single document. Metadata (including panzer's additive fields) are merged using pandoc's existing rules for multiple documents (left-biased union). Note that this will result in different overriding behaviour to that described above. Subsequent instances of `postflight` will simply clobber previous instances rather than adding to them.

### stdin input

If panzer takes stdin input, it buffers this in a temporary file in the current working directory. This is because scripts assume they can read the data in the document. The temporary file is removed when panzer exits, irrespective of errors.

Executables
-----------

``` yaml
[preflight|filter|postprocess|postflight|cleanup]:
    - run: ...
      args: ...
    - kill: ...
    - killall: [true|false]
```

Executables (scripts, filters, postprocessors) are ordered by a *run list*. The run list determines what gets run when. Executables are run in the order that they appear in the run list: from first to last. The run list is specified by metadata lists with the name of the relevant process (`preflight`, `cleanup`, `filter`, `postprocess`). These metadata lists declare items that add or remove executables from the run list. If an item appears as the value of a `run` field, then it is added to the run list for that process. If an item appears as the value of a `kill` field, then any previous invocation is removed from the run list for that process. A run list for a process can emptied entirely by adding `killall: true`. Killing items does not prevent them being added later by a subsequent metadata declaration.

| field     | value                                 | value type    |
|:----------|:--------------------------------------|:--------------|
| `run`     | add to run list                       | `MetaInlines` |
| `kill`    | remove from run list                  | `MetaInlines` |
| `killall` | if true, empty run list at this point | `MetaBool`    |

### An executable's arguments

Arguments can be passed to executables by listing them as the value of the `args` field of an item that has a `run` field.

If `args` is a string, then that string is passed as on the command line to the external process. If `args` is a list, then the items in that list are used to construct the command line arguments from first to last. In this case, boolean values add double-dashed flags of the same name. Other values set double-dashed key--value arguments.

| field  | value                                          | value type    |
|:-------|:-----------------------------------------------|:--------------|
| `args` | string of command line arguments               | `MetaInlines` |
|        | list of key--value pairs:                      | `MetaList`    |
|        | `key: true`: argument passed is `--key`        | `MetaBool`    |
|        | `key: value`: argument passed is `--key=value` | `MetaInlines` |

The following constructions are equivalent:

``` yaml
- run: ...
  args: --verbose --bibliography="mybib.bib"
```

``` yaml
- run: ...
  args:
      - verbose: true
      - bibliography: mybib.bib
```

Finding scripts and filters
---------------------------

When panzer is searching for an executable or template, say filter `foo.py`, it will search in the following places and in the following order (current working directory is starting point; panzer's support directory is `~/.panzer`):

|:----|:------------------------------------------------|
| 1   | `foo.py`                                        |
| 2   | `filter/foo.py`                                 |
| 3   | `filter/foo/foo.py`                             |
| 4   | `~/.panzer/filter/foo.py`                       |
| 5   | `~/.panzer/filter/foo/foo.py`                   |
| 6   | `foo.py` in PATH defined by current environment |

panzer support directory
------------------------

`styles.yaml`, along with its related executables and templates, lives in panzer's support directory (default: `~/.panzer`).

    .panzer/
        styles.yaml
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        template/
        shared/

Within each directory, each executable may have its own subdirectory:

    postflight/
        latexmk/
            latexmk.py

Passing messages to executables
===============================

| subprocess    | arguments            | stdin                  | stdout                   | stderr         |
|---------------|:---------------------|:-----------------------|:-------------------------|:---------------|
| preflight     | set by `args` field  | json message           | to screen                | error messages |
| postflight    | set by `args` field  | json messa             | ge "                     | "              |
| postflight    | set by `args` field  | "                      | "                        | "              |
| cleanup       | set by `args` field  | "                      | "                        | "              |
| postprocessor | set by `args` field  | output te              | xt output te             | xt "           |
| filter        | set by `args` field; | json string of documen | t json string of documen | t "            |
|               | writer 1st arg       |                        |                          |                |

Passing messages to scripts
---------------------------

panzer sets the environment variable `PANZER_SHARED` to the location of the `shared` directory in the panzer support directory. `shared/` is where files shared between executables should be kept.

Scripts often need to know more than this. A script, for example, may need to know what files are being used as input to panzer, which file is the target output, and options being used for the document processing (e.g. the writer). Scripts are passed this information and more via stdin. They are sent it as a json-encoded message. The json message received on stdin in utf8 by scripts as follows:

``` json
JSON_MESSAGE = [{'metadata':  METADATA,
                 'template':  TEMPLATE,
                 'style':     STYLE,
                 'stylefull': STYLEFULL,
                 'styledef':  STYLEDEF,
                 'runlist':   RUNLIST,
                 'options':   OPTIONS}]
```

`METADATA` is the metadata branch of the document's AST, encoded in json, as would be produced by pandoc's json writer.

`TEMPLATE` is a string, possibly empty, with the full path to the selected template.

`STYLE` is a list with the styles that the user selected in the document with the `style` metadata field.

`STYLEFULL` is the expanded list of styles that are being applied in order to the document, including all parents, grandparents, etc.

`STYLEDEF` is the metadata branch of the document's AST that includes the definitions of styles used by the document (local and global).

`RUNLIST` is the run list for the document and it has the following structure.

``` json
RUNLIST = [{'kind':      'preflight'|'filter'|'postprocess'|'postflight'|'cleanup',
            'command':   'my command',
            'arguments': ['argument1', 'argument2', ...]
            'status':    'queued'|'running'|'failed'|'done'}
            'stderr':
            ...
            ...
          ]
```

`OPTIONS` is a dictionary with information about the command line options. It is divided into two dictionaries that concern `panzer` and `pandoc` respectively.

    OPTIONS = {
        'panzer': {
            'support'         : DEFAULT_SUPPORT_DIR,   # panzer support directory
            'debug'           : False,                 # panzer ---debug option
            'verbose'         : 1,                     # panzer ---verbose option
            'stdin_temp_file' : ''                     # name of temporary file used to store stdin input
        },
        'pandoc': {
            'input'      : [],                         # input files
            'output'     : '-',                        # output file ('-' means stdout)
            'pdf_output' : False,                      # write pdf directly?
            'read'       : '',                         # pandoc reader
            'write'      : '',                         # pandoc writer
            'template'   : '',                         # template set on command line
            'filter'     : [],                         # filters set on command line
            'options'    : []                          # remaining pandoc command line options
        }
    }

The `filter` and `template` fields specify filters and templates set on the command line (via `--filter` and `--template`) These fields do *not* contain any filters or the template specified in the metadata or style.

    RUN_LISTS = {
        'preflight'   : [],
        'filter'      : [],
        'postprocess' : [],
        'postflight'  : [],
        'cleanup'     : []
    }

Passing messages to filters
---------------------------

The method above will not work for filters, since stdin is already occupied with the document's AST. Filters can access the same information as scripts via a special metadata field that panzer injects into the document, `panzer_reserved`. The value of `panzer_reserved` is the same json string that scripts receive by stdin.

    panzer_reserved: |
        ```
        JSON_MESSAGE
        ```

Filters can retrieve the json message by extracting the following item from the document's AST:

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

Why not encode every item of `OPTIONS` individually as a pandoc metadata field? This would be needless work for both panzer and the filters. It is quicker and simpler to retrieve and encode the value of one field and run a json (de)serialisation operation. The point of pandoc metadata fields is to be easily human readable and editable. This concern does not apply if a field is never seen by the user and used only for inter-process communication.

Passing messages to postprocessors
----------------------------------

This is currently not possible.

Receiving messages from executables
===================================

panzer captures stderr output from all executables. Scripts/filters that are aware of panzer should send correctly formatted info and error messages to stderr for pretty printing. If a message is sent to stderr that is not correctly formatted as a json message, panzer will print it verbatim prefixed by a '!'. There is nothing wrong with these messages, but if you frequently use a non-panzer-aware script/filter, you may wish to consider writing a wrapper that will provide pretty messages.

The message format for stderr that panzer expects is a newline-separated string of utf-8 encoded json strings, each with the following structure:

    { 'level': LEVEL, 'message': MESSAGE }

`LEVEL` is a string that sets the error level; it can take one of the following values:

    'CRITICAL'
    'ERROR'
    'WARNING'
    'INFO'
    'DEBUG'
    'NOTSET'

`MESSAGE` is your error message.

The Python module `panzertools` provides a `log` function to scripts/filters to send error messages to panzer using this format.

Compatibility with pandoc
=========================

panzer works with all pandoc filters. But not all filters that work with panzer will work with pandoc.

panzer extends pandoc's filters in two ways:

1.  Filters can take more than one command line argument (first argument still reserved for the writer).
2.  Injecting a special `panzer_reserved` metadata field into the AST with lots of goodies for filters to mine.

Reserved metadata fields
------------------------

The following metadata fields are reserved for use by panzer. Using these fields in ways other than described above in your document is liable to produce unpredictable results.

-   `styledef`
-   `style`
-   `template`
-   `preflight`
-   `filter`
-   `postflight`
-   `postprocess`
-   `cleanup`
-   `panzer_reserved`

Using a custom pandoc writer with the name `all` should also be avoided.

Known issues
============

-   Slow (a Haskell implementation is in the works)
-   Calls to subprocesses (scripts, filters, etc.) are blocking
-   No Python 2 support

