# NSW Census 2021 Query Agent

An AI agent that answers questions about NSW 2021 census data using Google Cloud BigQuery and the Google ADK.

## Overview

Ask questions in plain English about NSW census demographics. The agent translates them to SQL and returns insights from 8 census tables.

## Datasets

- `g08_ancestry` — Ancestry by suburb/postcode
- `g32_family_income_weekly` — Family weekly income
- `g33_household_income_weekly` — Household weekly income
- `g04_age` — Age by sex
- `g05_marital_status` — Marital status by age/sex
- `g17_personal_income` — Personal weekly income
- `g49_education` — Education level by age/sex
- `g56_occupation` — Employment by occupation

## Example Questions

- "List top 10 suburbs with highest percentage of postgraduate degrees"
- "Show ancestry composition of Artarmon"
- "What's the median household weekly income in postcode 2000?"
- "Which suburbs have highest percentage of high earners (>$3,500/week)?"
- "Show age distribution for Bondi"

## Quick Start

### Install

```bash
git clone https://github.com/wzha8255/census_query_agent.git
cd census_query_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gcloud auth application-default login
```

### Run

```bash
python census_query_agent/agent.py
```

## Configuration

Update project ID in `census_query_agent/agent.py`:

```python
tool_config = BigQueryToolConfig(
    compute_project_id="your-project-id",
    write_mode=WriteMode.BLOCKED
)
```

## Features

- ✅ Natural language to SQL
- ✅ Read-only (write protection)
- ✅ Parameterized queries (SQL injection safe)
- ✅ Aggregated results (percentages, medians, totals)
- ✅ Clear error messages

## Infrastructure

Provision service account:

```bash
cd deployment/terraform/terraform-sa
terraform init && terraform apply
```

Creates `bq-agent` service account with BigQuery + Vertex AI roles.

## Troubleshooting

**Auth fails?**
```bash
gcloud auth application-default login
```

**Table not found?**
```bash
gcloud bq ls census_2021
```

**Query slow?** Add `LIMIT` or filter by suburb/postcode.

## Architecture

User Question → Gemini 2.5 Flash → SQL → BigQuery → Response

## Cost

~$7.50/TB scanned (1TB free/month). Typical queries <$0.01.

## Links

- [ADK Docs](https://developers.google.com/adk)
- [BigQuery](https://cloud.google.com/bigquery/docs)
- [Census 2021](https://www.abs.gov.au/census)

---

**Version**: 1.0 | **Dataset**: Census 2021 | **Updated**: November 2025
