set export
set positional-arguments

DEV := "./.dev"
DIST := DEV / "dist"
VENV :=  "./.venv"
DJ := "DJANGO_SETTINGS_MODULE=demo.settings PYTHONPATH=. uv run django-admin"


# Display recipe listing
help:
    @just --list

# Show all recipe variables
info:
    @echo dist = {{DIST}}
    @echo dj = {{DJ}}


# Setup the demo project for non-docker development
demo-init:
    rm -f demo/demo.sqlite3
    {{DJ}} migrate --no-input
    {{DJ}} loaddata demo/fixtures/picker.json
    {{DJ}} import_picks tests/nfl2024.json tests/quidditch.json tests/eng1.json

# Run the demo project in non-docker mode
demo *args='':
    {{DJ}} "$@"

# Create virtual environment and install / update all dev dependencies
init: info update demo-init
    @echo Initialization complete

graph:
    brew upgrade graphviz
    uv pip install -U pygraphviz
    {{DJ}} graph_models picker -o resources/models.png -t django2018
    open resources/models.png

# Run test suite
test *args='':
    #!/usr/bin/env bash
    for s in `python scripts/permute.py "py{312,313,314}-dj{52,60,main}"`; do
        echo s =  $s
    done
    # uv run pytest -vv -s --diff-width=60 "$@"

    # py{312,313,314}-dj{52,60,main}


# RE-run test suite with just previous failures
retest:
    uv run pytest -vv -s --diff-width=60 --lf

# Run all tox tests
tox *args='':
    #!/usr/bin/env bash
    if [ -z "${args}" ]; then
        uv run tox
    else
        uv run tox "$@"
    fi

# Run coverage report from test suite
cov:
    -uv run coverage run -m pytest -vv -s
    uv run coverage report
    uv run coverage html

# Remove the virtual env dir
rmvenv:
    #!/usr/bin/env bash
    if [ -d ./venv ]; then
        rm -rf {{VENV}}
    fi

# Remove all *.pyc files and __pycache__ dirs
clean:
    find . -name .DS_Store -delete
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete

# Remove the dev directory, where all generated artifacts are stored
clean-dev:
    rm -rf {{DEV}}
    rm -f demo/demo.sqlite3

# Remove all build and dist artifacts
clean-build:
    rm -rf {{DIST}}/*

clean-eggs:
    rm -rf ./picker.egg-info

# Clean all build, test, and compile artifacts and remove venv
[confirm('Remove all build, test, coverage, and compiled artifacts and delete venv?')]
purge: clean clean-dev rmvenv clean-build clean-eggs
    echo All artifacts purged

# Build sdist and wheel files for distribution
build:
    uv run python -m build --outdir {{DIST}}

# Build distros and upload to PyPI
upload:
    twine upload {{DIST}}/*

# Run linter and code formatter tools
lint:
    @echo Linting...
    -uv run ruff check src/picker tests demo

    @echo Format checks...
    -uv run ruff format --diff --line-length 100 src/picker tests demo

# Build the demo Docker container
docker-build *args='':
    docker compose build "$@"

# Run the Django server in a Docker container
docker-run *args='':
    @echo Browse to http://127.0.0.1:8008 when Docker is up
    docker compose up "$@"

# Execute a command in a running Docker container
docker-exec *args='':
    docker compose exec app "$@"

version arg="":
    #!/usr/bin/env bash
    if [ -z "${arg}" ]; then
        grep -E "__version__ = \"[^\"]+\"" picker/__init__.py
    else
        sed -E "s/:Version: [0-9]+(\.[0-9]+)+/:Version: ${arg}/" README.rst
        sed -E "s/__version__ = \"[^\"]+\"/__version__ = \"${arg}\"/" picker/__init__.py
    fi

