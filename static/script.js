const state = {
  agents: [],
  matches: [],
  replay: null,
  frameIndex: 0,
  timer: null,
};

const labels = ["A", "B", "C", "D"];
const colors = {
  A: { area: "rgba(60,199,214,0.55)", trail: "#3cc7d6", player: "#dffbff" },
  B: { area: "rgba(232,93,117,0.55)", trail: "#e85d75", player: "#ffe4e9" },
  C: { area: "rgba(117,214,123,0.55)", trail: "#75d67b", player: "#e8ffe9" },
  D: { area: "rgba(230,199,92,0.55)", trail: "#e6c75c", player: "#fff7d6" },
};

const arena = document.querySelector("#arena");
const ctx = arena.getContext("2d");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  return res.json();
}

async function refresh() {
  const [agents, matches] = await Promise.all([api("/api/agents"), api("/api/matches")]);
  state.agents = agents;
  state.matches = matches;
  renderAgents();
  renderLeaderboard();
  renderMatches();
  if (!state.replay && matches[0]) {
    await loadMatch(matches[0].id);
  }
}

function renderAgents() {
  const selects = document.querySelectorAll(".agentSelect");
  selects.forEach((select, index) => {
    const selected = select.value;
    select.innerHTML = "";
    if (index >= 2) {
      select.appendChild(new Option("None", ""));
    }
    for (const agent of state.agents) {
      select.appendChild(new Option(`${agent.name} (${agent.rating})`, agent.id));
    }
    if (selected) select.value = selected;
  });
  if (state.agents[0] && !document.querySelector("#agentA").value) {
    document.querySelector("#agentA").value = state.agents[0].id;
  }
  if (state.agents[1] && !document.querySelector("#agentB").value) {
    document.querySelector("#agentB").value = state.agents[1].id;
  }
}

function renderLeaderboard() {
  const root = document.querySelector("#leaderboard");
  root.innerHTML = "";
  for (const [index, agent] of state.agents.entries()) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `<div><b>#${index + 1} ${escapeHtml(agent.name)}</b><br><small>${escapeHtml(agent.author)} · ${agent.wins}W ${agent.losses}L ${agent.draws}D</small></div><strong>${agent.rating}</strong>`;
    root.appendChild(row);
  }
}

function renderMatches() {
  const root = document.querySelector("#matches");
  root.innerHTML = "";
  for (const match of state.matches) {
    const row = document.createElement("button");
    row.className = "row";
    const scoreText = Object.entries(match.scores || {})
      .map(([label, score]) => `${label}:${score}`)
      .join(" ");
    row.innerHTML = `<div><b>${escapeHtml(match.agent_names)}</b><br><small>${match.reason} · ${match.turns} turns · ${scoreText}</small></div><strong>#${match.id}</strong>`;
    row.addEventListener("click", () => loadMatch(match.id));
    root.appendChild(row);
  }
}

async function runMatch() {
  const agentIds = [...document.querySelectorAll(".agentSelect")]
    .map((select) => Number(select.value))
    .filter(Boolean);
  if (agentIds.length < 2 || agentIds.length > 4) {
    alert("Select 2 to 4 agents.");
    return;
  }
  const size = Number(document.querySelector("#boardSize").value);
  const payload = { agent_ids: agentIds, size };
  document.querySelector("#matchMeta").textContent = `Running ${agentIds.length}-agent ${size}x${size} match.`;
  pause();
  const result = await api("/api/matches", { method: "POST", body: JSON.stringify(payload) });
  await refresh();
  await loadMatch(result.id);
  play();
}

async function uploadAgent() {
  const payload = {
    name: document.querySelector("#agentName").value,
    author: document.querySelector("#authorName").value,
    code: document.querySelector("#codeInput").value,
  };
  await api("/api/agents", { method: "POST", body: JSON.stringify(payload) });
  await refresh();
}

async function loadMatch(id) {
  const match = await api(`/api/matches/${id}`);
  state.replay = match.replay;
  if (!state.replay.participants) {
    state.replay.participants = match.participants || [];
  }
  state.frameIndex = 0;
  document.querySelector("#turnSlider").max = match.replay.frames.length - 1;
  document.querySelector("#turnSlider").value = 0;
  const starts = Object.entries(match.replay.start_positions || {})
    .map(([label, pos]) => `${label}(${pos.x},${pos.y})`)
    .join(" ");
  document.querySelector("#matchMeta").textContent =
    `#${match.id} ${match.agent_names} · ${match.replay.size || match.replay.width}x${match.replay.height} · ${starts} · ${match.reason}`;
  draw();
}

