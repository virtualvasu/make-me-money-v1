# config/queries.py
# All query definitions live in config/queries.json.
# Add new queries there without touching any other file.
# Run with: python main.py --query momentum_breakout

import json
import os

_queries_path = os.path.join(os.path.dirname(__file__), "queries.json")

with open(_queries_path, "r") as _f:
    QUERIES = json.load(_f)
