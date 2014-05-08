---
title  : "panzer user guide"
author : Mark Sprevak
date   : 6 May 2014
style  : Notes
...

# Introduction

[pandoc][] is a powerful and flexible document processing tool. 
    The problem is that using pandoc presents a huge range of options for customisation of document output.
    Millions of dials can be twiddled, and it is not easy to know which combinations to choose to quickly achieve your desired result.
    Often you want to produce document output that fits certain formats, and this may involve the coordination of many elements, scripts and filters.

[panzer][] can help. 
    panzer adds *styles* to pandoc.
    Styles are metadata fields that govern the look and feel of your document in a convenient and reusable way. 
    Styles are effectively canned combinations of templates, metadata settings, filters, postprocessers, and pre- and post-flight scripts. 
    panzer remembers all this so that you don't have to.
    Styles can be tweaked on a per document basis by adding the relevant metadata field.

How do I use panzer?
    Instead of `pandoc`, you run `panzer` on your document.
    panzer will drive pandoc and any associated scripts, and pass on the right information based on your style.
    It is easy to create and customise styles.
    This is done with YAML metadata.
    To invoke a style in your document, add the field `style` to its metadata. 
    By convention, styles take capitalized values. 
    For example:

    style: Notes

This would activate the `Notes` style. 
    This style would be defined in panzer's `defaults.yaml` file or inside the document.



# Installation

*Requirements:*

* [pandoc][]
* [Python 3][]

Why is Python 3 required? 
    Python 3 provides sane unicode handling.

*Installation:*


# Command line use

`panzer` takes the same command line arguments and options as `pandoc`.
    panzer passes these arguments and options to the underlying instance of pandoc.
    panzer also has a few of its own command line options.
    These panzer-specific options are prefixed by triple dashes `---`.
    Run the command `panzer -h` to see a list of panzer-specific options.

Like pandoc, panzer expects all input to be encoded in utf-8.
    This also applies to interactions between panzer and processes that it spawns (scripts, etc.).

The `panzer` command can be used as a drop-in replacement for the `pandoc` command.


# Styles

A style consists of the following elements:

1. **Default metadata**: 
    Any valid pandoc metadata can be set by the style.
    This includes standard metadata fields (`author`, `numberedsections`),
        or any custom metadata field you may create.
2. **Template**:
    A pandoc template associated with each writer for the style.
3. **Pre-flight scripts**:
    Executables run before the file(s) are processed by panzer.
4. **Filters**:
    pandoc [json filters][pandoc-filters].
5. **Postprocessors**:
    Text processing operations run on the output file from pandoc.
6. **Post-flight scripts**:
    Executables run after the output is written.
7. **Cleanup scripts**:
    Executables run after the output is written irrespective whether an error has occurred.
    Guaranteed to be run before panzer finishes.


Styles are defined in the `defaults.yaml` file in panzer's support directory (normally: `~/.panzer/`), or in your document's metadata.
    Style definitions are hierarchically scoped by *style name* and *pandoc writer*.
    There are two special values: `All` for style name, and `all` for name of writer.
    The `All` style is applied to every document.
    The `all` writer is applied for every writer for that style.

Here is an example definition of a style `Notes` (only for illustrative purposes):


    Notes:
        all:                 
            default:
                numbersections: false
        latex:
            default:
                numbersections: true
                fontsize: 12pt
            preflight:
                - run: tmp_out.py
                  opt:
                    - directory: mytmp
                    - create: true
            filter:
                 - run: optimise_bib.py
            postprocess:
                 - run: smallcaps.py
                   opt: --verbose -skip-names
            postflight:
                - run: latexmk.py
                - run: open_pdf.py
            cleanup:
                - run: tmp_back.py

The standard metadata field `numberedsections` is set to true by default by the style.
    If the latex writer is being used, the language, papersize, and fontsize are automatically set.
    These metafields are moved into global scope in the document unless otherwise overridden.
    So apply this style and selecting the latex writer feeds pandoc a document containing:

    ---
    title: "My document"
    author: Mark Sprevak
    style: Notes
    ...

    Here is my text


So apply this style and selecting the latex writer invokes pandoc with a document containing:

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
    
    Here is my text

The first fields set metadata fields which will be used by the template.
The others control panzer's processing chain.
All these fields are accessible to the scripts and filters.

## Combining styles

