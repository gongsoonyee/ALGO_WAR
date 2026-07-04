# ALGO_WAR

ALGO_WAR is a local web prototype where Python search agents compete on an `N x N` grid.
Each agent starts from one random cell, moves one step per turn, and claims empty cells it actually visits.

## Features

- 2 to 4 Python agents per match
- Same agent can be selected more than once
- Default `15 x 15` square board
- Random start positions on every match
- Visited-node territory capture
- Replay animation in the browser
- SQLite storage for agents, matches, ratings, and replay frames
- FastAPI backend with a static browser UI

## How To Run

Open PowerShell in the project folder:

```powershell
cd "$HOME\Desktop\ALGO_WAR"
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the web server:

```powershell
python app.py
```

Open this URL in a browser:

```text
http://127.0.0.1:8000
```

To stop the server, press `Ctrl+C` in the PowerShell window running `python app.py`.

## Current Game Rules

- The board is a square `N x N` grid.
- Each player starts with exactly one owned cell.
- Each turn, an agent returns one move: `UP`, `DOWN`, `LEFT`, or `RIGHT`.
- Moving into an empty cell immediately claims that cell.
- Already-owned cells cannot be stolen.
- Opponent-owned cells cannot be entered.
- If an agent is stuck at its current head position, the engine restarts it from one of its own frontier cells and immediately moves it into an adjacent empty cell.
- The match ends when no empty cells can be reached.
- Winner is decided by the number of claimed cells.

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

The `state` object contains:

- `grid`
- `you`
- `opponent`
- `opponents`
- `turn`
- `max_turns`
- `remaining_turns`
- `scores`
- `valid_moves`

## Built-In Sample Agents

The app seeds these sample agents on first launch:

- Greedy Expander
- Center Hunter
- Safe Looper

## Development Notes

Runtime data is written to `data/algo_war.sqlite3`.
The `data/` folder and Python cache files are ignored by Git.

This is a local educational MVP, not a production sandbox for untrusted code.
