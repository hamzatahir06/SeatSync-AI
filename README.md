
# SeatSync AI

A fully local conversational agent for bus seat booking, with a RAG knowledge base.
Built with Streamlit, Ollama (llama3.2, nomic-embed-text), and ChromaDB. No cloud APIs.

## What it does

- **Understands intent** – an LLM classifies each message (book, check status,
  view history, cancel, support, or a general question), even with typos.
- **Takes actions safely** – booking, lookup, and cancellation run as validated,
  deterministic code. The LLM routes the request; it never writes data itself.
- **Handles multi-turn flows** – asks for missing details like a booking number,
  and lets the user back out ("nvm", "forget it").
- **Answers from documents** – questions outside booking go to a RAG pipeline that
  answers only from the ingested document. `info_about_ai.pdf` is a sample; swap in
  any PDF, DOCX, or TXT.

## Run it

1. Install [Ollama](https://ollama.com), then run `ollama pull llama3.2` and `ollama pull nomic-embed-text`
2. `pip install -r requirements.txt`
3. `python ingest.py` to build the knowledge base
4. `streamlit run app.py`

## Status

A learning prototype built to explore hybrid LLM routing, form-based
state management, and local RAG. Bookings are stored in a local JSON file.
