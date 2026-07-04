from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from .runner import LocalAgentRuntime

LABELS = ["A", "B", "C", "D"]
MOVES = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


@dataclass(frozen=True)
class GameConfig:
    size: int = 24
    max_turns: int = 4608
    seed: int | None = None

    @property
    def width(self) -> int:
        return self.size

    @property
    def height(self) -> int:
        return self.size


@dataclass
class Player:
    agent_id: int
    name: str
    label: str
    x: int
    y: int
    alive: bool = True


@dataclass
class MatchResult:
    winner_agent_id: int | None
    winner_label: str | None
    reason: str
    turns: int
    scores: dict[str, int]
    replay: dict[str, Any]

    @property
    def score_a(self) -> int:
        return self.scores.get("A", 0)

    @property
    def score_b(self) -> int:
        return self.scores.get("B", 0)

    def summary(self) -> dict[str, Any]:
        return {
            "winner_agent_id": self.winner_agent_id,
            "winner_label": self.winner_label,
            "reason": self.reason,
            "turns": self.turns,
            "scores": self.scores,
            "score_a": self.score_a,
            "score_b": self.score_b,
        }


def run_match(agent_a: dict[str, Any], agent_b: dict[str, Any], config: GameConfig) -> MatchResult:
    return run_battle([agent_a, agent_b], config)


def run_battle(agents: list[dict[str, Any]], config: GameConfig) -> MatchResult:
    if not 2 <= len(agents) <= 4:
        raise ValueError("run_battle requires 2 to 4 agents")

    owner = [["." for _ in range(config.width)] for _ in range(config.height)]
    trail = [["." for _ in range(config.width)] for _ in range(config.height)]
    rng = random.Random(config.seed)
    starts = random_start_positions(config, len(agents), rng)
    start_positions = {
        LABELS[index]: {"x": starts[index][0], "y": starts[index][1]}
        for index in range(len(agents))
    }

    players = [
        Player(
            agent_id=agent["id"],
            name=agent["name"],
            label=LABELS[index],
            x=starts[index][0],
            y=starts[index][1],
        )
        for index, agent in enumerate(agents)
    ]
    runtimes = {player.label: LocalAgentRuntime(agents[index]["code"]) for index, player in enumerate(players)}

    for player in players:
        seed_base(owner, player.x, player.y, player.label)

    frames: list[dict[str, Any]] = []
    reason = "all stopped"
    idle_turns = {player.label: 0 for player in players}
    previous_scores = {player.label: count_cells(owner, player.label) for player in players}
    idle_limit = config.size * 4

    for turn in range(config.max_turns + 1):
        for player in players:
            if not player.alive and relocate_to_frontier(config, owner, trail, player, rng):
                player.alive = True
            if player.alive and not has_legal_move(config, owner, trail, player):
                relocate_to_frontier(config, owner, trail, player, rng)
        if not any(player.alive for player in players):
            frames.append(frame(config, owner, trail, players, turn))
            reason = "all stopped"
            break

        frames.append(frame(config, owner, trail, players, turn))
        if turn == config.max_turns:
            reason = "safety limit"
            break

        moves = {
            player.label: runtimes[player.label].move(public_state(config, owner, trail, player, players, turn))
            for player in players
            if player.alive
        }
        for player in players:
            if player.alive:
                step_player(config, owner, trail, player, players, moves.get(player.label, "UP"), rng)
        resolve_head_collisions(players)
        update_idle_players(config, owner, trail, players, previous_scores, idle_turns, idle_limit, rng)

    scores = {player.label: count_cells(owner, player.label) for player in players}
    winner = decide_winner(players, scores)
    return MatchResult(
        winner_agent_id=winner.agent_id if winner else None,
        winner_label=winner.label if winner else None,
        reason=reason,
        turns=len(frames) - 1,
        scores=scores,
        replay={
            "width": config.width,
            "height": config.height,
            "size": config.size,
            "max_turns": config.max_turns,
            "participants": [
                {"id": player.agent_id, "name": player.name, "label": player.label}
                for player in players
            ],
            "start_positions": start_positions,
            "frames": frames,
        },
    )


