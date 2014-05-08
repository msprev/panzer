Introduction
============

[pandoc](http://johnmacfarlane.net/pandoc/index.html) is a powerful and flexible document processing tool. The problem is that using pandoc presents a huge range of options for customisation of document output. Millions of dials can be twiddled, and it is not easy to know which combinations to choose to quickly achieve your desired result. Often you want to produce document output that fits certain formats, and this may involve the coordination of many elements, scripts and filters.

[panzer](https://github.com/msprev) can help. panzer adds *styles* to pandoc. Styles are metadata fields that govern the look and feel of your document in a convenient and reusable way. Styles are effectively canned combinations of templates, metadata settings, filters, postprocessers, and pre- and post-flight scripts. panzer remembers all this so that you don't have to. Styles can be tweaked on a per document basis by adding the relevant metadata field.

How do I use panzer? Instead of `pandoc`, you run `panzer` on your document. panzer will drive pandoc and any associated scripts, and pass on the right information based on your style. It is easy to create and customise styles. This is done with YAML metadata. To invoke a style in your document, add the field `style` to its metadata. By convention, styles take capitalized values. For example:

    style: Notes

This would activate the `Notes` style. This style would be defined in panzer's `defaults.yaml` file or inside the document.

<!--Like pandoc, panzer expects all input to be encoded in utf-8, and yields-->
<!--all output in utf-8. This also to all interactions between panzer and-->
<!--processes that it spawns (scripts, etc.).-->


Installation
============

*Requirements:*

-   [pandoc](http://johnmacfarlane.net/pandoc/index.html)
-   [python 3](https://www.python.org/download/releases/3.0)

*Installation:*

Command line use
================

`panzer` takes the same command line arguments and options as `pandoc`. panzer passes these arguments and options to the underlying instance of pandoc. panzer also has a few of its own command line options. These panzer-specific options are prefixed by triple dashes `---`. Run the command `panzer -h` to see a list of panzer-specific options.

The `panzer` command can be used as a drop-in replacement for the `pandoc` command.

Styles
======

A style consists of the following elements:

1.  **Default metadata**: Any valid pandoc metadata can be set by the style. This includes standard metadata fields (`author`, `numberedsections`), or any custom metadata field you may create.
2.  **Template**: A pandoc template associated with each writer for the style.
3.  **Pre-flight scripts**: Executables run before the file(s) are processed by panzer.
4.  **Filters**: pandoc [json filters](http://johnmacfarlane.net/pandoc/scripting.html).
5.  **Postprocessors**: Text processing operations run on the output file from pandoc.
6.  **Post-flight scripts**: Executables run after the output is written.
7.  **Cleanup scripts**: Executables run after the output is written irrespective whether an error has occurred. Guaranteed to be run before panzer finishes.

Styles are defined in the `defaults.yaml` file in panzer's support directory (normally: `~/.panzer/`), or in your document's metadata. Style definitions are hierarchically scoped by *style name* and *pandoc writer*. There are two special values: `All` for style name, and `all` for name of writer. The `All` style is applied to every document. The `all` writer is applied for every writer for that style.

Here is an example definition of the style `Notes`:

    Notes:
        all:                 
            default:
                numbersections: true
        latex:
            default:
                lang: british
                papersize: a4paper
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

The standard metadata field `numberedsections` is set to true by default by the style. If the latex writer is being used, the language, papersize, and fontsize are automatically set. These metafields are moved into global scope in the document unless otherwise overridden. So apply this style and selecting the latex writer feeds pandoc a document containing:

    ---
    title: "My document"
    author: Mark Sprevak
    ...

    Here is my text

So apply this style and selecting the latex writer feeds pandoc a document containing:

    ---
    title: "My document"
    author: Mark Sprevak
    numbersections: true
    lang: british
    papersize: a4paper
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

    Here is my text

The first fields set metadata fields used by the template. The other fields are used by panzer to control its processing chain. These fields are accessible to the scripts and filters.

Combining styles
----------------

Items in styles are combined with a union biased to the most specific named settings. Items in the global scope take highest precedence (say, you place `template: mytemplate` in your document's metadata) Items in the style definitions in document take precedence over items in the definitions in `defaults.yaml` Items in the selected style take precedence over items in `All` and `all`.

Items in styles are combined with a union biased to the highest ranked items below:

1.  Global scope in document
2.  Style definitions in document:
    1.  Current style, current writer
    2.  Current style, `all` writer
    3.  `All` style, current writer
    4.  `All` style, `all` writer

3.  Style definitions in `defaults.yaml`:
    1.  Current style, current writer
    2.  Current style, `all` writer
    3.  `All` style, current writer
    4.  `All` style, `all` writer

If two items take different values (say, two different settings for `template`), then the item with the highest precedence above is used.

The exception to this are *additive fields*: lists of filters, postprocessors, and scripts. Here, the union above is non-destructive. Items lower in precedence are simply added to the list after higher precedence items. Items are added in the order that they appear in the style definition, first items run first. To remove a previously added filter or script use the `kill` or `killall` field:

    filter:
        - kill: smallcap.py

or

    filter:
        - killall: true

`kill` removes a named filter if already present. `killall` empties the filter list completely and starts from scratch. Note `kill` or `killall` only affect items of lower precedence in the list above, or which occur before them in the currently list. They do not prevent a filter or script being added by subsequent items or items with higher precedence. If you want to be sure a filter is not added, place the relevant `kill` or `killall` command last in the relevant list in global scope in your document, so it has the highest precedence.

If multiple documents are passed to panzer, their metadata is merged using pandoc's rules (left-biased union).

Creating your own style
=======================

Style are invoked in a document by using the metadata field `style`. Styles can be defined in your document or in a separate YAML file that contains default styles.

Styles are almost equivalent to templates. Invoking a style selects a template (from the `support/templates` directory of the bundle), but it also activates the appropriate pandoc filters to perform pre and post processing for the LaTeX file generated for the style. The pandoc filters used by each style are describe below.

The support directory
---------------------

Unless you want mess in your files, you can expect to spend some time populating `panzer`'s support directory with your own files. The default structure of the support directory is:

    ~/.panzer
        defaults.yaml
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        shared/
        template/

`defaults.yaml` is the file that contains all default style definitions. You should customise this file for your own use.

Each script directory will have

    postflight/
        latexmk/
            latexmk.py

The `shared` directory contains common scripts, libraries and modules, organised by language, which may be useful for script writers. By default `shared/python/panzertools.py`, which contains functions helpful to use in scripts.

Example style: Notes
--------------------

Customising styles
==================

|:--|:--|
|`styledefault.all_styles.all_writers`|lowest|
|`styledefault.all_styles.`*my\_writer*||
|`styledefault.`*my\_style*`.all_writers`||
|`styledefault.`*my\_style*`.`*my\_writer*|highest|

|:--|:--|
|`stylecustom.all_styles.`*my\_writer*|lowest|
|`stylecustom.`*my\_style*`.all_writers`||
|`stylecustom.`*my\_style*`.`*my\_writer*||
|`stylecustom.all_styles.`*my\_writer*|highest|

Creating scripts
================

Filters
-------

### Killing filters

-   Filters can be bypassed ('killed') by adding them using the `kill` rather than the `run` field. Killing a filters will prevent it being run if it has been invoked at a lower level. A typical use case for this is to disable filters on a per-document basis.

-   Adding the special item `- killall: true` to the list of filters will kill all previously applied (custom and default) filters. This is a way of starting from a clean slate for filtering a document.

Note that a killed filter will be reenabled if a higher-precedence field invokes it with `run`.

``` {.yaml}
filter:   
    kill: optimise_bibtex
```

Postprocessors
--------------

Pre-flight scripts
------------------

Preflight scripts live in the `preflight-scripts` directory of panzer's

Preflight scripts receive as input:

-   The command line options specified by their `options` field
-   Via standard input, a string representing the command line options that `panzer` receives

Preflight scripts yield as output:

-   A return value:
    -   0 for success
    -   1 for failure
    -   2 for critical error (abort further processing in `panzer`)

Post-flight scripts
-------------------

Cleanup scripts
---------------

Reserved metadata keys
======================

The following metadata keys are reserved for use by `panzer` and should be avoided. Using these fields in markdown in ways other than described above will result in unpredictable results.

-   `panzer_reserved`
-   `style`

Known issues
============

-   panzer is slower than vanilla pandoc because it runs pandoc twice (once for a read phase, once for a write phase)
-   Calls to subprocesses (scripts, etc.) are currently blocking
-   Untested under Windows

1.  **Default metadata**: Any valid pandoc metadata can be set by the style. This includes standard metadata fields (`author`, `numberedsections`), or any custom metadata field you may create.

2.  **Template**: A pandoc template associated with each writer for the style.

3.  **Pre-flight scripts**: Executables run before the file(s) are processed by panzer.

    -   *command line arguments*: set by the `opt` field
    -   *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
    -   *sterr*: captured and parsed by panzer

4.  **Filters**: pandoc [json filters](http://johnmacfarlane.net/pandoc/scripting.html).

    -   *command line arguments*: 1st argument is name of writer; other arguments set by the `opt` field
    -   *stdin*: json input with pandoc's abstract syntax tree
    -   *sterr*: captured and parsed by panzer
    -   *stout*: json output with pandoc's abstract syntax tree

5.  **Postprocessors**: Text processing operations run on the output file from pandoc.

    -   *command line arguments*: set by the `opt` field in the style
    -   *stdin*: output file from pandoc
    -   *sterr*: captured and parsed by panzer
    -   *stout*: processed file sent back to panzer

6.  **Post-flight scripts**: Executables run after the output is written.

    -   *command line arguments*: set by the `opt` field
    -   *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
    -   *sterr*: captured and parsed by panzer

7.  **Cleanup scripts**: Executables run after the output is written irrespective whether an error has occurred. Guaranteed to be run before panzer finishes.

    -   *command line arguments*: set by the `opt` field in the style
    -   *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
    -   *sterr*: captured and parsed by panzer


