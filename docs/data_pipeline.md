# Data Pipeline Specification

This document describes the end-to-end data ingestion and transformation flow supporting the experiment.

## 1. Overview

The pipeline comprises modular collectors scheduled via an orchestration framework (e.g., Airflow, Prefect) to ingest heterogeneous data sources on daily, weekly, and monthly cadences. Each collector writes to a staging schema before validation and promotion to the analytics warehouse.

## 2. Pipelines

### 2.1 Market Data Collector

- **Source**: CoinGecko Pro + exchange APIs (Binance, Coinbase, Kraken).
- **Frequency**: Hourly pulls with 5-minute staggering to avoid rate limits.
- **Process**:
  1. Fetch OHLCV data for all assets in experiment universe.
  2. Validate price parity against previous close and alternate exchange snapshots.
  3. Load to `market_data.prices_raw` table.
  4. Run deduplication/quality rules; promote to `market_data.prices_clean`.

### 2.2 LLM Response Collector

- **Source**: PromptRunner module (`src/llmoptimization/llm_queries.py`).
- **Frequency**: Baseline (Week 0) and monthly thereafter.
- **Process**:
  1. Generate standardized prompts from template catalog.
  2. Execute asynchronous API calls respecting provider throttles.
  3. Persist raw responses, metadata, and usage statistics to MongoDB.
  4. Trigger NLP parsing job to extract entities, sentiment, ranking positions.

### 2.3 Documentation Scraper

- **Source**: Official project websites, GitHub repos, whitepapers, Medium blogs.
- **Frequency**: Quarterly with incremental updates on change detection.
- **Process**:
  1. Crawl documentation sitemap; download HTML/PDF assets.
  2. Parse with BeautifulSoup, compute readability, coverage, and update timestamps.
  3. Store normalized metrics in `documentation.metrics` table and raw artifacts in object storage with SHA256 hashes.

### 2.4 Social & Community Metrics

- **Sources**: Reddit, Twitter/X, GitHub, Stack Overflow, Medium.
- **Frequency**: Weekly.
- **Process**:
  1. Query API endpoints for subscriber counts, engagement, repositories, stars, forks.
  2. Normalize via log scaling; compute percentile ranks vs. universe.
  3. Append to `community.engagement` fact table keyed by asset and week.

### 2.5 Developer Activity Tracker

- **Source**: GitHub/GitLab APIs.
- **Frequency**: Weekly.
- **Process**:
  1. Enumerate repositories linked to each asset.
  2. Capture commits, contributors, issues, PRs, and response time metrics.
  3. Weight repositories by primary/language relevance; aggregate per asset.

## 3. Validation & Monitoring

- **Schema Validation**: Enforce column types and nullability via dbt or Great Expectations.
- **Anomaly Detection**: Use control charts for sudden spikes in volume or social metrics.
- **Alerting**: PagerDuty/Slack notifications for pipeline failures or data quality breaches.
- **Audit Trail**: All data loads logged with checksum, record counts, and run metadata.

## 4. Access Patterns

- Analytical queries served via PostgreSQL views optimized for weekly aggregation.
- Machine learning workloads access staged parquet files stored in object storage.
- Sensitive API keys stored in AWS Secrets Manager; rotated quarterly.

## 5. Disaster Recovery

- Daily snapshots of PostgreSQL and MongoDB to S3 with 7-year retention.
- Runbook includes cold-start instructions and infrastructure-as-code scripts (Terraform) to recreate environment within 4 hours.