def seed_base(owner: list[list[str]], x: int, y: int, label: str) -> None:
    owner[y][x] = label


def can_move(config: GameConfig, trail: list[list[str]], player: Player) -> bool:
    # Kept for older callers; legal movement needs owner data and is handled by has_legal_move.
    for dx, dy in MOVES.values():
        nx, ny = player.x + dx, player.y + dy
        if 0 <= nx < config.width and 0 <= ny < config.height and trail[ny][nx] != player.label:
            return True
    return False


def has_legal_move(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
) -> bool:
    return bool(legal_moves(config, owner, trail, player))


def legal_moves(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
) -> list[str]:
    moves = []
    for move, (dx, dy) in MOVES.items():
        nx, ny = player.x + dx, player.y + dy
        if 0 <= nx < config.width and 0 <= ny < config.height and is_legal_destination(owner, trail, player, nx, ny):
            moves.append(move)
    return moves


def fallback_move(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
) -> str | None:
    moves = legal_moves(config, owner, trail, player)
    if not moves:
        return None
    empty_moves = []
    home_moves = []
    for move in moves:
        dx, dy = MOVES[move]
        nx, ny = player.x + dx, player.y + dy
        if owner[ny][nx] == ".":
            empty_moves.append(move)
        else:
            home_moves.append(move)
    return (empty_moves or home_moves)[0]


def relocate_to_frontier(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
    rng: random.Random,
) -> bool:
    exits = frontier_exits(config, owner, trail, player)
    if not exits:
        player.alive = False
        return False
    _home, outside = rng.choice(exits)
    player.x, player.y = outside
    owner[outside[1]][outside[0]] = player.label
    trail[outside[1]][outside[0]] = player.label
    return True


def frontier_cells(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
) -> list[tuple[int, int]]:
    return [home for home, _outside in frontier_exits(config, owner, trail, player)]


def frontier_exits(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    exits = []
    for y in range(config.height):
        for x in range(config.width):
            if owner[y][x] != player.label:
                continue
            for dx, dy in MOVES.values():
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < config.width
                    and 0 <= ny < config.height
                    and owner[ny][nx] == "."
                    and trail[ny][nx] == "."
                ):
                    exits.append(((x, y), (nx, ny)))
    return exits


def is_legal_destination(
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
    x: int,
    y: int,
) -> bool:
    if owner[y][x] == player.label:
        return True
    if owner[y][x] != ".":
        return False
    return True


def update_idle_players(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    players: list[Player],
    previous_scores: dict[str, int],
    idle_turns: dict[str, int],
    idle_limit: int,
    rng: random.Random,
) -> None:
    for player in players:
        if not player.alive:
            continue
        score = count_cells(owner, player.label)
        if score == previous_scores[player.label]:
            idle_turns[player.label] += 1
        else:
            idle_turns[player.label] = 0
            previous_scores[player.label] = score
        if idle_turns[player.label] >= idle_limit:
            if relocate_to_frontier(config, owner, trail, player, rng):
                idle_turns[player.label] = 0
            else:
                player.alive = False


