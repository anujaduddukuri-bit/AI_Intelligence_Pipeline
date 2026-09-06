# AI Intelligence Pipeline

> **Production-oriented AI & Venture Intelligence Ingestion Pipeline**
> Built for large-scale startup, AI product, research paper, news, and job intelligence collection.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Async](https://img.shields.io/badge/Crawling-AsyncIO%20%2B%20aiohttp-green.svg)](https://docs.python.org/3/library/asyncio.html)
[![LLM](https://img.shields.io/badge/LLM-Multi--Tier%20Fallback-purple.svg)](#llm-orchestration)
[![Status](https://img.shields.io/badge/Status-Complete-success.svg)](#validation)

---

## 1. Project Overview

The **AI Intelligence Pipeline** is a scalable data ingestion and intelligence system designed to collect, normalize, validate, enrich, and resolve information from multiple AI and technology sources.

The pipeline combines:

* Asynchronous web crawling
* Structured API/data-source ingestion
* Full-text extraction
* Multi-tier LLM extraction
* Intelligent 413 payload handling
* 429 rate-limit handling with exponential backoff
* Deterministic entity resolution
* Freshness filtering
* Duplicate detection
* GitHub research-paper metrics
* Data-quality validation
* CSV/Google Sheets export

The architecture is designed with **500,000+ records in mind**, while the current implementation successfully produces more than the required minimum datasets.

---

# 2. Objectives

The main objectives are:

1. Collect at least **1,000 unique AI startups**.
2. Collect at least **1,000 AI products/tools**.
3. Collect at least **1,000 research papers** with GitHub metrics.
4. Collect AI-related news published within the **last 24 hours**.
5. Collect AI-related jobs published within the **last 24 hours**.
6. Normalize heterogeneous source data into canonical schemas.
7. Resolve products to their canonical startup/company entities.
8. Prevent hallucinated data through deterministic validation and strict LLM prompts.
9. Handle API failures, rate limits, and oversized requests intelligently.
10. Provide traceable source URLs for collected records.
11. Produce submission-ready datasets and documentation.

---

# 3. System Architecture

```text
                         ┌─────────────────────────┐
                         │     Source Discovery     │
                         └────────────┬────────────┘
                                      │
              ┌───────────────────────┼────────────────────────┐
              │                       │                        │
              ▼                       ▼                        ▼
       Startup Sources         Product Sources          Research Sources
              │                       │                        │
              └───────────────────────┼────────────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Async Crawler Layer   │
                         │     asyncio + aiohttp   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ Raw HTML / JSON / RSS   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │ Text Extraction &       │
                         │ Normalization           │
                         └────────────┬────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
                     ▼                                 ▼
             Deterministic Rules                LLM Extraction
                                                       │
                                      ┌────────────────┼───────────────┐
                                      ▼                ▼               ▼
                                   Gemini            Groq           DeepSeek
                                      │                │               │
                                      └────────────────┼───────────────┘
                                                       │
                                                       ▼
                                           Canonical JSON Records
                                                       │
                                                       ▼
                                         ┌────────────────────────┐
                                         │ Entity Resolution      │
                                         │ + Deduplication        │
                                         └────────────┬───────────┘
                                                      │
                                                      ▼
                                         ┌────────────────────────┐
                                         │ Freshness & Validation  │
                                         └────────────┬───────────┘
                                                      │
                                                      ▼
                                         ┌────────────────────────┐
                                         │ CSV / Google Sheets    │
                                         └────────────────────────┘
```

---

# 4. Pipeline Phases

## Phase I — Massive One-Time Acquisition

The pipeline acquires large datasets from structured and web-based sources.

### Startup acquisition

Primary source:

* Y Combinator AI startup directory

The collector discovers startup profile URLs and passes them to the asynchronous crawler.

Current result:

```text
Startup URLs available: 6200
Unique validated startups: 1028
```

### Product acquisition

Product data is collected from multiple structured AI-tool directories.

Sources include:

* Best of AI structured dataset
* AIFOXX structured tools dataset

Current result:

```text
Final unique products: 1672
```

### Research-paper acquisition

Research papers are collected from arXiv using AI/ML-related categories including:

* cs.AI
* cs.LG
* cs.CL
* cs.CV
* cs.NE
* stat.ML

Current result:

```text
Research papers: 1000
```

GitHub repositories associated with papers are resolved using a combination of:

* Papers With Code mapping data
* GitHub API
* Manual verification for unresolved cases

Each verified paper contains GitHub URL and GitHub star count.

---

# 5. Phase II — Fresh News and Job Intelligence

The pipeline monitors multiple AI news and job sources.

## News Sources

The system monitors five sources:

1. TechCrunch AI
2. VentureBeat AI
3. MIT Technology Review AI
4. The Verge AI
5. Google AI Blog

The crawler:

* Reads RSS/Atom feeds
* Parses publication dates
* Converts dates into normalized timestamps
* Applies a 24-hour freshness cutoff
* Crawls article pages when possible
* Falls back safely to RSS content when full-page crawling is unavailable
* Removes duplicates

Current result:

```text
Fresh AI news: 4
Fresh records: 4
Stale records: 0
Failed records: 0
```

## Job Sources

The system monitors five job sources:

1. Jobicy
2. RemoteFirstJobs AI
3. We Work Remotely
4. AI Jobs in National Security
5. AI Dev Jobs

The pipeline extracts:

* Company
* Job URL
* Date
* Remote status
* Role family

Current result:

```text
AI job candidates: 44
Unique job URLs: 44
Fresh AI jobs: 43
Companies extracted: 43
Companies missing: 0
```

All final job records passed freshness and schema validation.

---

# 6. Phase III — LLM Orchestration

The pipeline uses a multi-tier LLM architecture to reduce dependence on a single provider.

## Provider Chain

```text
Gemini
   │
   │ unavailable / quota / rate limit
   ▼
Groq
   │
   │ unavailable / quota / rate limit
   ▼
DeepSeek
```

### Primary provider

**Google Gemini**

Model:

```text
gemini-3.6-flash
```

### Fallback provider

**Groq**

Model:

```text
openai/gpt-oss-120b
```

### Secondary fallback

**DeepSeek**

Model:

```text
deepseek-chat
```

---

# 7. Strict LLM Extraction

The LLM is instructed to use only information explicitly available in the crawled webpage.

The extraction rules include:

* No guessing
* No invented employee counts
* No inferred startup status from domain names alone
* No hallucinated company information
* Return `null` when information is unavailable
* Return valid JSON only
* Reject unrelated pages

Example canonical startup extraction:

```json
{
  "isStartup": true,
  "entityName": "Example AI",
  "employeeCount": 75
}
```

If the page does not contain sufficient evidence:

```json
{
  "isStartup": false,
  "entityName": null,
  "employeeCount": null
}
```

This approach is particularly important because the assignment explicitly prohibits hallucinated records.

---

# 8. Intelligent 413 Handling

Large webpage inputs can exceed model request limits.

The pipeline therefore applies intelligent text reduction before LLM submission.

Current strategy:

```text
Raw webpage
     │
     ▼
HTML cleanup
     │
     ▼
Text extraction
     │
     ▼
Relevant content selection
     │
     ▼
Input truncation / chunking
     │
     ▼
LLM request
```

The orchestrator limits oversized prompts and prioritizes the relevant webpage content.

This prevents the entire raw webpage from being unnecessarily submitted to the model.

---

# 9. 429 Rate-Limit Handling

The LLM orchestrator detects temporary rate-limit failures and retries using exponential backoff with jitter.

Conceptually:

```text
Request
   │
   ├── Success ───────────────► Continue
   │
   └── 429
        │
        ▼
   Wait + random jitter
        │
        ▼
      Retry
        │
        └── Repeat within retry limit
```

The retry delay increases between attempts.

Permanent failures and daily quota exhaustion are handled differently from temporary rate limits.

Unavailable providers are disabled for the remainder of the process so the pipeline can continue with the remaining providers.

---

# 10. Responsible Web Crawling

The crawler is designed to behave responsibly.

It supports:

* Request timeouts
* Retry handling
* HTTP status handling
* 403 detection
* 429 detection
* Concurrent request limits
* Safe RSS fallback
* Batch processing
* No illegal anti-bot bypass

For Cloudflare, DataDome, JavaScript challenges, or similar protections, the system does **not attempt to bypass security mechanisms**.

Instead, it can:

1. Use a permitted structured/RSS source.
2. Use an available official API.
3. Use cached/source metadata where legitimate.
4. Record the failure.
5. Continue processing other records.

---

# 11. Phase IV — Deterministic Entity Resolution

Products frequently contain vendor/company information that differs from startup names.

The entity-resolution system maps products to canonical startup entities using deterministic evidence.

## Matching hierarchy

| Evidence                     | Confidence |
| ---------------------------- | ---------: |
| Exact domain                 |        100 |
| Registered domain            |         90 |
| Existing company name        |         85 |
| Description/company evidence |         80 |
| Exact product/startup name   |         75 |

A minimum confidence threshold is applied before accepting a mapping.

Ambiguous records remain unresolved rather than being incorrectly assigned.

---

# 12. Entity Resolution Results

Current dataset:

```text
Total products:        1672
Matched:               466
Unresolved:             1206
Resolution rate:       27.87%
Average confidence:    80.94
```

Matching methods:

```text
description_company: 444
exact_domain:          22
```

The system intentionally leaves uncertain mappings unresolved to avoid false relationships.

---

# 13. Freshness Processing

News and jobs must satisfy a strict 24-hour freshness requirement.

The freshness layer:

1. Reads source publication dates.
2. Parses RSS/Atom timestamps.
3. Normalizes time zones.
4. Compares against the current UTC time.
5. Rejects stale records.
6. Keeps only fresh records.

Final validation:

```text
NEWS
Fresh: 4
Stale: 0

JOBS
Fresh: 43
Stale: 0
```

---

# 14. Deduplication

Duplicate records are removed using deterministic keys.

Examples include:

* Startup name
* Startup URL
* Product name + product website
* Research-paper title
* News URL
* Job URL

This prevents duplicate ingestion when multiple sources contain the same entity.

---

# 15. Data Schemas

## Startup Schema

```json
{
  "schemaVersion": "1.0",
  "recordType": "STARTUP",
  "source": {
    "name": "source_name",
    "url": "https://example.com"
  },
  "content": {
    "entityName": "Example AI",
    "data": {
      "employeeCount": 75
    }
  },
  "collectedAt": "2026-09-06T00:00:00Z"
}
```

---

## Product Schema

```json
{
  "schemaVersion": "1.0",
  "recordType": "PRODUCT",
  "source": {
    "name": "source_name",
    "url": "https://example.com"
  },
  "content": {
    "startupName": "Example AI",
    "pricingModel": "FREEMIUM"
  },
  "collectedAt": "2026-09-06T00:00:00Z"
}
```

Allowed pricing models:

```text
FREE
FREEMIUM
PAID
ENTERPRISE
```

---

## Research Paper Schema

```json
{
  "schemaVersion": "1.0",
  "recordType": "RESEARCH_PAPER",
  "title": "Example Research Paper",
  "authors": [
    "Author One",
    "Author Two"
  ],
  "paper_url": "https://arxiv.org/abs/example",
  "github_url": "https://github.com/example/repository",
  "github_stars": 100,
  "published_date": "2026-01-01"
}
```

---

## Job Schema

```json
{
  "schemaVersion": "1.0",
  "recordType": "JOB",
  "company": "Example AI",
  "date": "2026-09-06T10:00:00Z",
  "is_remote": true,
  "role_family": "Machine Learning Engineer"
}
```

---

# 16. Current Dataset Results

| Dataset            |   Records | Status |
| ------------------ | --------: | ------ |
| Startups           | **1,028** | ✅      |
| Products           | **1,672** | ✅      |
| Research Papers    | **1,000** | ✅      |
| Fresh Jobs         |    **43** | ✅      |
| Fresh News         |     **4** | ✅      |
| Entity Mapping Log | **1,672** | ✅      |

The required minimum of 1,000 records has been achieved for:

* Startups
* Products
* Research Papers

---

# 17. Data Validation

A dedicated validation module checks the final datasets.

Validation includes:

### Startups

* Unique startup names
* Duplicate URLs
* Missing names
* URL validity
* Official website availability
* Schema validation

### Products

* Unique products
* Duplicate URLs
* Pricing-model validation
* Product-name validation
* Entity-resolution status

### Research Papers

* Unique titles
* Paper URL validation
* GitHub URL validation
* GitHub stars availability

### News

* Freshness
* Missing titles
* Missing dates
* URL validity
* Duplicate URLs

### Jobs

* Freshness
* Company availability
* Role family availability
* Remote flag availability
* URL validity
* Duplicate URLs

### Entity Resolution

* Mapping completeness
* Confidence
* Matched/unresolved status
* Invalid mappings

---

# 18. Final Validation Result

```text
STARTUP
Total: 1028
Status: PASS

PRODUCT
Total: 1672
Status: PASS

RESEARCH
Total: 1000
Status: PASS

NEWS
Total: 4
Fresh: 4
Status: PASS

JOBS
Total: 43
Fresh: 43
Status: PASS

ENTITY RESOLUTION
Total: 1672
Matched: 466
Unresolved: 1206
Status: PASS

ENTITY MAPPING LOG
Total: 1672
Matched: 466
Unresolved: 1206
Status: PASS

--------------------------------
OVERALL STATUS: PASS
Checks passed: 7/7
--------------------------------
```

---

# 19. Project Structure

```text
AI_Intelligence_Pipeline/
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── pipeline.py
│   ├── validation.py
│   │
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── async_crawler.py
│   │   ├── simple_crawler.py
│   │   ├── startup_sources.py
│   │   ├── startup_crawler.py
│   │   ├── product_collector.py
│   │   ├── product_crawler.py
│   │   ├── product_merger.py
│   │   ├── product_source2_collector.py
│   │   ├── research_paper_collector.py
│   │   ├── github_metrics.py
│   │   ├── github_match_diagnostic.py
│   │   ├── fix_two_papers.py
│   │   ├── news_sources.py
│   │   ├── news_crawler.py
│   │   ├── job_sources.py
│   │   └── job_crawler.py
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── text_extractor.py
│   │   └── json_converter.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_orchestrator.py
│   │   ├── startup_extractor.py
│   │   ├── gemini_test.py
│   │   ├── groq_test.py
│   │   ├── deepseek_test.py
│   │   └── test_gemini.py
│   │
│   ├── entity_resolution/
│   │   ├── __init__.py
│   │   ├── resolver.py
│   │   ├── enrich_startups.py
│   │   └── diagnose.py
│   │
│   ├── freshness/
│   │   └── __init__.py
│   │
│   ├── database/
│   │   └── __init__.py
│   │
│   └── export/
│       └── export_to_csv.py
│
├── data/
│   ├── raw/
│   └── processed/
│       └── export/
│
├── tests/
│
├── architecture.pdf
├── requirements.txt
├── .gitignore
├── .env
└── README.md
```

> **Note:** `.env` and other secret/temporary files are excluded from version control through `.gitignore`.

---

# 20. Installation

Clone the repository:

```bash
git clone https://github.com/anujaduddukuri-bit/AI_Intelligence_Pipeline.git
cd AI_Intelligence_Pipeline
```

Create a virtual environment:

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 21. Environment Variables

Create a local `.env` file:

```text
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
GITHUB_TOKEN=your_token
```

**Never commit `.env` to GitHub.**

The `.gitignore` configuration excludes it from version control.

---

# 22. Running the Pipeline

### Test asynchronous crawler

```bash
python -m src.crawler.async_crawler
```

### Collect startup sources

```bash
python -m src.crawler.startup_sources
```

### Crawl startups

```bash
python -m src.crawler.startup_crawler
```

### Collect products

```bash
python -m src.crawler.product_collector
```

### Crawl products

```bash
python -m src.crawler.product_crawler
```

### Merge product sources

```bash
python -m src.crawler.product_merger
```

### Collect research papers

```bash
python -m src.crawler.research_paper_collector
```

### Collect GitHub metrics

```bash
python -m src.crawler.github_metrics
```

### Crawl news

```bash
python -m src.crawler.news_crawler
```

### Crawl jobs

```bash
python -m src.crawler.job_crawler
```

### Resolve entities

```bash
python -m src.entity_resolution.enrich_startups
python -m src.entity_resolution.resolver
```

### Validate datasets

```bash
python -m src.validation
```

### Export datasets

```bash
python -m src.export.export_to_csv
```

---

# 23. Submission Data

The final datasets are exported as CSV files:

```text
data/processed/export/
│
├── Startups.csv
├── Products.csv
├── Research_Papers.csv
├── Jobs.csv
├── News.csv
└── Entity_Mapping_Log.csv
```

These datasets were uploaded into a public Google Sheet with six tabs:

1. **Startups**
2. **Products**
3. **Research Papers**
4. **Jobs**
5. **News**
6. **Entity Mapping Log**

### Public Google Sheet

https://docs.google.com/spreadsheets/d/153rhpk9LOP34jFSRqpQ4Bg30vzVwiKyvCIDjkjPvvLQ/edit?usp=sharing
```

---

# 24. Scalability — 500,000+ Records

The architecture is designed so that scaling the dataset does not require rewriting the core pipeline.

## Current approach

```text
Source URLs
     │
     ▼
Async task queue
     │
     ├── Batch 1
     ├── Batch 2
     ├── Batch 3
     ├── ...
     └── Batch N
```

The crawler uses:

* `asyncio`
* `aiohttp`
* Concurrent requests
* Bounded concurrency
* Batch processing
* Retry logic
* Checkpointing
* Incremental processing

## Production-scale evolution

For 500,000+ records, the architecture can be extended with:

```text
                  ┌─────────────────┐
                  │ Source Registry │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Message Queue   │
                  │ Kafka / SQS     │
                  └────────┬────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Worker 1      Worker 2     Worker N
              │            │            │
              └────────────┼────────────┘
                           ▼
                   Processing Layer
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          SQL DB       Vector DB      Graph DB
```

This enables horizontal scaling by adding crawler workers rather than changing the crawler logic.

---

# 25. Distributed Freshness and Duplicate Processing

At production scale, multiple crawler nodes may process the same URLs.

The system can use:

* Stable URL hashes
* Content hashes
* Idempotency keys
* Distributed locks
* Queue-level deduplication
* Processing timestamps
* Source-level checkpoints

Example:

```text
URL
 │
 ▼
SHA-256 / canonical URL hash
 │
 ▼
Idempotency check
 │
 ├── Already processed → Skip
 │
 └── New → Process
```

This prevents multiple workers from unnecessarily processing identical records.

---

# 26. Storage Architecture

A production deployment can use multiple storage layers.

## Relational Database

Suitable for:

* Startups
* Products
* Jobs
* News
* Research metadata
* Entity mappings

Examples:

* PostgreSQL
* MySQL

## Vector Database

Suitable for:

* Semantic search
* Similar startup discovery
* Similar product discovery
* Research-paper similarity
* News clustering

Possible technologies:

* pgvector
* Qdrant
* Weaviate

## Graph Database

Suitable for relationships such as:

```text
Startup
   │
   ├── develops → Product
   │
   ├── publishes → Research
   │
   ├── hires → Job
   │
   └── mentioned_in → News
```

Possible technology:

* Neo4j

---

# 27. Error Handling

The pipeline distinguishes between different failure classes.

### Temporary errors

Examples:

```text
429
Timeout
Connection reset
Temporary server failure
```

Action:

```text
Retry → Backoff → Retry
```

### Permanent errors

Examples:

```text
404
Invalid URL
Invalid response
Unsupported content
```

Action:

```text
Record failure → Continue
```

### Provider quota exhaustion

Action:

```text
Disable unavailable provider
       ↓
Try next provider
       ↓
Continue pipeline
```

This prevents a single API provider from stopping the complete ingestion process.

---

# 28. Data Quality Principles

The project follows several important principles.

### 1. Traceability

Every important record should have a legitimate source URL.

### 2. No hallucination

Missing information is represented as `null` rather than guessed.

### 3. Deterministic resolution

Entity matching uses explainable evidence rather than arbitrary LLM decisions.

### 4. Freshness

Time-sensitive data is filtered according to the required 24-hour window.

### 5. Deduplication

Repeated entities and URLs are removed.

### 6. Validation

All final datasets pass schema and quality checks.

### 7. Graceful failure

A single unavailable source or provider does not stop the entire pipeline.

---

# 29. Responsible Use of AI

LLMs are used primarily for **information extraction and normalization**, not for generating missing facts.

The pipeline architecture intentionally separates:

```text
Web evidence
     │
     ▼
Extraction
     │
     ▼
LLM interpretation
     │
     ▼
Deterministic validation
     │
     ▼
Canonical record
```

This reduces the risk of fabricated information entering the final dataset.

---

# 30. Assignment Requirements Coverage

| Requirement                              | Implementation |
| ---------------------------------------- | -------------- |
| 1,000+ startups                          | ✅ 1,028        |
| 1,000+ products                          | ✅ 1,672        |
| 1,000+ research papers                   | ✅ 1,000        |
| GitHub stars                             | ✅              |
| 5 AI news sources                        | ✅              |
| 5 AI job sources                         | ✅              |
| 24-hour freshness                        | ✅              |
| Full-text crawling                       | ✅              |
| Async crawling                           | ✅              |
| `asyncio` + `aiohttp`                    | ✅              |
| LLM extraction                           | ✅              |
| Gemini → Groq → DeepSeek                 | ✅              |
| 413 handling                             | ✅              |
| 429 handling                             | ✅              |
| Exponential backoff                      | ✅              |
| Deterministic entity resolution          | ✅              |
| Duplicate handling                       | ✅              |
| Cloudflare/DataDome responsible handling | ✅              |
| 500k+ scalability design                 | ✅              |
| Distributed processing design            | ✅              |
| DB + vector/graph storage design         | ✅              |
| Google Sheets export                     | ✅              |
| Architecture document                    | ✅              |
| Validation                               | ✅ 7/7 PASS     |

---

# 31. Final Project Statistics

```text
========================================
AI INTELLIGENCE PIPELINE
========================================

Startups                  1,028
Products                  1,672
Research Papers           1,000
Fresh AI Jobs                43
Fresh AI News                 4
Entity Mappings            1,672

Matched Products             466
Unresolved Products        1,206

Validation Checks              7
Checks Passed                   7

Overall Status               PASS
========================================
```

---

# 32. Architecture Documentation

The project includes a dedicated architecture document covering:

* System architecture
* Data flow
* 500k+ scalability
* Async crawling
* LLM orchestration
* 413 handling
* 429 handling
* Distributed freshness
* Duplicate processing
* Database architecture
* Vector/graph storage
* Entity resolution
* Responsible crawling

File:

```text
architecture.pdf
```

---

# 33. Repository

GitHub repository:

https://github.com/anujaduddukuri-bit/AI_Intelligence_Pipeline

---

# 34. Future Improvements

Potential production enhancements include:

* Kafka/SQS-based distributed task queues
* PostgreSQL persistence
* Redis caching
* Distributed locking
* Celery/Temporal orchestration
* Playwright for permitted JavaScript-rendered pages
* Advanced proxy rotation where legally permitted
* Content hashing
* Vector embeddings
* Semantic entity matching
* Neo4j knowledge graph
* Prometheus/Grafana monitoring
* Structured logging
* Automated scheduled ingestion
* Data lineage tracking
* Automated source health monitoring
* CI/CD pipeline
* Unit and integration test expansion

---

# 35. Conclusion

The **AI Intelligence Pipeline** demonstrates an end-to-end approach to large-scale AI and venture intelligence collection.

The implementation combines asynchronous crawling, structured ingestion, strict LLM extraction, intelligent failure handling, deterministic entity resolution, freshness filtering, deduplication, validation, and scalable architecture.

The current implementation successfully meets the core dataset requirements:

```text
1,028 Startups
1,672 Products
1,000 Research Papers
43 Fresh Jobs
4 Fresh News Records
1,672 Entity Mapping Records
7/7 Validation Checks Passed
```

The architecture is designed to evolve from the current dataset into a distributed **500,000+ record intelligence platform** without requiring a fundamental rewrite of the ingestion pipeline.

---

## Author

**DUDDUKURI ANUJA**

B.Tech Student | AI/ML & Data Engineering

---

## License

This project was developed as an engineering assessment / academic project.

Third-party datasets, APIs, websites, and source content remain subject to their respective licenses and terms of use.

