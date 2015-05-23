SOURCE = README.md

PANDOC = /usr/local/bin/pandoc
PANZER = /usr/local/bin/panzer
TEMPLATES = /Users/msprevak/Dropbox/msprevak/dot-panzer/template
OUT_BASENAME := $(basename $(SOURCE))

.PHONY: clean

########################################################################
#               Make the documentation files for release               #
########################################################################

doc:	$(SOURCE)
	$(PANZER) $(SOURCE) -o ../$(OUT_BASENAME).md -t markdown_github ---quiet; \
	$(PANZER) $(SOURCE) -o ../$(OUT_BASENAME).rst -t rst ---quiet

########################################################################
#                 Standard makefile for markdown file                  #
########################################################################

html:	$(SOURCE)
	$(PANZER) $(SOURCE) -o $(OUT_BASENAME).html

pdf:	$(SOURCE)
	$(PANZER) $(SOURCE) -o $(OUT_BASENAME).tex

docx:	$(SOURCE)
	$(PANZER) $(SOURCE) -o $(OUT_BASENAME).docx

pandoc-html:	$(SOURCE)
	$(PANDOC) \
		$(SOURCE) \
		-o .tmp/_$(OUT_BASENAME)_.html \
		--template $(TEMPLATES)/article.html \
		-H $(TEMPLATES)/Momento-pandoc.css \
		--smart \
		--standalone

clean:
	- rm -f .tmp/* \
        $(OUT_BASENAME).pdf $(OUT_BASENAME).docx $(OUT_BASENAME).html \
		../$(OUT_BASENAME).md \
		../$(OUT_BASENAME).rst
