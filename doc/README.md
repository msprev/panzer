---
title  : "panzer user guide"
author : Mark Sprevak
date   : 11 May 2014
style  : Notes
...

# Introduction

[pandoc][] is a powerful and flexible document processing tool.
    pandoc presents a huge range of options for customisation of document output.
    Millions of dials can be twiddled, and it is not easy to know which combinations to choose to quickly achieve your desired result.
    Often you want to produce output with a defined look, and this may involve the coordination of many elements, scripts and filters.

[panzer][] can help.
    panzer adds *styles* to pandoc.
    Styles are metadata fields that govern the look and feel of your document in a convenient and reusable way.
    Styles are combinations of templates, metadata settings, filters, post-processors, and pre- and post-flight scripts.
    panzer remembers the options for a style so that you don't have to.
    Styles are written and selected using YAML metadata.
    Styles can be customised on a per document and per writer basis.

Instead of running `pandoc`, you run `panzer` on your document.
    panzer will run pandoc plus any associated scripts, and it will pass on information based on your style.
    To select a style in your document, add the field `style` to its metadata.
    By convention, styles have MixedCase values.
    For example:

    style: Notes

This would select the `Notes` style.
    This style should be defined in panzer's `styles.md` file or inside your document itself using the YAML syntax below.
    If a document lacks a `style` field, panzer is equivalent to pandoc.

panzer can be used as a lightweight alternative to makefiles, or in conjunction with makefiles.


# Installation

*Requirements:*

* [pandoc][]
* [Python 3][]

Why is Python 3 required?
    Python 3 provides sane unicode handling.

*Installation:*

    pip3 install panzer

# Command line use

`panzer` takes the same command line arguments and options as `pandoc`.
    panzer passes these arguments and options to the underlying instance of pandoc.
    `panzer` can be used as a drop-in replacement for the `pandoc` command.

panzer also has a few of its own command line options.
    These panzer-specific options are prefixed by triple dashes (`---`).
    Run the command `panzer -h` to see a list of these options.

Like pandoc, panzer expects all I/O to be encoded in utf-8.
    This applies to interaction between panzer and processes that it spawns (scripts, etc.).


# Styles

A style consists of the following elements, which can be set on a per writer basis:

1. Default metadata
2. Template
3. Pre-flight scripts
4. Filters
5. Postprocessors
6. Post-flight scripts
7. Cleanup scripts

A style definition is a metadata block:

    Style:
        writer:
            ...

Style definitions are structured by *style name* and *writer*.
    Both are fields are of type `MetaMap`.
    Style names by convention are capitalized (`Notes`).
    Writer names are the same as corresponding pandoc writers (e.g. `latex`, `html`, `docx`, etc.)
    There is a special style, `Base`, whose settings applies to all documents with styles.
    There is special writer for each style, `default`, whose settings apply to all writers of the style.

Under a writer field, the following metadata fields may appear:

  field           value                                                            value type
  --------------- ---------------------------------------------------------------- ---------------
  `parent`        styles that it inherits                                          `MetaInlines` or `MetaList`
  `metadata`      default metadata fields                                          `MetaMap`
  `template`      pandoc template                                                  `MetaInlines`
  `preflight`     list of executables to run/kill before input doc is processed    `MetaList`
  `filter`        list of pandoc json filters to run/kill                          `MetaList`
  `postprocess`   list of executables to run/kill to postprocess pandoc's output   `MetaList`
  `postflight`    list of executables to run/kill after output file written        `MetaList`
  `cleanup`       list of executables to run/kill on exit irrespective of errors   `MetaList`

**Default metadata** can be set by the style.
    Any metadata field that can appear in a pandoc document can be defined as default metadata.
    This includes standard pandoc metadata fields, e.g. `numbersections`, `toc`.
    However, panzer comes into its own when one defines new default metadata fields for a style.
    New default fields allow the style's templates to employ new variables, the values of which can be overriden by the user on a per document basis.

