# Search Battle / ALGO_WAR

Search Battle is a local MVP for uploading Python search agents, running 1 vs 1 territory battles, rating agents with ELO, and replaying matches in the browser.

## Features

- Python-only agent submissions
- 1 vs 1 local match engine
- Paper.io-style territory, trail capture, and elimination rules
- SQLite persistence for agents, matches, ratings, and replay frames
- FastAPI backend
- Browser UI for ranking, upload, match launch, and replay

## Requirements
- Python 3.12 or 3.13
- pip

> **Note**
>
> Python **3.12 or 3.13** is required.
> Python **3.14** is not currently supported because some dependencies are not yet compatible.



## Quick Start
### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3.12 -m venv .venv source .venv/bin/activate pip install -r requirements.txt python app.py
```

Then open:

```text
http://127.0.0.1:8000
```
Stop the server with **Ctrl + C**.
## Agent Interface

Upload Python code that exposes either:

```python
def next_move(state):
    return "UP"
```

or:

```python
class Agent:
    def next_move(self, state):
        return "RIGHT"
```

Allowed moves are `UP`, `DOWN`, `LEFT`, and `RIGHT`.

The `state` object contains:

- `grid`
- `you`
- `opponent`
- `turn`
- `max_turns`
- `remaining_turns`
- `scores`
- `valid_moves`

## Built-in Sample Agents

The app seeds three agents on first launch:

- Greedy Expander
- Center Hunter
- Safe Looper

## Notes

This is a local educational MVP. It uses a separate Python process with a timeout for each move, but it is not a production-grade sandbox. Use Docker or a dedicated sandbox runner before accepting untrusted public submissions.
