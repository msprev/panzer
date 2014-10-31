---
title  : "panzer user guide"
author : Mark Sprevak
date   : 11 May 2014
style  : Notes
template :
...

# Warning

This documentation is a work in progress.
    Much of it is out of date.
    panzer's code is pretty much complete.
    Current focus is to:

1.  Write documentation
2.  Create full test suite

---

# Introduction

[pandoc][] is a powerful and flexible document processing tool.
    However, often you want to produce output with a certain look, and this may involve the coordination of many elements, scripts and filters.

[panzer][] can help.
    panzer adds *styles* to pandoc.
    Styles are metadata fields that govern the look and feel of your document in a convenient and reusable way.
    Styles are combinations of templates, metadata settings, filters, postprocessors, preflight and postflight scripts.
    Styles are written in YAML and can be cut and pasted into pandoc metadata blocks.
    Styles can be customised on a per document and per writer basis.

Instead of running `pandoc`, you run `panzer` on your document.
    panzer will invoke pandoc plus any associated scripts, and it will pass on information based on your style.
    To select a style in your document, add the field `style` to its metadata.

By convention, styles have MixedCase names.
    For example:

``` {.yaml}
style: MyNotes
```

If a document lacks a `style` metadata field, running `panzer` is equivalent to running `pandoc`.


# Installation

*Requirements:*

* [pandoc][]
* [Python 3][]

Python 3 provides sane unicode handling.

*Quick installation:*

    pip3 install panzer

*Source files:*

Alternatively, if you want to hack panzer, the source is freely available:
    <https://github.com/msprev/panzer>


# Command line use

`panzer` takes the same command line arguments and options as `pandoc`.
    panzer passes these arguments and options to a spawned instance of pandoc.
    `panzer` can be used as a drop-in replacement for the `pandoc` command.

panzer also has a few of its own command line options.
    These panzer-specific options are prefixed by triple dashes (`---`).
    Run the command `panzer -h` to see a list of these options:

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

Like pandoc, panzer expects all input and output to be encoded in utf-8.
    This also applies to interaction between panzer and executables that it spawns (scripts, etc.).


# Styles

A style definition consists of the following elements, all but the first of which can be set on a per writer basis:

1.  Parent style(s)
2.  Default metadata
3.  Template
4.  Pre-flight scripts
5.  Filters
6.  Postprocessors
7.  Post-flight scripts
8.  Cleanup scripts

A style definition is a YAML block:

``` {.yaml}
Style:
    parent:
    writer:
        ...
```

Style definitions are hierarchically structured by *style name* and *writer*.
    Both take values of type `MetaMap`.
    Style names by convention are MixedCase (`MyNotes`).
    Writer names are the same as corresponding pandoc writers (e.g. `latex`, `html`, `docx`, etc.)
    There is special writer for each style, `all`, whose settings apply to all writers of the style.

