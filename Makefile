.PHONY: install data run test lint all clean

install:
	pip install -e ".[dev]"

data:
	python -m leadfunnel.download

run:
	python -m leadfunnel.pipeline

test:
	pytest -q

lint:
	ruff check src tests

all: data run test

clean:
	rm -rf reports/*.json reports/*.md figures/*.png outputs/*
