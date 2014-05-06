`pandoc <http://johnmacfarlane.net/pandoc/index.html>`__ is an extremely
powerful and flexible document processing tool. However, using it is
like sitting behind the flight deck of the Space Shuttle. Millions of
dials can be twiddled, and it is not easy to know which combinations to
choose. Often you want to take it for a reliable and familiar ride
rather than a trip to the moon.

`panzer <https://github.com/msprev>`__ can help by allowing you to drive
pandoc with *styles*. Styles control the look and feel of your document
in a simple and reusable way. Styles are combinations of templates,
metadata settings, filters, postprocessers, and pre- and post-flight
scripts. panzer wraps around pandoc and twiddles the dials appropriate
for your chosen style. Instead of running ``pandoc``, you run ``panzer``
on your document.

Styles are invoked, customised, and created using pandoc's metadata
format. To use a style simply add the metadata key ``style`` to your
pandoc document. By convention, styles take capitalized values. For
example:

.. code:: yaml

    style: Notes

This one-line addition to a document could, for example, activate the
options below for the latex writer:

.. code:: yaml

    Notes:
        latex:
            template:     notes.latex
            default:
                fontsize: 12pt
                headings: sans-serif
            filter:       
                - run:    sortnotes.py

A style is defined inside the document(s) fed to panzer, or in panzer's
defaults file.

.. raw:: html

   <!--Like pandoc, panzer expects all input to be encoded in utf-8, and yields-->
   <!--all output in utf-8. This also to all interactions between panzer and-->
   <!--processes that it spawns (scripts, etc.).-->

Installation
============

Requirements:

-  `pandoc <http://johnmacfarlane.net/pandoc/index.html>`__
-  `python 3 <https://www.python.org/download/releases/3.0>`__

``panzer`` is a python script and it can be installed via the standard
mechanism.

Use
===

``panzer`` takes the same command line arguments and options as
``pandoc``. panzer passes these arguments and options to the underlying
instance of pandoc. panzer also has a few of its own command line
options. These panzer-specific options are prefixed by triple dashes
``---``. Run the command ``panzer -h`` to see a list of these
panzer-specific options.

The ``panzer`` command can be used as a drop-in replacement for the
``pandoc`` command.