**Parent** is a list of styles, or a single style, whose properties the current definition inherits.
    It takes values of type `MetaInlines` or `MetaList`
    A style definition may have multiple parents.
    The properties of children override those of their parents, parents override grandparents, and so on.
    See section below on [style inheritance](#style-inheritance) for more details on inheritance.

Under a writer field, any (and at least one) of the following fields may appear:

  field           value                                                            value type
  --------------- ---------------------------------------------------------------- ---------------
  `metadata`      default metadata fields                                          `MetaMap`
  `template`      pandoc template                                                  `MetaInlines`
  `preflight`     list of executables to run/kill before input doc is processed    `MetaList`
  `filter`        list of pandoc json filters to run/kill                          `MetaList`
  `postprocess`   list of executables to run/kill to postprocess pandoc's output   `MetaList`
  `postflight`    list of executables to run/kill after output file written        `MetaList`
  `cleanup`       list of executables to run/kill on exit irrespective of errors   `MetaList`

**Metadata** can be set by the style.
    Any metadata field that can appear in a pandoc document can be defined as default metadata.
    This includes pandoc metadata fields that are used by the standard templates, e.g. `numbersections`, `toc`.
    However, panzer comes into its own when one defines default metadata for your own custom templates.
    New default fields allow the style's templates to employ new variables, the values of which can be overriden by the user on a per document basis.

**Templates** are pandoc [templates][].
    Templates typically are more useful in panzer than in vanilla pandoc because templates can safely employ new variables defined in the style's default metadata.
    For example, if you know that a style defines `copyright_notice` in its default metadata, then the style's templates can safely use `$copyright_notice$`.

**Preflight scripts** are executables that are run before any other scripts or filters.
    Preflight scripts are run after panzer reads the source documents, but before panzer runs pandoc to convert this data to the output format.
    Note that this means that if preflight scripts modify the input document files this will not be reflected in panzer's output.

**Filters** are pandoc [json filters][].
    Filters gain two news powers from panzer.
        First, filters can be passed [more than one](#cli_options_executables) command line argument.
        The first command line argument is still reserved for the writer's name.
        Second, panzer injects a special metadata field, `panzer_reserved`, into the document which filters see.
        This field contains a json string that exposes [useful information](#passing_messages_exes) to filters.
        For more info, see section below on [compatibility](#pandoc_compatibility) with pandoc.

**Postprocessors** are text-processing pipes that take pandoc's output document, do something to it, and give an output.
    Standard unix executables (`sed`, `tr`, etc.) may be used as postprocessors with arbitrary arguments.
    Or you can write your own.
    Postprocessors operate on text-based output from pandoc.
    Postprocessors are not run if a writer that produces binary output files is selected.

**Postflight scripts** are executables that are run after the output file has been written.
    If output is stdout, postflight scripts are run after output to stdout has been flushed.
    Postflight scripts are not run if a fatal error occurs earlier in the processing chain.

**Cleanup scripts** are executables that are run before panzer exits.
    Cleanup scripts run irrespective of whether an error has occurred earlier.
    Cleanup scripts are run after postflight scripts.

## Example

Here is a simple definition for a `Notes` style:

``` {.yaml}
Notes:
    all:
        metadata:
            numbersections: false
    latex:
        metadata:
            numbersections: true
            fontsize:       12pt
        postflight:
            - run: latexmk.py
```

If panzer is run on the following document with the latex writer selected:

``` {.yaml}
---
title:  "My document"
author: John Smith
style:  Notes
...
```


panzer would run pandoc with the following document, and then run `latexmk.py` immediately.

``` {.yaml}
---
title: "My document"
author: John Smith
numbersections: true
fontsize: 12pt
...
```

Here are some [example style definitions](http://https://github.com/msprev/dot-panzer).
    These were created for my own use.
    They are not designed to be used in any environment.
    Nevertheless, they should give an idea of how to write style definitions and related executables.

# Writing a style definition

Styles are defined in either:

-   The global `styles.yaml` file in panzer's support directory (normally, `~/.panzer/`)
-   Inside a local `styledef` field in the metadata block the input document(s)

## Executables

```
    [preflight|filter|postprocess|postflight|cleanup]:
        - run: ...
          args: ...
        - kill: ...
        - killall: [true|false]
```

Executables (scripts, filters, postprocessors) are ordered by a *run list*.
    The run list determines what gets run when.
    Executables are run in the order that they appear in the run list: from first to last.
    The run list is specified by metadata lists with the name of the relevant process (`preflight`, `cleanup`, `filter`, `postprocess`).
    These metadata lists declare items that add or remove executables from the run list.
    If an item appears as the value of a `run` field, then it is added to the run list for that process.
    If an item appears as the value of a `kill` field, then any previous invocation is removed from the run list for that process.
    A run list for a process can emptied entirely by adding `killall: true`.
    Killing items does not prevent them being added later by a subsequent metadata declaration.

  field       value                                   value type
  ----------- --------------------------------------- ---------------
  `run`       add to run list                         `MetaInlines`
  `kill`      remove from run list                    `MetaInlines`
  `killall`   if true, empty run list at this point   `MetaBool`

### An executable's arguments {#cli_options_executables}

Arguments can be passed to executables by listing them as the value of the `args` field of an item that has a `run` field. 

If `args` is a string, then that string is passed as on the command line to the external process.
    If `args` is a list, then the items in that list are used to construct the command line arguments from first to last.
    In this case, boolean values add double-dashed flags of the same name. 
    Other values set double-dashed key--value arguments.

  field    value                                             value type
  -------- ----------------------------------------          ---------------
  `args`   string of command line arguments                  `MetaInlines`
           list of key--value pairs:                         `MetaList`
           `key: true`: argument passed is `--key`           `MetaBool`
           `key: value`: argument passed is `--key=value`    `MetaInlines`


The following constructions are equivalent:

```
- run: ...
  args: --verbose --bibliography="mybib.bib"
```

```
- run: ...
  args:
      - verbose: true
      - bibliography: mybib.bib
```

## Parents and inheritance

Inheritance among style settings follows four rules.
    Fields specified inside the document's metadata block override any style setting.
    When multiple styles are applied, later styles override earlier ones.
    Children override their parents.
    Writer-specific settings override settings for `all`.
    That is it.

There are some intuitive wrinkles regarding what 'overrides' means for different style properties.
    Generally, fields that pertain to the run list are *additive* while other fields are *non-additive*.

### Non-additive fields

For `metadata` and `template` fields, if two fields take different values (say, a parent and child set `numbersections` to different values), then inheritance is destructive, and only one (the child) wins.

### Additive fields

For lists specified under `preflight`, `filter`, `postflight` and `cleanup` the union is non-destructive.
    An overriding definition simply adds its items after the overridden ones.

This creates a puzzle about how to remove an items from an additive field.
    This is accomplished by issuing a specific declaration.
    To remove an item from the list, add it as the value of a `kill` field:

    filter:
        - kill: smallcap.py

`kill` removes the item from earlier in the list if present.
    `- killall: true` empties the entire list and starts from scratch.
    Note that `kill` or `killall` only affect items earlier in the list.
    They do not prevent a filter or script being added afterwards.
    A killed executable will be enabled again if a higher-precedence item invokes it again with `run`.
    If you want to be sure to kill an executable, place the relevant `kill` as the last item in the list in your document's metadata.

### Command line options

Command line options override metadata, and cannot be overridden by a metadata setting.
    Filters specified on the command line (via `--filter`) are always run first.
    Filters specified on the command line cannot be killed by a `kill` or `killall` command.
    Templates specified on the command line (via `--template`) always override a template specified in the metadata.

### Input files

For multiple input files, panzer's uses pandoc to join them into a single document.
    Metadata fields (including panzer's additive ones) are merged using pandoc's existing rules for multiple documents (left-biased union).

If panzer is to take input from stdin, it stores this input in a temporary file in the current working directory.
    This is because scripts may need to inspect and modify the data.
    The temporary file is removed when panzer exits, irrespective of whether errors occur.

## panzer support directory

`styles.yaml`, along with its related executables and templates, lives in panzer's support directory (default: `~/.panzer`).

    .panzer/
        styles.yaml
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        template/

Within each directory, each executable may have its own subdirectory:

    postflight/
        latexmk/
            latexmk.py


## Finding scripts and filters

When panzer is searching for an executable or template, say filter `foo`, it will search in the following places and in the following order
    (current working directory is `.`; panzer's support directory is `~/.panzer`):

--   --------------------------------------------
1    `./foo`
2    `./filter/foo`
3    `./filter/foo/foo`
4    `~/.panzer/filter/foo`
5    `~/.panzer/filter/foo/foo`
6    `foo` in PATH defined by current environment
--   --------------------------------------------

# Passing messages to executables {#passing_messages_exes}

subprocess     arguments              stdin                      stdout                     stderr
---------      -------------------    -----------                ---------                  --------------
preflight      set by `args` field    json message               to screen                  error messages
postflight     set by `args` field                     json message               "                          "
postflight     set by `args` field                      "                          "                          "
cleanup        set by `args` field                      "                          "                          "
postprocessor  set by `args` field                      output text                output text                "
filter         set by `args` field;        json string of document    json string of document    "
               writer 1st arg

## Passing messages to scripts {#passing_messages}

Scripts need to know about the command line options passed to panzer.
    A script, for example, may need to know what files are being used as input to panzer, which file is the target output, and options being used for the document processing (e.g. the writer).
    Scripts are passed this information via stdin by a utf8-encoded json message.
    The json message received on stdin by scripts is as follows:

``` {.json}
    MESSAGE = [{'metadata':  METADATA,
                'template':  TEMPLATE,
                'style':     STYLE,
                'stylefull': STYLEFULL,
                'styledef':  STYLEDEF,
                'runlist':   RUNLIST,
                'options':   OPTIONS}]
```

`OPTIONS` is a dictionary with information about the command line options.
    It is divided into two dictionaries that concern `panzer` and `pandoc` respectively.

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

The `filter` and `template` fields specify filters and templates set on the command line (via `--filter` and `--template`)
    These fields do *not* contain any filters or the template specified in the metadata or style.

    RUN_LISTS = {
        'preflight'   : [],
        'filter'      : [],
        'postprocess' : [],
        'postflight'  : [],
        'cleanup'     : []
    }



## Passing messages to filters {#passing_messages_filters}

The method above will not work for filters, since they receive the document as an AST via stdin.
    Nevertheless, it is conceivable that a filter may need to access information about panzer's command line options (for example, if it is going to create a temporary file to used by a later script).
    Filters can access the same information as scripts via a special metadata field that panzer injects into the document, `panzer_reserved`.
    The value of `panzer_reserved` is a json string identical to that received by the scripts via stdin.

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

Why not encode every item of `OPTIONS` individually as a pandoc metadata field?
    This would be more work for both panzer and the filters.
    It is quicker and simpler to retrieve/encode the value of just one field and run a json (de)serialisation operation.
    The point of pandoc metadata fields is to be easily human readable and editable.
    This concern does not apply if a field is never seen by the user and used only for inter-process communication.

## Passing messages to postprocessors

This is currently not possible.

# Receiving messages from executables

panzer captures stderr output from all executables.
    Scripts/filters that are aware of panzer should send correctly formatted info and error messages to stderr for pretty printing according to panzer's preferences.
    If a message is sent to stderr that is not correctly formatted, panzer will forward it print it verbatim prefixed by a '!'.
    This means that panzer can be used with generic (non-panzer-aware) scripts and filters.
    However, if you frequently use a non-panzer-aware script/filter, you may wish to consider writing a thin wrapper that will provide pretty panzer-style error messages.

The message format for stderr that panzer expects is a newline-separated sequence of utf-8 encoded json strings, each with the following structure:

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


# Compatibility with pandoc {#pandoc_compatibility}

panzer works with all pandoc filters.
    But not all filters that will work with panzer will work with vanilla pandoc.

panzer extends pandoc's existing use of filters in two ways:

1. Filters can take more than one command line argument (first argument still reserved for the writer).
2. Injecting a special `panzer_reserved` metadata field into the AST containing lots of goodies for filters to mine.

## Reserved metadata fields

The following metadata fields are reserved for use by panzer.
    Using these fields in ways other than described above in your document is liable to produce unpredictable results.

* `styledef`
* `style`
* `template`
* `preflight`
* `filter`
* `postflight`
* `postprocess`
* `cleanup`
* `panzer_reserved`

Creating a pandoc writer with the name `all` should also be avoided.

# Known issues

* Slow (a Haskell implementation is in the works that uses pandoc as a library; it should be almost as fast as pandoc)
* Calls to subprocesses (scripts, filters, etc.) are blocking
* No Python 2 support (pull requests welcome)

 [pandoc]: http://johnmacfarlane.net/pandoc/index.html
 [panzer]: https://github.com/msprev
 [python 3]: https://www.python.org/download/releases/3.0
 [json filters]: http://johnmacfarlane.net/pandoc/scripting.html
 [templates]: http://johnmacfarlane.net/pandoc/demo/example9/templates.html
