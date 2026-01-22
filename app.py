"""
Streamlit Community Cloud entrypoint.
Runs the taxonomy browser and auto-generates taxonomy.json if missing.
"""
from pathlib import Path

import streamlit as st


def ensure_taxonomy():
    taxonomy_path = Path("taxonomy.json")
    if taxonomy_path.exists():
        return

    context_path = Path("context.json")
    if not context_path.exists():
        st.error(
            "taxonomy.json is missing and context.json was not found. "
            "Please commit context.json or generate taxonomy.json locally."
        )
        st.stop()

    try:
        from scripts import build_taxonomy

        build_taxonomy.build_taxonomy()
    except Exception as exc:
        st.error(f"Failed to generate taxonomy.json: {exc}")
        st.stop()


ensure_taxonomy()

from scripts.taxonomy_browser import main

main()
