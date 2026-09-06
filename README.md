# AI Intelligence Pipeline

A modular Python project for building an AI-powered intelligence pipeline.

## Project Structure

- `src/crawler/` - Web/data crawling
- `src/extraction/` - Data extraction and preprocessing
- `src/llm/` - LLM integration
- `src/entity_resolution/` - Entity matching and resolution
- `src/freshness/` - Data freshness checks
- `src/database/` - Database operations
- `src/export/` - Exporting processed results
- `data/raw/` - Raw input data
- `data/processed/` - Processed data
- `tests/` - Tests

## Setup

```bash
python -m venv venv
```

Activate the virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python -m src.main
```
