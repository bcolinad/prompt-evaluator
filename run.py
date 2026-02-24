"""Bootstrap: patch LangChain import paths for Chainlit cache compatibility.

Chainlit's ``cache.py`` imports ``SQLiteCache`` from ``langchain.cache`` and
``set_llm_cache`` from ``langchain.globals``.  These submodules no longer exist
in the slim ``langchain >= 1.0`` package — they moved to
``langchain-community`` and ``langchain-core`` respectively.

This script registers the new locations under the old module names so that
Chainlit's ``init_lc_cache()`` (which runs before ``src/app.py`` is loaded)
finds them without error.

Usage (via Makefile ``make dev``)::

    uv run python run.py run src/app.py
"""

import sys
from langchain_community import cache as _community_cache
from langchain_core import globals as _core_globals

sys.modules["langchain.cache"] = _community_cache
sys.modules["langchain.globals"] = _core_globals

from chainlit.cli import cli

cli()