function draw() {
  ctx.clearRect(0, 0, arena.width, arena.height);
  if (!state.replay) {
    drawEmpty();
    return;
  }
  const frame = state.replay.frames[state.frameIndex];
  const w = state.replay.width;
  const h = state.replay.height;
  const cell = Math.min(arena.width / w, arena.height / h);
  const ox = (arena.width - cell * w) / 2;
  const oy = (arena.height - cell * h) / 2;

  ctx.fillStyle = "#0b0c0f";
  ctx.fillRect(0, 0, arena.width, arena.height);

  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      const owner = frame.owner[y][x];
      const trail = frame.trail[y][x];
      ctx.fillStyle = "#171a20";
      if (colors[owner]) ctx.fillStyle = colors[owner].area;
      const trailLabel = trail.toUpperCase();
      if (colors[trailLabel]) ctx.fillStyle = colors[trailLabel].trail;
      ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell);
    }
  }

  drawGrid(ox, oy, w, h, cell);
  for (const [label, player] of Object.entries(frame.players)) {
    if (player.alive) {
      drawPlayer(label, player, ox, oy, cell);
    }
  }
  renderScorebar(frame);
  document.querySelector("#turnSlider").value = state.frameIndex;
}

function renderScorebar(frame) {
  const root = document.querySelector("#scorebar");
  const participants = state.replay.participants || labels.map((label) => ({ label, name: label }));
  root.innerHTML = "";
  for (const participant of participants) {
    const label = participant.label;
    const item = document.createElement("span");
    item.className = `chip ${label.toLowerCase()}`;
    item.textContent = `${label} ${frame.scores[label] || 0}`;
    root.appendChild(item);
  }
  const turn = document.createElement("span");
  turn.id = "turnLabel";
  turn.textContent = `Turn ${frame.turn}`;
  root.appendChild(turn);
}

function drawGrid(ox, oy, w, h, cell) {
  ctx.strokeStyle = "rgba(255,255,255,0.11)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let x = 0; x <= w; x += 1) {
    ctx.moveTo(ox + x * cell, oy);
    ctx.lineTo(ox + x * cell, oy + h * cell);
  }
  for (let y = 0; y <= h; y += 1) {
    ctx.moveTo(ox, oy + y * cell);
    ctx.lineTo(ox + w * cell, oy + y * cell);
  }
  ctx.stroke();
}

function drawPlayer(label, player, ox, oy, cell) {
  const color = colors[label] || colors.A;
  ctx.fillStyle = color.player;
  ctx.strokeStyle = player.alive ? "#ffffff" : "#222";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(ox + player.x * cell + cell / 2, oy + player.y * cell + cell / 2, cell * 0.34, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function drawEmpty() {
  ctx.fillStyle = "#0b0c0f";
  ctx.fillRect(0, 0, arena.width, arena.height);
  ctx.fillStyle = "#a8afbd";
  ctx.font = "22px Segoe UI";
  ctx.textAlign = "center";
  ctx.fillText("Run an N x N match", arena.width / 2, arena.height / 2);
}

function play() {
  pause();
  if (state.replay && state.frameIndex >= state.replay.frames.length - 1) {
    state.frameIndex = 0;
    draw();
  }
  state.timer = setInterval(() => {
    if (!state.replay) return;
    state.frameIndex = Math.min(state.frameIndex + 1, state.replay.frames.length - 1);
    draw();
    if (state.frameIndex >= state.replay.frames.length - 1) pause();
  }, 100);
}

function pause() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[ch]));
}

document.querySelector("#refreshBtn").addEventListener("click", refresh);
document.querySelector("#runMatchBtn").addEventListener("click", runMatch);
document.querySelector("#uploadBtn").addEventListener("click", uploadAgent);
document.querySelector("#playBtn").addEventListener("click", play);
document.querySelector("#pauseBtn").addEventListener("click", pause);
document.querySelector("#turnSlider").addEventListener("input", (event) => {
  state.frameIndex = Number(event.target.value);
  draw();
});

draw();
refresh().catch((error) => alert(error.message));
