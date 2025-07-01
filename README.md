# PaperPilot

Local-first research paper intelligence platform built in Python.

## Overview

PaperPilot ingests academic papers (PDF, arXiv, BibTeX), extracts structured knowledge, and provides a workbench for literature review, citation analysis, and question answering across your personal paper library. Everything runs locally without cloud API keys.

## Architecture

```
paperpilot/
├── api/           FastAPI routes and app factory
├── core/          Config, database, shared models
├── ingestion/     PDF and metadata ingestion pipeline
├── parsers/       Section extraction and layout parsing
├── embeddings/    Local embedding generation and FAISS index
├── search/        Semantic and hybrid search
├── rag/           Multi-paper question answering via Ollama
├── citations/     Citation graph construction
├── topics/        Topic clustering and trend detection
├── review/        Literature review generation
└── dashboard/     Jinja web UI
```

## Local setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
paperpilot
```

Server listens on `http://localhost:8800`.

## Stack

- Python 3.12+, FastAPI, SQLAlchemy
- sentence-transformers, FAISS, networkx
- Ollama for local LLM inference
- SQLite for metadata, DuckDB for analytics
- pytest, ruff, mypy

## License

MIT