Items in styles are combined with a union biased to the most specific named settings.
    Items in the global scope take highest precedence (say, you place `template: mytemplate` in your document's metadata, this would override any setting in the style).
    Items in the definitions in the document take precedence over items in the definitions in `defaults.yaml`
    Items in the selected style take precedence over items in `All` and `all`.

Items in styles are combined with a union biased to the highest ranked items below:

1. Global scope in document
2. Style definitions in document:
    a. Current style, current writer
    b. Current style, `all` writer
    c. `All` style, current writer
    d. `All` style, `all` writer
7. Style definitions in `defaults.yaml`:
    a. Current style, current writer
    b. Current style, `all` writer
    c. `All` style, current writer
    d. `All` style, `all` writer

If two items take different values (say, two different settings for `template`), then the item with the highest precedence is used.

The exceptions are *additive fields*: lists of filters, postprocessors, and scripts.
    Here, the union is non-destructive.
    Items lower in precedence are added to the list after higher precedence items.
    Items are added in the order that they appear in the style definition, first items run first.
    To remove a previously added filter or script use the `kill` or `killall` field:

    filter:
        - kill: smallcap.py

or 

    filter:
        - killall: true

`kill` removes a named filter if already present. 
    `killall` empties the filter list completely and starts from scratch.
    Note `kill` or `killall` only affect items of lower precedence in the list above, or which occur before them in the currently list.
    They do not prevent a filter or script being added by subsequent items or items with higher precedence.
    A killed filter will be re-enabled if a higher-precedence item invokes it with `run`. 
    If you want to be sure a filter is not added, place the relevant `kill` or `killall` command last in the relevant list in global scope in your document, so it has the highest precedence.

If multiple documents are passed to panzer, their metadata is merged using pandoc's rules (left-biased union).

# Creating your own style

Style are invoked in a document by using the metadata field `style`.
Styles can be defined in your document or in a separate YAML file that
contains default styles.

Styles are almost equivalent to templates. Invoking a style selects a
template (from the `support/templates` directory of the bundle), but it
also activates the appropriate pandoc filters to perform pre and post
processing for the LaTeX file generated for the style. The pandoc
filters used by each style are describe below. 

## The support directory

Unless you want mess in your files, you can expect to spend some time populating `panzer`'s support directory with your own files.
The default structure of the support directory is:

    ~/.panzer
        defaults.yaml
        cleanup/
        filter/
        postflight/
        postprocess/
        preflight/
        shared/
        template/

`defaults.yaml` is the file that contains all default style definitions.
    You should customise this file for your own use.

Each script directory will have 

    postflight/
        latexmk/
            latexmk.py

The `shared` directory contains common scripts, libraries and modules, organised by language, which may be useful for script writers.
    By default `shared/python/panzertools.py`, which contains functions helpful to use in scripts.

## Pre-flight scripts

* *command line arguments*: set by the `opt` field
* *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
* *sterr*: captured and parsed by panzer

## Filters

* *command line arguments*: 1st argument is name of writer; other arguments set by the `opt` field
* *stdin*: json input with pandoc's abstract syntax tree
* *sterr*: captured and parsed by panzer
* *stout*: json output with pandoc's abstract syntax tree

## Postprocessors

* *command line arguments*: set by the `opt` field in the style
* *stdin*: output file from pandoc
* *sterr*: captured and parsed by panzer
* *stout*: processed file sent back to panzer

## Post-flight scripts

* *command line arguments*: set by the `opt` field
* *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
* *sterr*: captured and parsed by panzer

## Cleanup scripts

* *command line arguments*: set by the `opt` field in the style
* *stdin*: receives json string that includes all panzer and pandoc options, including a list of input and output files
* *sterr*: captured and parsed by panzer

# Reserved metadata fields

The following metadata fields are reserved for use by panzer and should be avoided. 
    Using these fields in ways other than described above will result in unpredictable results.

* `panzer_reserved`
* `All`
* `style`
* Field whose name is the value of `style`

# Known issues

* panzer is slower than vanilla pandoc because it runs pandoc twice (once for a read phase, once for a write phase)
* Calls to subprocesses (scripts, etc.) are currently blocking
* Untested under Windows


 [pandoc]: http://johnmacfarlane.net/pandoc/index.html
 [panzer]: https://github.com/msprev
 [python 3]: https://www.python.org/download/releases/3.0
 [pandoc-filters]: http://johnmacfarlane.net/pandoc/scripting.html
