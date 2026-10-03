demo:
	python3 -m applyorch demo

test:
	python3 -m unittest discover -s tests -t .

scrub:
	python3 scripts/scrub_check.py

.PHONY: demo test scrub
