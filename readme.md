---
title:           "panzer"
author:
  - name:        Mark Sprevak
    affiliation: University of Edinburgh
    email:       mark.sprevak@ed.ac.uk
date:            5 November 2013

...

[pandoc]: http://johnmacfarlane.net/pandoc/index.html

# Rationale

[`pandoc`][pandoc] is an extremely powerful and flexible document processing tool. However, using it is like sitting behind the flight deck of the Space Shuttle. Millions of settings that can be chosen, and it is not easy to know which combinations to choose.

`panzer` simplifies this by providing an elegant way to drive `pandoc` with *styles*. Styles are a powerful tool to easily control the look and feel of your document.

*Styles* are reusable combinations of templates, metadata settings, filters, postprocessers, and pre- and post-flight scripts. Styles are invoked and customised via a document's metadata. 



# Installing

place panezpan


# How styles work

Style are invoked in a document by using the metadata field `style`. Styles can be defined in your document or in a separate YAML file that contains default styles.

Styles are almost equivalent to templates. Invoking a style selects a template (from the `support/templates` directory of the bundle), but it also activates the appropriate pandoc filters to perform pre and post processing for the LaTeX file generated for the style. The pandoc filters used by each style are describe below. 


# Command line options

# Style definitions


# Writing new styles


# Example: Notes


# The support files


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

# Templates

Templates are specified in either `styledefault` or `stylecustom` in the following way:

~~~~ {.yaml}
---
styledefault:
    notes:
        latex:
            template:   
                name: notes.latex
...
~~~~


# Metadata

~~~~ {.yaml}
---
stylecustom:
    notes:
        latex:
            metadata:
                sans_headings:    false
                wide_margin:      false
                fontsize:         10pt
...
~~~~


# Filters

## Killing filters

* Filters can be bypassed ('killed') by adding them using the `kill` rather than the `run` field. Killing a filters will prevent it being run if it has been invoked at a lower level. A typical use case for this is to disable filters on a per-document basis.

* Adding the special item `- killall: true` to the list of filters will kill all previously applied (custom and default) filters. This is a way of starting from a clean slate for filtering a document.

Note that a killed filter will be reenabled if a higher-precedence field invokes it with `run`. 

~~~~ {.yaml}
---
filter:   
    kill: optimise_bibtex
...
~~~~


# Postprocessors

# Pre-flight scripts

Preflight scripts live in the `preflight-scripts` directory of panzer's 

Preflight scripts receive as input:

* The command line options specified by their `options` field
* Via standard input, a string representing the command line options that `panzer` receives

Preflight scripts yield as output:

* A return value: 
    * 0 for success
    * 1 for failure
    * 2 for critical error (abort further processing in `panzer`)

# Post-flight scripts

# Appendix

## Reserved metadata fields

The following metadata fields are reserved for use by `panzer` and should be avoided. Using these fields in markdown in ways other than described above will result in unpredictable results.

`style`  
`All`  
`filter`
`postprocess`
`preflight_script`
`postflight_script`  
`on_error`



