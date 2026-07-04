from __future__ import annotations

import sqlite3
from pathlib import Path

SAMPLES = [
    (
        "Greedy Expander",
        "system",
        '''
def next_move(state):
    x, y = state["you"]["x"], state["you"]["y"]
    label = state["you"]["label"]
    grid = state["grid"]
    moves = [("RIGHT", 1, 0), ("DOWN", 0, 1), ("LEFT", -1, 0), ("UP", 0, -1)]

    def bfs(target, owned_only):
        queue = [(x, y, None)]
        seen = {(x, y)}
        head = 0
        while head < len(queue):
            cx, cy, first = queue[head]
            head += 1
            for move, dx, dy in moves:
                nx, ny = cx + dx, cy + dy
                if ny < 0 or nx < 0 or ny >= len(grid) or nx >= len(grid[0]):
                    continue
                cell = grid[ny][nx]
                if (nx, ny) in seen or cell == label.lower() or cell not in (".", label):
                    continue
                step = move if first is None else first
                if target(cell):
                    return step
                if not owned_only or cell == label:
                    seen.add((nx, ny))
                    queue.append((nx, ny, step))
        return None

    return bfs(lambda cell: cell == ".", True) or "UP"
''',
    ),
    (
        "Center Hunter",
        "system",
        '''
def next_move(state):
    x, y = state["you"]["x"], state["you"]["y"]
    grid = state["grid"]
    width = len(grid[0])
    height = len(grid)
    target_x = width // 2
    target_y = height // 2
    choices = []
    for move, dx, dy in [("RIGHT",1,0),("LEFT",-1,0),("DOWN",0,1),("UP",0,-1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] not in ("a", "b"):
            dist = abs(target_x - nx) + abs(target_y - ny)
            choices.append((dist, move))
    choices.sort()
    return choices[0][1] if choices else "UP"
''',
    ),
    (
        "Safe Looper",
        "system",
        '''
class Agent:
    def next_move(self, state):
        phase = state["turn"] % 24
        if phase < 6:
            return "RIGHT"
        if phase < 12:
            return "DOWN"
        if phase < 18:
            return "LEFT"
        return "UP"
''',
    ),
]


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                author TEXT NOT NULL,
                code TEXT NOT NULL,
                rating INTEGER NOT NULL DEFAULT 1000,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_a_id INTEGER NOT NULL,
                agent_b_id INTEGER NOT NULL,
                winner_agent_id INTEGER,
                reason TEXT NOT NULL,
                turns INTEGER NOT NULL,
                score_a INTEGER NOT NULL,
                score_b INTEGER NOT NULL,
                replay_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_a_id) REFERENCES agents(id),
                FOREIGN KEY(agent_b_id) REFERENCES agents(id)
            )
            """
        )


def seed_agents(path: Path) -> None:
    with sqlite3.connect(path) as con:
        for name, author, code in SAMPLES:
            row = con.execute("SELECT id FROM agents WHERE name = ? AND author = ?", (name, author)).fetchone()
            if row:
                con.execute("UPDATE agents SET code = ? WHERE id = ?", (code, row[0]))
            else:
                con.execute(
                    """
                    INSERT INTO agents(name, author, code, rating, wins, losses, draws)
                    VALUES (?, ?, ?, 1000, 0, 0, 0)
                    """,
                    (name, author, code),
                )