def random_start_positions(config: GameConfig, count: int, rng: random.Random) -> list[tuple[int, int]]:
    margin = 2
    xs = range(margin, max(margin + 1, config.width - margin))
    ys = range(margin, max(margin + 1, config.height - margin))
    candidates = [(x, y) for y in ys for x in xs]
    min_distance = max(5, config.size // 3)

    for _ in range(1000):
        starts = rng.sample(candidates, count)
        distances = [
            abs(a[0] - b[0]) + abs(a[1] - b[1])
            for index, a in enumerate(starts)
            for b in starts[index + 1 :]
        ]
        if all(distance >= min_distance for distance in distances):
            return starts

    corners = [
        (2, 2),
        (config.width - 3, config.height - 3),
        (config.width - 3, 2),
        (2, config.height - 3),
    ]
    return corners[:count]


def public_state(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    you: Player,
    players: list[Player],
    turn: int,
) -> dict[str, Any]:
    grid = []
    for y in range(config.height):
        row = []
        for x in range(config.width):
            cell = owner[y][x]
            if trail[y][x] != ".":
                cell = trail[y][x].lower()
            row.append(cell)
        grid.append(row)

    opponents = [player for player in players if player.label != you.label]
    closest = min(opponents, key=lambda p: abs(p.x - you.x) + abs(p.y - you.y))
    return {
        "grid": grid,
        "you": player_state(owner, trail, you),
        "opponent": player_state(owner, trail, closest),
        "opponents": [player_state(owner, trail, player) for player in opponents],
        "turn": turn,
        "max_turns": config.max_turns,
        "remaining_turns": config.max_turns - turn,
        "scores": {player.label: count_cells(owner, player.label) for player in players},
        "valid_moves": legal_moves(config, owner, trail, you),
    }


def player_state(owner: list[list[str]], trail: list[list[str]], player: Player) -> dict[str, Any]:
    return {
        "label": player.label,
        "x": player.x,
        "y": player.y,
        "alive": player.alive,
        "territory": count_cells(owner, player.label),
        "trail": collect_cells(trail, player.label),
    }


def step_player(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    player: Player,
    players: list[Player],
    move: str,
    rng: random.Random,
) -> None:
    dx, dy = MOVES.get(move, MOVES["UP"])
    nx, ny = player.x + dx, player.y + dy
    if nx < 0 or ny < 0 or nx >= config.width or ny >= config.height or not is_legal_destination(owner, trail, player, nx, ny):
        move = fallback_move(config, owner, trail, player)
        if move is None:
            relocate_to_frontier(config, owner, trail, player, rng)
            return
        dx, dy = MOVES[move]
        nx, ny = player.x + dx, player.y + dy
    if not is_legal_destination(owner, trail, player, nx, ny):
        player.alive = False
        return

    player.x, player.y = nx, ny
    cell_trail = trail[ny][nx]
    if cell_trail != ".":
        victim = next((p for p in players if p.label == cell_trail), None)
        if victim:
            victim.alive = False
            clear_trail(trail, victim.label)

    if owner[ny][nx] == ".":
        owner[ny][nx] = player.label
        trail[ny][nx] = player.label


def clear_trail(trail: list[list[str]], label: str) -> None:
    for y, row in enumerate(trail):
        for x, cell in enumerate(row):
            if cell == label:
                trail[y][x] = "."


def resolve_head_collisions(players: list[Player]) -> None:
    return


def decide_winner(players: list[Player], scores: dict[str, int]) -> Player | None:
    alive = [player for player in players if player.alive]
    candidates = alive or players
    ordered = sorted(candidates, key=lambda player: scores.get(player.label, 0), reverse=True)
    if len(ordered) >= 2 and scores.get(ordered[0].label, 0) == scores.get(ordered[1].label, 0):
        return None
    return ordered[0] if ordered else None


def claimed_ratio(owner: list[list[str]]) -> float:
    total = len(owner) * len(owner[0])
    return sum(1 for row in owner for cell in row if cell != ".") / total


def count_cells(grid: list[list[str]], label: str) -> int:
    return sum(1 for row in grid for cell in row if cell == label)


def collect_cells(grid: list[list[str]], label: str) -> list[dict[str, int]]:
    return [{"x": x, "y": y} for y, row in enumerate(grid) for x, cell in enumerate(row) if cell == label]


def frame(
    config: GameConfig,
    owner: list[list[str]],
    trail: list[list[str]],
    players: list[Player],
    turn: int,
) -> dict[str, Any]:
    return {
        "turn": turn,
        "owner": ["".join(row) for row in owner],
        "trail": ["".join(row) for row in trail],
        "players": {
            player.label: {
                "x": player.x,
                "y": player.y,
                "alive": player.alive,
                "agent_id": player.agent_id,
            }
            for player in players
        },
        "scores": {player.label: count_cells(owner, player.label) for player in players},
    }
