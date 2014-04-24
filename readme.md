---
title           : "panzer"
author          :
  - name        : Mark Sprevak
    affiliation : University of Edinburgh
    email       : mark.sprevak@ed.ac.uk
date            : 5 November 2013
...

# Rationale

[pandoc] is an extremely powerful and flexible document processing tool. 
    However, using it is like sitting behind the flight deck of the Space Shuttle. 
    Millions of dials can be twiddled, and it is not easy to know which combinations to choose. 
    Often you want to take it for a reliable and familiar ride rather than a trip to the moon. 

[panzer] can help by allowing you to drive pandoc with *styles*. 
    Styles control the look and feel of your document in a simple and reusable way. 
    Styles are combinations of templates, metadata settings, filters, postprocessers, and pre- and post-flight scripts. 
    panzer wraps around pandoc and twiddles the dials appropriate for your chosen style. 
    Instead of running `pandoc`, you run `panzer` on your document.

Styles are invoked, customised, and created using pandoc's metadata format.
    To use a style simply add the metadata key `style` to your pandoc document. 
    By convention, styles take capitalized values. 
    For example:

``` {.yaml}
style: Notes
```

This one-line addition to a document could, for example, activate the options below for the latex writer:

``` {.yaml}
Notes:
    latex:
        template:     notes.latex
        default:
            fontsize: 12pt
            headings: sans-serif
        filter:       
            - run:    sortnotes.py
```

A style is defined inside the document(s) fed to panzer, or in panzer's defaults file.

<!--Like pandoc, panzer expects all input to be encoded in utf-8, and yields-->
<!--all output in utf-8. This also to all interactions between panzer and-->
<!--processes that it spawns (scripts, etc.).-->


# Installation

Requirements:

* [pandoc]
* [python 3]

`panzer` is a python script and it can be installed via the standard mechanism.



# Use

`panzer` takes the same command line arguments and options as `pandoc`.
    panzer passes these arguments and options to the underlying instance of pandoc.
    panzer also has a few of its own command line options.
    These panzer-specific options are prefixed by triple dashes `---`.
    Run the command `panzer -h` to see a list of these panzer-specific options.

The `panzer` command can be used as a drop-in replacement for the `pandoc` command.


# Creating styles

Style are invoked in a document by using the metadata field `style`.
Styles can be defined in your document or in a separate YAML file that
contains default styles.

Styles are almost equivalent to templates. Invoking a style selects a
template (from the `support/templates` directory of the bundle), but it
also activates the appropriate pandoc filters to perform pre and post
processing for the LaTeX file generated for the style. The pandoc
filters used by each style are describe below. 

## `panzer`'s support directory

Unless you want mess in your files, you can expect to spend some time populating `panzer`'s support directory with your own files.
The default structure of the support directory is:

```
~/.panzer
    defaults.yaml
    cleanup/
    filter/
    postflight/
    postprocess/
    preflight/
    shared/
    template/
```

`defaults.yaml` is the file that contains all default style definitions.
    You should customise this file for your own use.

Each script directory will have 

```
postflight/
    latexmk/
        latexmk.py
```

The `shared` directory contains common scripts, libraries and modules, organised by language, which may be useful for script writers.
    By default `shared/python/panzertools.py`, which contains functions helpful to use in scripts.


## Example style: Notes


# Customising styles

--------------------------------------    --------      
`styledefault.all_styles.all_writers`     lowest                                
`styledefault.all_styles.`*my_writer*                                       
`styledefault.`*my_style*`.all_writers`                                     
`styledefault.`*my_style*`.`*my_writer*   highest                                
--------------------------------------    --------

--------------------------------------    --------   
`stylecustom.all_styles.`*my_writer*      lowest   
`stylecustom.`*my_style*`.all_writers`             
`stylecustom.`*my_style*`.`*my_writer*             
`stylecustom.all_styles.`*my_writer*      highest  
--------------------------------------    --------

# Creating scripts


## Filters

### Killing filters

* Filters can be bypassed ('killed') by adding them using the `kill` rather than the `run` field. Killing a filters will prevent it being run if it has been invoked at a lower level. A typical use case for this is to disable filters on a per-document basis.

* Adding the special item `- killall: true` to the list of filters will kill all previously applied (custom and default) filters. This is a way of starting from a clean slate for filtering a document.

Note that a killed filter will be reenabled if a higher-precedence field invokes it with `run`. 

``` {.yaml}
filter:   
    kill: optimise_bibtex
```


## Postprocessors

## Pre-flight scripts

Preflight scripts live in the `preflight-scripts` directory of panzer's 

Preflight scripts receive as input:

* The command line options specified by their `options` field
* Via standard input, a string representing the command line options that `panzer` receives

Preflight scripts yield as output:

* A return value: 
    * 0 for success
    * 1 for failure
    * 2 for critical error (abort further processing in `panzer`)

## Post-flight scripts

## Cleanup scripts


# Reserved metadata keys

The following metadata keys are reserved for use by `panzer` and should be avoided. 
    Using these fields in markdown in ways other than described above will result in unpredictable results.

* `panzer_reserved`
* `style`

# Known limitations

* Calls to subprocesses (scripts, etc.) are blocking


[pandoc]: http://johnmacfarlane.net/pandoc/index.html
[panzer]: https://github.com/msprev
[python 3]: https://www.python.org/download/releases/3.0

