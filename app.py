from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from engine.elo import update_ratings
from engine.game import GameConfig, run_battle
from engine.storage import init_db, seed_agents

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "algo_war.sqlite3"

app = FastAPI(title="ALGO_WAR Search Battle", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    author: str = Field(default="anonymous", min_length=1, max_length=80)
    code: str = Field(min_length=10, max_length=20000)


class MatchCreate(BaseModel):
    agent_ids: list[int] | None = None
    agent_a_id: int | None = None
    agent_b_id: int | None = None
    size: int = Field(default=15, ge=12, le=48)
    max_turns: int | None = Field(default=None, ge=40, le=50000)


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)
    seed_agents(DB_PATH)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/agents")
def list_agents() -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT id, name, author, rating, wins, losses, draws, created_at
            FROM agents
            ORDER BY rating DESC, wins DESC, name
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/agents")
def create_agent(payload: AgentCreate) -> dict[str, Any]:
    with db() as con:
        cur = con.execute(
            """
            INSERT INTO agents(name, author, code, rating, wins, losses, draws)
            VALUES (?, ?, ?, 1000, 0, 0, 0)
            """,
            (payload.name.strip(), payload.author.strip(), payload.code),
        )
        agent_id = cur.lastrowid
    return {"id": agent_id, "message": "agent uploaded"}


@app.get("/api/leaderboard")
def leaderboard() -> list[dict[str, Any]]:
    return list_agents()


@app.get("/api/matches")
def list_matches() -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT id, agent_a_id, agent_b_id, winner_agent_id, reason, turns,
                   score_a, score_b, replay_json, created_at
            FROM matches
            ORDER BY id DESC
            LIMIT 30
            """
        ).fetchall()

    matches = []
    for row in rows:
        item = dict(row)
        replay = json.loads(item.pop("replay_json"))
        participants = replay.get("participants") or legacy_participants(replay, item)
        scores = replay.get("frames", [{}])[-1].get("scores", {"A": item["score_a"], "B": item["score_b"]})
        item["participants"] = participants
        item["agent_names"] = " vs ".join(p["name"] for p in participants)
        item["scores"] = scores
        matches.append(item)
    return matches


@app.post("/api/matches")
def create_match(payload: MatchCreate) -> dict[str, Any]:
    agent_ids = normalize_agent_ids(payload)
    lookup_ids = list(dict.fromkeys(agent_ids))
    placeholders = ",".join("?" for _ in lookup_ids)
    with db() as con:
        agents = con.execute(
            f"SELECT id, name, code, rating FROM agents WHERE id IN ({placeholders})",
            lookup_ids,
        ).fetchall()
    if len(agents) != len(lookup_ids):
        raise HTTPException(status_code=404, detail="All selected agents must exist")

    by_id = {row["id"]: dict(row) for row in agents}
    ordered_agents = [by_id[agent_id] for agent_id in agent_ids]
    safety_turns = payload.max_turns or payload.size * payload.size * 8
    result = run_battle(ordered_agents, GameConfig(size=payload.size, max_turns=safety_turns))
    new_ratings = multiplayer_ratings(ordered_agents, result.scores)

    with db() as con:
        cur = con.execute(
            """
            INSERT INTO matches(
                agent_a_id, agent_b_id, winner_agent_id, reason, turns,
                score_a, score_b, replay_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_ids[0],
                agent_ids[1],
                result.winner_agent_id,
                result.reason,
                result.turns,
                result.score_a,
                result.score_b,
                json.dumps(result.replay, ensure_ascii=False),
            ),
        )
        for agent_id, rating in new_ratings.items():
            con.execute("UPDATE agents SET rating = ? WHERE id = ?", (rating, agent_id))
        if result.winner_agent_id is None:
            con.executemany("UPDATE agents SET draws = draws + 1 WHERE id = ?", [(agent_id,) for agent_id in lookup_ids])
        else:
            con.execute("UPDATE agents SET wins = wins + 1 WHERE id = ?", (result.winner_agent_id,))
            loser_rows = [(agent_id,) for agent_id in lookup_ids if agent_id != result.winner_agent_id]
            con.executemany("UPDATE agents SET losses = losses + 1 WHERE id = ?", loser_rows)
        match_id = cur.lastrowid

    return {"id": match_id, **result.summary(), "ratings": new_ratings}


@app.get("/api/matches/{match_id}")
def get_match(match_id: int) -> dict[str, Any]:
    with db() as con:
        row = con.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Match not found")
    data = dict(row)
    data["replay"] = json.loads(data.pop("replay_json"))
    participants = data["replay"].get("participants") or legacy_participants(data["replay"], data)
    data["participants"] = participants
    data["agent_names"] = " vs ".join(p["name"] for p in participants)
    return data


def normalize_agent_ids(payload: MatchCreate) -> list[int]:
    agent_ids = payload.agent_ids
    if agent_ids is None:
        if payload.agent_a_id is None or payload.agent_b_id is None:
            raise HTTPException(status_code=422, detail="Select 2 to 4 agents")
        agent_ids = [payload.agent_a_id, payload.agent_b_id]
    clean = [agent_id for agent_id in agent_ids if agent_id is not None]
    if not 2 <= len(clean) <= 4:
        raise HTTPException(status_code=422, detail="Select 2 to 4 agents")
    return clean


def multiplayer_ratings(agents: list[dict[str, Any]], scores: dict[str, int]) -> dict[int, int]:
    ratings = {agent["id"]: agent["rating"] for agent in agents}
    labels = ["A", "B", "C", "D"][: len(agents)]
    for i, agent_i in enumerate(agents):
        for j, agent_j in enumerate(agents):
            if j <= i:
                continue
            score_i = scores.get(labels[i], 0)
            score_j = scores.get(labels[j], 0)
            outcome_i = 0.5
            if score_i > score_j:
                outcome_i = 1.0
            elif score_i < score_j:
                outcome_i = 0.0
            new_i, new_j = update_ratings(ratings[agent_i["id"]], ratings[agent_j["id"]], outcome_i, k=12)
            ratings[agent_i["id"]] = new_i
            ratings[agent_j["id"]] = new_j
    return ratings


def legacy_participants(replay: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    agent_a = replay.get("agent_a", {"id": row["agent_a_id"], "name": "Agent A"})
    agent_b = replay.get("agent_b", {"id": row["agent_b_id"], "name": "Agent B"})
    return [
        {"id": agent_a["id"], "name": agent_a["name"], "label": "A"},
        {"id": agent_b["id"], "name": agent_b["name"], "label": "B"},
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
