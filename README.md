-----

Development has ceased on panzer. Over the years, pandoc has gained
powerful new functionality (e.g. the `--metadata-file` option and Lua
filters) that means that 90% of what can be done with panzer can be done
with pandoc and some simple wrapper scripts. I no longer use panzer in
my own workflow for this reason.

If you would like to take over development of panzer, let me know.

-----

# panzer

panzer adds *styles* to
[pandoc](http://johnmacfarlane.net/pandoc/index.html). Styles provide a
way to set all options for a pandoc document with one line (‘I want this
document be an article/CV/notes/letter’).

You can think of styles as a level up in abstraction from a pandoc
template. Styles are combinations of templates, metadata settings,
pandoc command line options, and instructions to run filters, scripts
and postprocessors. These settings can be customised on a per writer and
per document basis. Styles can be combined and can bear inheritance
relations to each other. panzer exposes a large amount of structured
information to the external processes called by styles, allowing those
processes to be both more powerful and themselves controllable via
metadata (and hence also by styles). Styles simplify makefiles, bundling
everything related to the look of the document in one place.

You can think of panzer as an exoskeleton that sits around pandoc and
configures pandoc based on a single choice in your document.

To use a style, add a field with your style name to the yaml metadata
block of your document:

``` yaml
style: Notes
```

Multiple styles can be supplied as a list:

``` yaml
style:
  - Notes
  - BoldHeadings
```

Styles are defined in a yaml file
([example](https://github.com/msprev/dot-panzer/blob/master/styles/styles.yaml)).
The style definition file, plus associated executables, are placed in
the `.panzer` directory in the user’s home folder
([example](https://github.com/msprev/dot-panzer)).

A style can also be defined inside the document’s metadata block:

``` yaml
---
style: Notes
styledef:
  Notes:
    all:
      metadata:
        numbersections: false
    latex:
      metadata:
        numbersections: true
        fontsize: 12pt
      commandline:
        columns: "`75`"
      lua-filter:
        - run: macroexpand.lua
      filter:
        - run: deemph.py
...
```

Style settings can be overridden by adding the appropriate field outside
a style definition in the document’s metadata block:

``` yaml
---
style: Notes
numbersections: true
filter:
  - run: smallcaps.py
commandline:
  - pdf-engine: "`xelatex`"
...
```

# Installation

``` bash
pip3 install git+https://github.com/msprev/panzer
```

*Requirements:*

  - [pandoc](http://johnmacfarlane.net/pandoc/index.html) \> 2.0
  - [Python 3](https://www.python.org/downloads/)
  - [pip](https://pip.pypa.io/en/stable/index.html) (included in most
    Python 3 distributions)

*To upgrade existing installation:*

``` bash
pip3 install --upgrade git+https://github.com/msprev/panzer
```

On Arch Linux systems, the AUR package
[panzer-git](https://aur.archlinux.org/packages/panzer-git/) can be
used.

## Troubleshooting

An [issue](https://github.com/msprev/panzer/issues/20) has been reported
using pip to install on Windows. If the method above does not work, use
the alternative install method below.

``` 
    git clone https://github.com/msprev/panzer
    cd panzer
    python3 setup.py install
```

*To upgrade existing installation:*

``` 
    cd /path/to/panzer/directory/cloned
    git pull
    python3 setup.py install --force
```

# Use

Run `panzer` on your document as you would `pandoc`. If the document
lacks a `style` field, this is equivalent to running `pandoc`. If the
document has a `style` field, panzer will invoke pandoc plus any
associated scripts, filters, and populate the appropriate metadata
fields.

`panzer` accepts the same command line options as `pandoc`. These
options are passed to the underlying instance of pandoc. pandoc command
line options can also be set via metadata.

panzer has additional command line options. These are prefixed by triple
dashes (`---`). Run the command `panzer -h` to see them:

``` 
  -h, --help, ---help, ---h
                        show this help message and exit
  -v, --version, ---version, ---v
                        show program's version number and exit
  ---quiet              only print errors and warnings
  ---strict             exit on first error
  ---panzer-support PANZER_SUPPORT
                        panzer user data directory
  ---pandoc PANDOC      pandoc executable
  ---debug DEBUG        filename to write .log and .json debug files
```

Panzer expects all input and output to be utf-8.

# Style definition

A style definition may consist
of:

| field         | value                              | value type                    |
| :------------ | :--------------------------------- | :---------------------------- |
| `parent`      | parent(s) of style                 | `MetaList` or `MetaInlines`   |
| `metadata`    | default metadata fields            | `MetaMap`                     |
| `commandline` | pandoc command line options        | `MetaMap`                     |
| `template`    | pandoc template                    | `MetaInlines` or `MetaString` |
| `preflight`   | run before input doc is processed  | `MetaList`                    |
| `filter`      | pandoc filters                     | `MetaList`                    |
| `lua-filter`  | pandoc lua filters                 | `MetaList`                    |
| `postprocess` | run on pandoc’s output             | `MetaList`                    |
| `postflight`  | run after output file written      | `MetaList`                    |
| `cleanup`     | run on exit irrespective of errors | `MetaList`                    |

Style definitions are hierarchically structured by *name* and *writer*.
Style names by convention should be MixedCase (`MyNotes`) to avoid
confusion with other metadata fields. Writer names are the same as those
of the relevant pandoc writer (e.g. `latex`, `html`, `docx`, etc.) A
special writer, `all`, matches every writer.

  - `parent` takes a list or single style. Children inherit the
    properties of their parents. Children may have multiple parents.

  - `metadata` contains default metadata set by the style. Any metadata
    field that can appear in a pandoc document can appear here.

  - `commandline` specifies pandoc’s command line options.

  - `template` is a pandoc
    [template](http://johnmacfarlane.net/pandoc/demo/example9/templates.html)
    for the style.

  - `preflight` lists executables run before the document is processed.
    These are run after panzer reads the input, but before that input is
    sent to pandoc.

  - `filter` lists pandoc [json
    filters](http://johnmacfarlane.net/pandoc/scripting.html). Filters
    gain two new properties from panzer. For more info, see section on
    [compatibility](#compatibility) with pandoc.

  - `lua-filter` lists pandoc [lua
    filters](https://pandoc.org/lua-filters.html).

  - `postprocessor` lists executable to pipe pandoc’s output through.
    Standard unix executables (`sed`, `tr`, etc.) are examples of
    possible use. Postprocessors are skipped if a binary writer
    (e.g. `docx`) is used.

  - `postflight` lists executables run after the output has been
    written. If output is stdout, postflight scripts are run after
    stdout has been flushed.

  - `cleanup` lists executables run before panzer exits and after
    postflight scripts. Cleanup scripts run irrespective of whether an
    error has occurred earlier.

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
    commandline:
      wrap: preserve
    filter:
      - run: deemph.py
    postflight:
      - run: latexmk.py
```

If panzer were run on the following document with the latex writer
selected,

``` yaml
---
title: "My document"
style: Notes
...
```

it would run pandoc with filter `deemph.py` and command line option
`--wrap=preserve` on the following and then execute `latexmk.py`.

``` yaml
---
title: "My document"
numbersections: true
fontsize: 12pt
...
```

## Style overriding

Styles may be defined:

  - ‘Globally’ in `.yaml` files in `.panzer/styles/`
  - ‘Locally’ in `.yaml` files in the current working directory
    `./styles/`)
  - ‘In document’ inside a `styledef` field in the document’s yaml
    metadata block

If no `.panzer/styles/` directory is found, panzer will look for global
style definitions in `.panzer/styles.yaml` if it exists. If no
`./styles/` directory is found in the current working directory, panzer
will look for local style definitions in `./styles.yaml` if it exists.

Overriding among style settings is determined by the following
rules:

| \# | overriding rule                                                    |
| :- | :----------------------------------------------------------------- |
| 1  | Local style definitions override global style definitions          |
| 2  | In document style definitions override local style definitions     |
| 3  | Writer-specific settings override settings for `all`               |
| 4  | In a list, later styles override earlier ones                      |
| 5  | Children override parents                                          |
| 6  | Fields set outside a style definition override any style’s setting |

For fields that pertain to scripts/filters, overriding is *additive*;
for other fields, it is *non-additive*:

  - For `metadata`, `template`, and `commandline`, if one style
    overrides another (say, a parent and child set `numbersections` to
    different values), then inheritance is non-additive, and only one
    (the child) wins.

  - For `preflight`, `lua-filter`, `filter`, `postflight` and `cleanup`
    if one style overrides another, then the ‘winner’ adds its items
    after those of the ‘loser’. For example, if the parent adds to
    `postflight` an item `-run: latexmk.py`, and the child adds `- run:
    printlog.py`, then `printlog.py` will be run after `latexmk.py`

  - To remove an item from an additive list, add it as the value of a
    `kill` field: for example, `- kill: latexmk.py`

Arguments passed to panzer directly on the command line trump any style
settings, and cannot be overridden by any metadata setting. Filters
specified on the command line (via `--filter` and `--lua-filter`) are
run first, and cannot be removed. All lua filters are run after json
filters. pandoc options set via panzer’s command line invocation
override any set via `commandline`.

Multiple input files are joined according to pandoc’s rules. Metadata
are merged using left-biased union. This means overriding behaviour when
merging multiple input files is different from that of panzer, and
always non-additive.

If fed input from stdin, panzer buffers this to a temporary file in the
current working directory before proceeding. This is required to allow
preflight scripts to access the data. The temporary file is removed when
panzer exits.

## The run list

Executables (scripts, filters, postprocessors) are specified by a list
(the ‘run list’). The list determines what gets run when. Processes are
executed from first to last in the run list. If an item appears as the
value of a `run:` field, then it is added to the run list. If an item
appears as the value of a `kill:` field, then any previous occurrence is
removed from the run list. Killing an item does not prevent it from
being added later. A run list can be completely emptied by adding the
special item `- killall: true`.

Arguments can be passed to executables by listing them as the value of
the `args` field of that item. The value of the `args` field is passed
as the command line options to the external process. This value of
`args` should be a quoted inline code span (e.g. ``"`--options`"``) to
prevent the parser interpreting it as markdown. Note that json filters
always receive the writer name as their first argument.

Lua filters cannot take arguments and the contents of their `args` field
is ignored.

Example:

``` yaml
- filter:
  - run: setbaseheader.py
    args: "`--level=2`"
- postprocess:
  - run: sed
    args: "`-e 's/hello/goodbye/g'`"
- postflight:
  - kill: open_pdf.py
- cleanup:
  - killall: true
```

The filter `setbaseheader.py` receives the writer name as its first
argument and `--level=2` as its second argument.

When panzer is searching for a filter `foo.py`, it will look for:

| \# | look for                                        |
| :- | :---------------------------------------------- |
| 1  | `./foo.py`                                      |
| 2  | `./filter/foo.py`                               |
| 3  | `./filter/foo/foo.py`                           |
| 4  | `~/.panzer/filter/foo.py`                       |
| 5  | `~/.panzer/filter/foo/foo.py`                   |
| 6  | `foo.py` in PATH defined by current environment |

Similar rules apply to other executables and to templates.

The typical structure for the support directory `.panzer` is:

    .panzer/
        cleanup/
        filter/
        lua-filter/
        postflight/
        postprocess/
        preflight/
        template/
        shared/
        styles/

Within each directory, each executable may have a named subdirectory:

    postflight/
        latexmk/
            latexmk.py

## Pandoc command line options

Arbitrary pandoc command line options can be set using metadata via
`commandline`. `commandline` can appear outside a style definition and
in a document’s metadata block, where it overrides the settings of any
style.

`commandline` contains one field for each pandoc command line option.
The field name is the unabbreviated name of the relevant pandoc command
line option (e.g. `standalone`).

  - For pandoc flags, the value should be boolean (`true`, `false`),
    e.g. `standalone: true`.
  - For pandoc key-values, the value should be a quoted inline code
    span, e.g. ``include-in-header: "`path/to/my/header`"``.
  - For pandoc repeated key-values, the value should be a list of inline
    code spans, e.g.

<!-- end list -->

``` yaml
commandline:
  include-in-header:
    - "`file1.txt`"
    - "`file2.txt`"
    - "`file3.txt`"
```

Repeated key-value options in `comandline` are added after any provided
from the command line. Overriding styles append to repeated key-value
lists of the styles that they override.

`false` plays a special role. `false` means that the pandoc command line
option with the field’s name, if set, should be unset. `false` can be
used for both flags and key-value options (e.g. `include-in-header:
false`).

Example:

``` yaml
commandline:
  standalone: true
  slide-level: "`3`"
  number-sections: false
  include-in-header: false
```

This passes the following options to pandoc `--standalone
--slide-level=3` and removes any `--number-sections` and
`--include-in-header=...` options.

These pandoc command line options cannot be set via `commandline`:

  - `bash-completion`
  - `dump-args`
  - `filter`
  - `from`
  - `help`
  - `ignore-args`
  - `list-extensions`
  - `list-highlight-languages`
  - `list-highlight-styles`
  - `list-input-formats`
  - `list-output-formats`
  - `lua-filter`
  - `metadata`
  - `output`
  - `print-default-data-file`
  - `print-default-template`
  - `print-highlight-style`
  - `read`
  - `template`
  - `to`
  - `variable`
  - `version`
  - `write`

# Passing messages to external processes

External processes have just as much information as panzer does. panzer
sends its information to external processes via a json message. This
message is sent as a string over stdin to scripts (preflight,
postflight, cleanup scripts). It is stored inside a `CodeBlock` of the
AST for filters. Note that filters need to parse the `panzer_reserved`
field and deserialise the contents of its `CodeBlock` to recover the
json message. Some relevant discussion is
[here](https://github.com/msprev/panzer/issues/38#issuecomment-367664291).
Postprocessors do not receive a json message (if you need it, you should
probably be using a filter).

    JSON_MESSAGE = [{'metadata':    METADATA,
                     'template':    TEMPLATE,
                     'style':       STYLE,
                     'stylefull':   STYLEFULL,
                     'styledef':    STYLEDEF,
                     'runlist':     RUNLIST,
                     'options':     OPTIONS}]

  - `METADATA` is a copy of the metadata branch of the document’s AST
    (useful for scripts, not useful for filters)

  - `TEMPLATE` is a string with path to the current template

  - `STYLE` is a list of current style(s)

  - `STYLEFULL` is a list of current style(s) including all parents,
    grandparents, etc. in order of application

  - `STYLEDEF` is a copy of all style definitions employed in document

  - `RUNLIST` is a list of processes in the run list; it has the
    following
    structure:

<!-- end list -->

    RUNLIST = [{'kind':      'preflight'|'filter'|'lua-filter'|'postprocess'|'postflight'|'cleanup',
                'command':   'my command',
                'arguments': ['argument1', 'argument2', ...],
                'status':    'queued'|'running'|'failed'|'done'
               },
                ...
                ...
              ]

  - `OPTIONS` is a dictionary containing panzer’s and pandoc’s command
    line options:

<!-- end list -->

``` python
OPTIONS = {
    'panzer': {
        'panzer_support':  const.DEFAULT_SUPPORT_DIR,
        'pandoc':          'pandoc',
        'debug':           str(),
        'quiet':           False,
        'strict':          False,
        'stdin_temp_file': str()   # tempfile used to buffer stdin
    },
    'pandoc': {
        'input':      list(),      # list of input files
        'output':     '-',         # output file; '-' is stdout
        'pdf_output': False,       # if pandoc will write a .pdf
        'read':       str(),       # reader
        'write':      str(),       # writer
        'options':    {'r': dict(), 'w': dict()}
    }
}
```

`options` contains the command line options with which pandoc is called.
It consists of two separate dictionaries. The dictionary under the `'r'`
key contains all pandoc options pertaining to reading the source
documents to the AST. The dictionary under the `'w'` key contains all
pandoc options pertaining to writing the AST to the output document.

Scripts read the json message above by deserialising json input on
stdin.

Filters can read the json message by reading the metadata field,
`panzer_reserved`, stored as a raw code block in the AST, and
deserialising the string `JSON_MESSAGE_STR` to recover the json:

    panzer_reserved:
      json_message: |
        ``` {.json}
        JSON_MESSAGE_STR
        ```

# Receiving messages from external processes

panzer captures stderr output from all executables. This is for pretty
printing of info and errors. Scripts and filters should send json
messages to panzer via stderr. If a message is sent to stderr that is
not correctly formatted, panzer will print it verbatim prefixed by a
‘\!’.

The json message that panzer expects is a newline-separated sequence of
utf-8 encoded json dictionaries, each with the following structure:

    { 'level': LEVEL, 'message': MESSAGE }

  - `LEVEL` is a string that sets the error level; it can take one of
    the following values:
    
    ``` 
      'CRITICAL'
      'ERROR'
      'WARNING'
      'INFO'
      'DEBUG'
      'NOTSET'
    ```

  - `MESSAGE` is a string with your message

# Compatibility

panzer accepts pandoc filters. panzer allows filters to behave in two
new ways:

1.  Json filters can take more than one command line argument (first
    argument still reserved for the writer).
2.  A `panzer_reserved` field is added to the AST metadata branch with
    goodies for filters to mine.

For pandoc, json filters and lua-filters are applied in the order
specified by respective occurances of `--filter` and `--lua-filter` on
the command line. This behaviour is not entirely supported in panzer.
Instead, all json filters are applied first and in the order specified
on the command line and the style definition (command line filters are
applied first and unkillable). Then the lua-filters are applied, also in
the order specified on the command line and by the style definition
(command line filters are applied first and unkillable). The reasons for
the divergence with pandoc’s behaviour are complex but mainly derive
from performance benefit.

The follow pandoc command line options cannot be used with panzer:

  - `--bash-completion`
  - `--dump-args`
  - `--ignore-args`
  - `--list-extensions`
  - `--list-highlight-languages`
  - `--list-highlight-styles`
  - `--list-input-formats`
  - `--list-output-formats`
  - `--print-default-template`, `-D`
  - `--print-default-data-file`
  - `--version`, `-v`
  - `--help`, `-h`

The following metadata fields are reserved for use by panzer:

  - `styledef`
  - `style`
  - `template`
  - `preflight`
  - `filter`
  - `lua-filter`
  - `postflight`
  - `postprocess`
  - `cleanup`
  - `commandline`
  - `panzer_reserved`
  - `read`

The writer name `all` is also occupied.

# Known issues

Pull requests welcome:

  - Slower than I would like (calls to subprocess slow in Python)
  - Calls to subprocesses (scripts, filters, etc.) block ui
  - [Possible issue under
    Windows](https://github.com/msprev/panzer/pull/9), so far reported
    by only one user. A leading dot plus slash is required on filter
    filenames. Rather than having `- run: foo.bar`, on Windows one needs
    to have `- run: ./foo.bar`. More information on this is welcome. I
    am happy to fix compatibility problems under Windows.

# FAQ

1.  Why do I get the error `[Errno 13] Permission denied`? Filters and
    scripts must be executable. Vanilla pandoc allows filters to be run
    without their executable permission set. panzer does not allow this.
    The solution: set the executable permission of your filter or
    script, `chmod +x myfilter_name.py` For more, see
    [here](https://github.com/msprev/panzer/issues/22).

2.  Does panzer expand `~` or `*` inside field of a style definition?
    panzer does not do any shell expansion/globbing inside a style
    definition. The reason is described
    [here](https://github.com/msprev/panzer/issues/23). TL;DR: expansion
    and globbing are messy and not something that panzer is in a
    position to do correctly or predictably inside a style definition.
    You need to use the full path to reference your home directory
    inside a style definition.

# Similar

  - <https://github.com/mb21/panrun>
  - <https://github.com/htdebeer/pandocomatic>
  - <https://github.com/balachia/panopy>
  - <https://github.com/phyllisstein/pandown>

# Release notes

  - 1.4.1 (22 February 2018):
      - improved support of lua filters thanks to feedback from
        [jzeneto](https://github.com/jzeneto)
  - 1.4 (20 February 2018):
      - support added for lua filters
  - 1.3.1 (18 December 2017):
      - updated for pandoc 2.0.5
        [\#35](https://github.com/msprev/panzer/issues/34). Support for
        all changes to command line interface and `pptx` writer.
  - 1.3 (7 November 2017):
      - updated for pandoc 2.0
        [\#31](https://github.com/msprev/panzer/issues/31). Please note
        that this version of panzer *breaks compatibility with versions
        of pandoc earlier than 2.0*. Please upgrade to a version of
        pandoc \>2.0. Versions of pandoc prior to 2.0 will no longer be
        supported in future releases of panzer.
  - 1.2 (12 January 2017):
      - fixed issue introduced by breaking change in panzer 1.1
        [\#27](https://github.com/msprev/panzer/issues/27). Added panzer
        compatibility mode for pandoc versions \<1.18. All version of
        pandoc \>1.12.1 should work with panzer now.
  - 1.1 (27 October 2016):
      - breaking change: support pandoc 1.18’s new api; earlier versions
        of pandoc will not work
  - 1.0 (21 July 2015):
      - new: `---strict` panzer command line option:
        [\#10](https://github.com/msprev/panzer/issues/10)
      - new: `commandline` allows repeated options using lists:
        [\#3](https://github.com/msprev/panzer/issues/3)
      - new: `commandline` lists behave as additive in style
        inheritance: [\#6](https://github.com/msprev/panzer/issues/6)
      - new: support multiple yaml style definition files:
        [\#4](https://github.com/msprev/panzer/issues/4)
      - new: support local yaml style definition files:
        [\#4](https://github.com/msprev/panzer/issues/4)
      - new: simplify format for panzer’s json message:
        [ce2a12](https://github.com/msprev/panzer/commit/f3a6cc28b78957827cb572e254977c2344ce2a12)
      - new: reproduce pandoc’s reader depending on writer settings:
        [\#1](https://github.com/msprev/panzer/issues/1),
        [\#7](https://github.com/msprev/panzer/issues/7)
      - fix: refactor `commandline` implementation:
        [\#1](https://github.com/msprev/panzer/issues/1)
      - fix: improve documentation:
        [\#2](https://github.com/msprev/panzer/issues/2)
      - fix: unicode error in `setup.py`:
        [\#12](https://github.com/msprev/panzer/issues/12)
      - fix: support yaml style definition files without closing empty
        line: [\#13](https://github.com/msprev/panzer/issues/13)
      - fix: add `.gitignore` files to repository:
        [PR\#1](https://github.com/msprev/panzer/pull/9)
  - 1.0b2 (23 May 2015):
      - new: `commandline` - set arbitrary pandoc command line options
        via metadata
  - 1.0b1 (14 May 2015):
      - initial release