**Templates** are pandoc [templates][].
    Templates typically are more useful in panzer than in vanilla pandoc because templates can safely employ new variables defined in the style's default metadata.
    For example, if a style defines `copyright_notice` in default metadata, then the style's templates can safely use `$copyright_notice$`.

**Preflight scripts** are executables that are run before any other scripts or filters.
    Preflight scripts are run after panzer reads the source documents, but before panzer runs pandoc to convert this data to the output format.
    Note that this means that if preflight scripts modify the input document files this will not be reflected in panzer's output.

**Filters** are pandoc [json filters][].
    Filters gain two news powers from panzer.
        First, filters can be passed [more than one](#cli_options_executables) command line argument.
        The first command line argument is still reserved for the writer's name to maintain backwards compatibility with pandoc's filters.
        Second, panzer injects a special metadata field, `panzer_reserved`, into the document which filters see.
        This field contains a json string that exposes [useful information](#passing_messages_exes) to filters, including information about all command line arguments with which panzer was invoked.
        See section below on [compatibility](#pandoc_compatibility) with pandoc.

**Postprocessors** are text-processing pipes that take pandoc's output document, do some further text processing, and give an output.
    Standard unix executables (`sed`, `tr`, etc.) may be used as postprocessors with arbitrary arguments.
    Or you can write your own.
    Postprocessors operate on text-based output from pandoc.
    Postprocessors are not run if the `pdf` writer is selected.

**Postflight scripts** are executables that are run after the output file has been written.
    If output is stdout, postflight scripts are run after output to stdout has been flushed.
    Postflight scripts are not run if a fatal error occurs earlier in the processing chain.

**Cleanup scripts** are executables that are run before panzer exits.
    Cleanup scripts run irrespective of whether an error has occurred earlier.
    Cleanup scripts are run after postflight scripts.

### Style definition locations

Styles can be defined either in:

1. The `styles.md` file in panzer's support directory (normally, `~/.panzer/`)
2. The metadata of the input document(s).

### Run lists

Executables (scripts, filters, postprocessors) are specified using a *run list*.
    The run list is populated by the metadata list for the relevant executables (`preflight`, `cleanup`, `filter`, `postprocess`).
    These metadata lists consist of items that are parsed as commands to add or remove executables from the relevant run list.
    If an item contains a `run` field, then an executable whose name is the value of that field is added to the run list (`run: ...`).
    Executables will be run in the order that they are listed: from first to last.
    If an item contains a `kill` field, then an executable whose name is the value of that field is removed from the run list if present (`kill: ...`).
    Killing does not prevent a later item from adding the executable again.
    The run list is emptied by adding an item `killall: true`.
    Arguments can be passed to executables by listing them as the value of the `args` field of an item that has a `run` field.

  field       value                                   value type
  ----------- --------------------------------------- ---------------
  `run`       add to run list                         `MetaInlines`
  `kill`      remove from run list                    `MetaInlines`
  `killall`   if true, empty run list at this point   `MetaBool`


```
    [preflight|filter|postprocess|postflight|cleanup]:
        - run: ...
          args: ...
        - kill: ...
        - killall: [true|false]
```

### Passing command line arguments to executables {#cli_options_executables}

The `args` field allows one to specify command line arguments in two ways.
    If `args` is a string, then that string is used as the command line arguments to the external process.
    If `args` is a list, then the items in that list are used to construct the command line arguments.
    Boolean values set double-dashed flags of the same name, and other values set double-dashed key--value command line arguments of the same name as the field.
    The command line arguments are constructed from first to last.

  field    value                                    value type
  -------- ---------------------------------------- ---------------
  `args`   verbatim command line arguments          `MetaInlines`
  `args`   list of key--value pairs:                `MetaList`
           `flag: true` argument is `--flag`        `MetaBool`
           `key: value` argument is `--key=value`   `MetaInlines`


The following are equivalent:

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

Either style for the `args` field may be used in the same file.

## Example style

Here is a definition for the `Notes` style:

    Notes:
        default:
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

    ---
    title: "My document"
    author: Mark Sprevak
    style: Notes
    ...


panzer would run pandoc with the following document:

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



## Applying styles to documents

Individual items in styles are combined with a union biased to the most specific named settings.
    Items in the global scope take highest precedence (say, you place `template: new_one` in your document's metadata, this would override any setting by the style).
    Items in the style definitions that appear inside the document take precedence over items that appear in the style definitions in `styles.md`
    Items in the currently selected style take precedence over items in `Base` and `default`.
    This allows for a flexible and commonsensical way for style fields to be overrided.

Items in styles are combined with a union biased to the highest ranked items below:

1. Options specified on command line trump everything
2. Raw metadata fields in document (i.e. outside a style definition) clobber any set by styles
3. Style definitions inside the document's own metadata definitions inside `styles.yaml`
4. Current writer trumps `default` writer
5. Children trump their parents
6. Later parents (listed later under `parent`) trump earlier parents
7. Later styles (listed later in `style` field) trump earlier styles

The 'trumping' relation is one in which settings

This sounds complex, but it is actually pretty natural and fits roughly with one's expectations on how styles should behave.

Here are some examples:

    style: Notes
    Notes:
        default:
            metadata:
                name: Notey
        latex:
            metadata:
                name: Latexy
    name: MyName

As it stands, the `name` gets set to `MyName`.


### Non-additive fields

If two fields take different values (say, two different settings for `numbersections`), then the item with the highest precedence wins.

### Additive fields

Exceptions are lists of filters, post-processors, and scripts.
    These are additive fields and the union is non-destructive.
        Items lower in precedence are appended to the list after higher precedence items.
        To remove a filter or script from the list, add it as the value of a `kill` field:

    filter:
        - kill: smallcap.py

`kill` removes a filter/script if it is already present.
    `- killall: true` empties the entire list and starts from scratch.
    Note that `kill` or `killall` only affect items of lower precedence.
    They do not prevent a filter or script being added afterwards.
    A killed filter will be enabled again if a higher-precedence item invokes it again with `run`.
    If you want to be sure to kill a filter, place the relevant `kill` as the last item in the list in your document's metadata.

Any text outside the metadata block in `styles.md` is ignored.

### Command line options

Command line options override settings in the metadata, and they cannot be disable by a metadata setting.

Filters specified on the command line (as a value of `--filter`) are always run first: they will be treated as appearing at the start of the list.
    Filters specified on the command line cannot be killed by a `kill` or `killall` command.

Templates specified on the command line (as a value of `--template`) will override any template selected in the metadata.

### Input files

If multiple input files are given to panzer on the command line, panzer's uses pandoc to join those files into a single document.
    Metadata fields (including style definitions and items in global scope) are merged using pandoc's rules (left-biased union).
    Note that this means that if fields in multiple files have fields with the same name (e.g. `filter`) they will clobber each other, rather than follow the rules on additive union above.

If panzer is passed input via stdin, it stores this in a temporary file in the current working directory.
    This is necessary because scripts may wish to inspect and modify this data.
    See section on [passing messages to scripts](#passing_messages) to see how they can access this information.
    The temporary file is always removed when panzer exits, irrespective of whether any errors have occurred.



# Writing your own style

Styles can be defined in your document's metadata or in panzer's `styles.md` file.

## panzer support directory

panzer's style definition file `styles.md` lives in panzer's support directory (default: `~/.panzer`).

    .panzer/
        styles.md
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        template/

`styles.md` is the file that contains all default style definitions.
    Templates, scripts and filters live in their own subdirectories with corresponding names.

A recommended structure for each executable's directory:

    postflight/
        latexmk/
            latexmk.py


## Finding scripts and filters

When panzer is looking for an executable, say a filter with name `foo`, it will search in the following places in the order from first to last
    (the current working directory is `.`; panzer's support directory is `~/.panzer`):

1. `./foo`
2. `./panzer/filter/foo`
3. `./panzer/filter/foo/foo`
4. `~/.panzer/filter/foo`
5. `~/.panzer/filter/foo/foo`
6. `foo` in system's path as exported via shell

The same rules apply for templates.

## Passing messages to executables {#passing_messages_exes}

subprocess     arguments              stdin                      stdout                     stderr
---------      -------------------    -----------                ---------                  --------------
preflight      set by `args` field    json message               to screen                  error messages
postflight     "                      json message               "                          "
postflight     "                      "                          "                          "
cleanup        "                      "                          "                          "
postprocessor  "                      output text                output text                "
filter         writer 1st arg;        json string of document    json string of document    "
               others, set by `args`

### Passing messages to scripts {#passing_messages}

Scripts need to know about the command line options passed to panzer.
    A script, for example, may need to know what files are being used as input to panzer, which file is the target output, and options being used for the document processing (e.g. the writer).
    Scripts are passed this information via stdin by a utf8-encoded json message.
    The json message received on stdin by scripts is as follows:

    [ { 'cli_options' : OPTIONS,
        'run_lists'   : RUN_LISTS,
        'metadata'    : METADATA   } ]

`OPTIONS` is a json dictionary with the relevant information.
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

### Passing messages to filters {#passing_messages_filters}

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

### Passing messages to postprocessors

There is currently no mechanism for passing a similar json message to postprocessors.

## Passing messages back to panzer

panzer captures stderr output from all executables.
    Scripts/filters that are aware of panzer should send correctly formatted info and error messages to stderr for pretty printing according to panzer's preferences.
    If a message is sent to stderr that is not correctly formatted, panzer will forward it print it verbatim prefixed by a '!'.
    This means that panzer can be used with generic (non-panzer-aware) scripts and filters.
    However, if you frequently use a non-panzer-aware script/filter, you may wish to consider writing a thin wrapper that will provide pretty panzer-style error messages.

The message format for stderr that panzer expects is a newline-separated sequence of utf-8 encoded json strings, each with the following structure:

    [ { 'error_msg': { 'level': LEVEL, 'message': MESSAGE } } ]

`LEVEL` is a string that sets the error level; it can take one of the following values:

    'CRITICAL'
    'ERROR'
    'WARNING'
    'INFO'
    'DEBUG'
    'NOTSET'

`MESSAGE` is your error message.

The Python module `panzertools` provides a `log` function to scripts/filters to send error messages to panzer using this format.


# Reserved metadata fields

The following metadata fields are reserved for use by panzer and should be avoided.
    Using these fields in ways other than described above in your document will result in unpredictable results.

* `panzer_reserved`
* `style`
* Field with name same as the value of `style` field.
    Style names should be capitalized (`Notes`) to prevent name collision with other fields of the same name (`notes`).

# Compatibility with pandoc {#pandoc_compatibility}

panzer works will all pandoc filters.
Note that not all filters that work with panzer will work with pandoc's vanilla `--filter` option.

panzer extends pandoc's existing use of filters by:

1. Filters may take more than one command line argument (first argument still reserved for the writer).
    Presumably pandoc does not permit this because the syntax to provide arguments to filters from the command line would be awkward and non-obvious.
    panzer lets filters be specified cleanly in metadata, so this limitation does not apply.
2. Injecting a special `panzer_reserved` metadata field into document containing json message with lots of goodies for filters to mine.

# Known issues

* Calls to subprocesses (scripts, filters, etc.) are blocking
* Incompatible with Python 2 (pull requests welcome)
* panzer is not the fastest; a Haskell version is in the works and it should be much faster.


 [pandoc]: http://johnmacfarlane.net/pandoc/index.html
 [panzer]: https://github.com/msprev
 [python 3]: https://www.python.org/download/releases/3.0
 [json filters]: http://johnmacfarlane.net/pandoc/scripting.html
 [templates]: http://johnmacfarlane.net/pandoc/demo/example9/templates.html
