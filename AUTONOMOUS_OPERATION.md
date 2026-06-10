# WorldQuant Autonomous Alpha Pipeline

**Complete local implementation. No manual intervention required except cookie updates.**

## Quick Start

```bash
python run_pipeline.py
```

## System Features

### 1. **Full Autonomy**
- Run `python run_pipeline.py` to execute the complete workflow:
  1. Generate candidate alphas
  2. Submit to WorldQuant for simulation
  3. Poll results
  4. Generate analytics
  5. Update Excel dashboards

### 2. **Centralized Authentication**
- Cookie stored in `config.json`
- Automatically validates on startup
- Prompts for update if expired
- Set `WQB_COOKIE` environment variable to bypass prompts

### 3. **Dynamic Database Schema**
- Automatically captures **all** API fields
- New metrics added dynamically - no hardcoding
- Schema expands as API returns new data

### 4. **Comprehensive Excel Dashboard**

Single file: `project/reports/alpha_history.xlsx`

Sheets:
- **All Results** - Every alpha tested with all metrics
- **Elite Results** - Sharpe ≥ 1.0, Fitness ≥ 0.8
- **Best Settings** - Top performing parameter combinations
- **Best Fields** - Most frequently used fields
- **Best Operators** - Most frequently used operators
- **Top 10 Daily** - Highest predicted alphas
- **Simulation Budget** - Usage summary
- **Family Summary** - Success rates by category

### 5. **Simulation Budget Management**
- Budget: 1500 simulations per session
- Allocation: 60% proven, 25% promising, 15% exploration
- Automatically selects candidates within budget

### 6. **Settings Learning**
- Tracks success of settings combinations
- Recommends best settings per category
- Dynamic optimization based on results

## Configuration

### Setup Cookie

**Option 1: Interactive Prompt**
On first run, you'll be prompted to paste your WorldQuant authentication cookie.

**Option 2: config.json**
Edit `config.json`:
```json
{
  "cookie": "your_token_here",
  "api_base": "https://api.worldquantbrain.com"
}
```

**Option 3: Environment Variable**
```bash
set WQB_COOKIE=your_token_here
python run_pipeline.py
```

### Adjust Settings (project/config.py)

```python
SIMULATION_BUDGET = 1500  # Total simulations per run
BUDGET_ALLOCATION = {
    "proven": 0.6,      # 60% on proven categories
    "promising": 0.25,  # 25% on emerging categories
    "exploration": 0.15 # 15% on new ideas
}
```

## Output Files

**Database**: `project/data/results.db`
- All alphas, simulations, and metrics

**Daily Report**: `project/reports/daily_report_summary.txt`
- Session summary and statistics

**Excel Dashboard**: `project/reports/alpha_history.xlsx`
- 8-sheet workbook with all analytics

**Elite Alphas**: `project/reports/elite_alphas.csv`
- High-performing alphas for submission

**Daily Top 10**: `daily_top10.txt`
- Today's best candidates

## Command-Line Options

```bash
# Full workflow (default)
python run_pipeline.py

# Skip submission (generate and poll only)
python run_pipeline.py --no-submit

# Skip polling (generate and submit only)
python run_pipeline.py --no-poll

# Dry run (generate candidates only, no API calls)
python run_pipeline.py --dry-run

# Limit submissions
python run_pipeline.py --submit-limit 10
```

## How It Works

### Generation Phase
1. Load field catalog from datasets
2. Apply learning from previous sessions
3. Generate 250 candidates per session
4. Score based on predicted metrics
5. Filter duplicates and near-duplicates

### Submission Phase
1. Prioritize under budget constraints
2. Select best settings per category
3. Submit to WorldQuant API
4. Track simulation IDs in database

### Polling Phase
1. Monitor simulation status
2. Fetch completed results
3. Extract **all** metrics from API
4. Dynamically add new columns to database
5. Update learning engine

### Reporting Phase
1. Export all results to Excel
2. Generate analytics sheets
3. Update daily top 10
4. Write summary report

## Key Components

- **`project/auth.py`** - Centralized authentication
- **`project/config.py`** - Configuration and settings
- **`project/engine/data_manager.py`** - Dynamic database management
- **`project/engine/learning_engine.py`** - Settings and field learning
- **`project/engine/generator_engine.py`** - Alpha generation
- **`project/worldquant/submit.py`** - API submission with auth handling
- **`project/worldquant/poll.py`** - Dynamic result polling
- **`project/reports/summary.py`** - Excel and CSV export
- **`run_pipeline.py`** - Main orchestration script

## Metrics Captured

The system dynamically captures all metrics returned by the WorldQuant API:
- sharpe, fitness, turnover, returns, margin
- Any additional metrics are automatically added as new columns

No hardcoding. If the API adds new metrics, they appear in your Excel automatically.

## Troubleshooting

**"No WorldQuant cookie found"**
→ Set WQB_COOKIE or add cookie to config.json

**"Authentication failed"**
→ Your cookie expired. Run the pipeline again and enter a new one, or update config.json

**"No remaining simulation budget"**
→ You've used all 1500 simulations. The system will wait until next session.

**New column appeared in Excel but not labeled**
→ Restart the pipeline. New metrics from API are automatically added.

## Performance

- **Generation**: ~50 candidates/second
- **Submission**: ~1 per second (rate limited by API)
- **Polling**: 10-second intervals
- **Full pipeline**: 5-30 minutes depending on submission count

## Local-Only Execution

✅ No cloud dependencies
✅ No manual code generation
✅ No return to Codex needed
✅ Fully self-contained
✅ Cookie update is the only manual action required
