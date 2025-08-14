#!/bin/bash

export PROJECT_PATH="$(pwd)/src"
export PYTHONPATH="$PROJECT_PATH:$PYTHONPATH"
source ./.venv/bin/activate
mkdir -p "logs"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$(pwd)/.venv/lib/python3.9/site-packages/torch/lib"
uv run --project $PROJECT_PATH --active ./src/pipeline/server.py
