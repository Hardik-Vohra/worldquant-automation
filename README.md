# WorldQuant Alpha Research Automation

Automated quantitative research pipeline built for WorldQuant Brain.

## Overview

This project automates the end-to-end alpha research workflow:

- Dataset discovery and field extraction
- Dataset catalog generation
- Alpha generation using financial and alternative data
- Batch simulation submission
- Automated simulation monitoring
- Result collection and enrichment
- Performance-based alpha mutation
- Iterative alpha research and optimization

## Features

### Dataset Engine
- Download and catalog data fields from multiple WorldQuant datasets
- Store dataset metadata in structured CSV format
- Support for Analyst Estimates, Fundamentals, News, Sentiment, Options, Risk Models, and more

### Alpha Generation
- Ratio-based alpha generation
- Rank spread alphas
- Z-score spread alphas
- Momentum-based signals
- Automatic parameter variation

### Simulation Pipeline
- Automated batch submission
- Rate-limit handling
- Simulation tracking
- Result polling and collection

### Research Automation
- Sharpe-based alpha filtering
- Winner mutation engine
- Loser inversion logic
- Next-generation alpha creation

## Project Structure

```text
dataset_downloader.py    -> Dataset extraction
generator_v*.py          -> Alpha generation engines
submit_batch.py          -> Simulation submission
poll_results.py          -> Simulation polling
field_selector.py        -> Field selection
field_ranker.py          -> Field ranking
merge_datasets.py        -> Dataset aggregation
generate_next_batch.py   -> Alpha evolution
```

## Technologies

- Python
- Pandas
- Requests
- WorldQuant Brain API

## Research Workflow

1. Download datasets
2. Generate candidate alphas
3. Submit simulations
4. Collect results
5. Rank performance
6. Generate improved candidates
7. Repeat research cycle

## Disclaimer

This repository is intended for educational and research purposes. No proprietary credentials, cookies, or authentication tokens are included.
