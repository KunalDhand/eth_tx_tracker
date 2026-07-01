import csv
import json
import os
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8010
FINALIZED_CSV_FILE = "finalized_blocks_range.csv"
LOG_CSV_FILE = "blocks_log.csv"


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Parallel Blockchain Compare Viewer</title>
  <style>
    :root {
      --bg: #f6efe8;
      --panel: rgba(255, 252, 248, 0.9);
      --text: #2c241e;
      --muted: #78695f;
      --line-main: #ca744f;
      --line-log: #2f6f83;
      --line-missing: #b88b58;
      --node-finalized: #fff8f3;
      --node-log: #edf7fb;
      --node-diff: #fff0ec;
      --node-missing: #fff6e8;
      --border-finalized: rgba(202, 116, 79, 0.4);
      --border-log: rgba(47, 111, 131, 0.42);
      --border-diff: rgba(196, 82, 56, 0.45);
      --border-missing: rgba(184, 139, 88, 0.45);
      --shadow: 0 18px 40px rgba(126, 98, 72, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(202, 116, 79, 0.12), transparent 28%),
        radial-gradient(circle at bottom right, rgba(47, 111, 131, 0.12), transparent 30%),
        linear-gradient(180deg, #fbf8f5 0%, var(--bg) 100%);
    }

    .shell {
      max-width: 1480px;
      margin: 0 auto;
      padding: 22px;
    }

    .hero {
      position: relative;
      background: var(--panel);
      border: 1px solid rgba(120, 105, 95, 0.14);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 22px 24px 20px;
    }

    h1 {
      margin: 0;
      font-size: 23px;
      letter-spacing: 0.02em;
    }

    .corner-stat {
      position: absolute;
      top: 18px;
      right: 20px;
      min-width: 170px;
      text-align: right;
      background: rgba(255, 255, 255, 0.76);
      border: 1px solid rgba(120, 105, 95, 0.14);
      border-radius: 16px;
      padding: 10px 12px;
    }

    .corner-stat-label {
      font-size: 6px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .corner-stat-value {
      margin-top: 4px;
      font-size: 20px;
      font-weight: 700;
    }

    .corner-stat-note {
      margin-top: 3px;
      color: var(--muted);
      font-size: 11px;
    }

    .subhead {
      margin-top: 10px;
      color: var(--muted);
      line-height: 1.4;
      font-size: 14px;
      max-width: 980px;
    }

    .toolbar {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      align-items: center;
      margin-top: 18px;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      color: white;
      background: linear-gradient(135deg, #cd7a55 0%, #b25b35 100%);
      box-shadow: 0 8px 18px rgba(178, 91, 53, 0.22);
    }

    button.secondary {
      background: linear-gradient(135deg, #47798a 0%, #2f5b6b 100%);
      box-shadow: 0 8px 18px rgba(47, 91, 107, 0.2);
    }

    button:disabled {
      cursor: not-allowed;
      opacity: 0.5;
      box-shadow: none;
    }

    .metric-row {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 12px;
    }

    .metric {
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(120, 105, 95, 0.14);
      border-radius: 18px;
      padding: 14px 16px;
    }

    .metric-label {
      font-size: 7px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .metric-value {
      margin-top: 6px;
      font-size: 19px;
      font-weight: 700;
    }

    .metric-note {
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }

    .graph-shell {
      margin-top: 20px;
      background: rgba(255, 252, 248, 0.92);
      border: 1px solid rgba(120, 105, 95, 0.14);
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .legend {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      padding: 16px 18px 0;
      color: var(--muted);
      font-size: 12px;
    }

    .chip {
      border-radius: 999px;
      padding: 5px 10px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }

    .chip.finalized { background: rgba(202, 116, 79, 0.14); color: #8f4d31; }
    .chip.log { background: rgba(47, 111, 131, 0.12); color: #24586a; }
    .chip.diff { background: rgba(196, 82, 56, 0.12); color: #9b4229; }
    .chip.missing { background: rgba(184, 139, 88, 0.14); color: #85613a; }

    #graph {
      position: relative;
      height: 620px;
      overflow: hidden;
      cursor: grab;
      user-select: none;
      touch-action: pan-x pan-y;
    }

    #graph.dragging { cursor: grabbing; }

    #graph-inner {
      position: relative;
      height: 100%;
      min-width: 100%;
    }

    #links {
      position: absolute;
      inset: 0;
      pointer-events: none;
      overflow: visible;
    }

    .lane-title {
      position: absolute;
      left: 24px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      z-index: 2;
    }

    .block-node {
      position: absolute;
      width: 150px;
      min-height: 138px;
      border-radius: 18px;
      padding: 12px 12px 11px;
      box-shadow: var(--shadow);
      border: 1px solid transparent;
      background: white;
      z-index: 1;
    }

    .block-node.finalized {
      background: var(--node-finalized);
      border-color: var(--border-finalized);
    }

    .block-node.log.match {
      background: var(--node-log);
      border-color: var(--border-log);
    }

    .block-node.log.diff {
      background: var(--node-diff);
      border-color: var(--border-diff);
    }

    .block-node.log.missing {
      background: var(--node-missing);
      border-color: var(--border-missing);
      border-style: dashed;
    }

    .block-node.focused {
      box-shadow: 0 0 0 3px rgba(47, 111, 131, 0.22), var(--shadow);
      transform: translateY(-4px);
    }

    .node-badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      letter-spacing: 0.06em;
      font-weight: 700;
      background: rgba(121, 97, 76, 0.08);
    }

    .block-node.log.match .node-badge { background: rgba(47, 111, 131, 0.12); }
    .block-node.log.diff .node-badge { background: rgba(196, 82, 56, 0.14); }
    .block-node.log.missing .node-badge { background: rgba(184, 139, 88, 0.16); }

    .block-number {
      margin-top: 10px;
      font-size: 15px;
      font-weight: 700;
    }

    .node-label {
      margin-top: 7px;
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .node-value {
      margin-top: 3px;
      font-size: 12px;
      line-height: 1.3;
      word-break: break-word;
    }

    .status-bar {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      padding: 0 18px 16px;
      color: var(--muted);
      font-size: 12px;
    }

    @media (max-width: 960px) {
      .shell { padding: 16px; }
      .corner-stat {
        position: static;
        margin-top: 14px;
        text-align: left;
      }
      .metric-row { grid-template-columns: repeat(2, minmax(160px, 1fr)); }
      #graph { height: 700px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="corner-stat">
        <div class="corner-stat-label">Total Log Differences</div>
        <div class="corner-stat-value" id="differenceCountValue">Loading...</div>
        <div class="corner-stat-note" id="differenceCountNote">Counting mismatch block numbers</div>
      </div>
      <h1>Parallel Blockchain Compare Viewer</h1>
      <div class="subhead">
        Finalized blocks are shown on the top lane and real-time collected blocks are shown below them.
        Navigation jumps between comparison events: mismatch segments, missing-data spans, and the next point where data becomes available again.
      </div>

      <div class="toolbar">
        <button id="prevBtn">Move Left</button>
        <button id="nextBtn" class="secondary">Move Right</button>
      </div>

      <div class="metric-row">
        <div class="metric">
          <div class="metric-label">Focused Position</div>
          <div class="metric-value" id="focusValue">Loading...</div>
          <div class="metric-note" id="focusNote">Preparing comparison payload</div>
        </div>
        <div class="metric">
          <div class="metric-label">Visible Range</div>
          <div class="metric-value" id="rangeValue">Loading...</div>
          <div class="metric-note" id="rangeNote">Calculating viewport</div>
        </div>
        <div class="metric">
          <div class="metric-label">Time Range</div>
          <div class="metric-value" id="timeRangeValue">Loading...</div>
          <div class="metric-note" id="timeRangeNote">Calculating blockchain timestamp span</div>
        </div>
        <div class="metric">
          <div class="metric-label">Dataset Summary</div>
          <div class="metric-value" id="summaryValue">Loading...</div>
          <div class="metric-note" id="summaryNote">Reading both chains</div>
        </div>
      </div>
    </section>

    <section class="graph-shell">
      <div class="legend">
        <span class="chip finalized">Finalized lane</span>
        <span class="chip log">Real-time lane</span>
        <span class="chip diff">Hash or parent differs</span>
        <span class="chip missing">Data not available in log</span>
      </div>
      <div id="graph">
        <div id="graph-inner">
          <svg id="links"></svg>
        </div>
      </div>
      <div class="status-bar">
        <div id="statusText">Loading data...</div>
        <div id="navText">Finding comparison events...</div>
      </div>
    </section>
  </div>

  <script>
    const state = {
      entries: [],
      entriesByNumber: {},
      eventPositions: [],
      segments: [],
      minBlockNumber: 0,
      maxBlockNumber: 0,
      offsetPx: 0,
      maxOffsetPx: 0,
      pendingFrame: null,
      isDragging: false,
      dragStartX: 0,
      dragStartOffsetPx: 0
    };

    const graph = document.getElementById("graph");
    const graphInner = document.getElementById("graph-inner");
    const links = document.getElementById("links");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const focusValue = document.getElementById("focusValue");
    const focusNote = document.getElementById("focusNote");
    const rangeValue = document.getElementById("rangeValue");
    const rangeNote = document.getElementById("rangeNote");
    const timeRangeValue = document.getElementById("timeRangeValue");
    const timeRangeNote = document.getElementById("timeRangeNote");
    const summaryValue = document.getElementById("summaryValue");
    const summaryNote = document.getElementById("summaryNote");
    const differenceCountValue = document.getElementById("differenceCountValue");
    const differenceCountNote = document.getElementById("differenceCountNote");
    const statusText = document.getElementById("statusText");
    const navText = document.getElementById("navText");

    const layout = {
      cardWidth: 150,
      cardHeight: 150,
      gapX: 58,
      padding: 32,
      finalizedY: 70,
      logBaseY: 300,
      logStackOffsetY: 168,
      renderBuffer: 3
    };

    function getStepX() {
      return layout.cardWidth + layout.gapX;
    }

    function shortHash(value) {
      if (!value) return "data not available";
      if (value.length <= 20) return value;
      return value.slice(0, 10) + "..." + value.slice(-8);
    }

    function blockNumberToX(blockNumber) {
      return layout.padding + (blockNumber - state.minBlockNumber) * getStepX() - state.offsetPx;
    }

    function classifyLogNodeClass(entry) {
      if (entry.kind === "missing") return "log missing";
      return entry.matches_finalized ? "log match" : "log diff";
    }

    function createNode(entry, laneKind, focused, stackIndex = 0) {
      const node = document.createElement("div");
      const nodeClass = laneKind === "finalized" ? "finalized" : classifyLogNodeClass(entry);
      node.className = `block-node ${nodeClass}`;
      if (focused) {
        node.classList.add("focused");
      }

      const left = blockNumberToX(entry.block_number);
      const top = laneKind === "finalized"
        ? layout.finalizedY
        : layout.logBaseY + stackIndex * layout.logStackOffsetY;

      node.style.left = left + "px";
      node.style.top = top + "px";
      node.dataset.hash = entry.block_hash || `missing-${entry.block_number}-${stackIndex}`;

      const badge = laneKind === "finalized"
        ? "Finalized"
        : (entry.kind === "missing" ? "Log Missing" : (entry.matches_finalized ? "Log Match" : "Log Difference"));

      const details = laneKind === "finalized"
        ? `
          <div class="node-label">Parent</div>
          <div class="node-value">${shortHash(entry.parent_hash)}</div>
        `
        : (entry.kind === "missing"
            ? `
              <div class="node-label">Status</div>
              <div class="node-value">Data not available in blocks_log.csv for this block number.</div>
            `
            : `
              <div class="node-label">Compare</div>
              <div class="node-value">${entry.compare_note}</div>
              <div class="node-label">Parent</div>
              <div class="node-value">${shortHash(entry.parent_hash)}</div>
            `);

      node.innerHTML = `
        <div class="node-badge">${badge}</div>
        <div class="block-number">#${entry.block_number}</div>
        <div class="node-label">Timestamp</div>
        <div class="node-value">${entry.timestamp || "data not available"}</div>
        <div class="node-label">Hash</div>
        <div class="node-value">${shortHash(entry.block_hash)}</div>
        ${details}
      `;

      return node;
    }

    function drawArrow(fromEl, toEl, strokeColor) {
      const startX = fromEl.offsetLeft + layout.cardWidth;
      const startY = fromEl.offsetTop + fromEl.offsetHeight / 2;
      const endX = toEl.offsetLeft;
      const endY = toEl.offsetTop + toEl.offsetHeight / 2;
      const midX = startX + (endX - startX) / 2;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX - 16} ${endY}`);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", strokeColor);
      path.setAttribute("stroke-width", "3");
      path.setAttribute("stroke-linecap", "round");

      const arrow = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      arrow.setAttribute("points", `${endX - 16},${endY - 7} ${endX},${endY} ${endX - 16},${endY + 7}`);
      arrow.setAttribute("fill", strokeColor);

      links.appendChild(path);
      links.appendChild(arrow);
    }

    function getVisibleRange() {
      const viewportWidth = Math.max(graph.clientWidth - 36, 1);
      const visibleCount = Math.max(Math.ceil(viewportWidth / getStepX()), 1);
      const startBlockNumber = Math.max(
        state.minBlockNumber,
        state.minBlockNumber + Math.floor(state.offsetPx / getStepX()) - layout.renderBuffer
      );
      const endBlockNumber = Math.min(
        state.maxBlockNumber,
        startBlockNumber + visibleCount + layout.renderBuffer * 2 - 1
      );
      return { startBlockNumber, endBlockNumber, visibleCount };
    }

    function getCenteredBlockNumber() {
      const viewportWidth = Math.max(graph.clientWidth - 36, 1);
      const centerPx = state.offsetPx + viewportWidth / 2;
      const centerOffset = Math.round((centerPx - layout.padding - layout.cardWidth / 2) / getStepX());
      return Math.min(Math.max(state.minBlockNumber + centerOffset, state.minBlockNumber), state.maxBlockNumber);
    }

    function clampOffset(offsetPx) {
      return Math.min(Math.max(offsetPx, 0), state.maxOffsetPx);
    }

    function blockNumberToOffset(blockNumber) {
      return clampOffset((blockNumber - state.minBlockNumber) * getStepX());
    }

    function recalculateBounds() {
      const viewportWidth = Math.max(graph.clientWidth - 36, 1);
      const blockSpan = Math.max(state.maxBlockNumber - state.minBlockNumber, 0);
      const virtualWidth = layout.padding * 2 + blockSpan * getStepX() + layout.cardWidth;
      state.maxOffsetPx = Math.max(virtualWidth - viewportWidth, 0);
      state.offsetPx = clampOffset(state.offsetPx);
    }

    function getCurrentSegment(blockNumber) {
      let active = null;
      for (const segment of state.segments) {
        if (segment.start_block <= blockNumber && blockNumber <= segment.end_block) {
          active = segment;
        }
      }
      return active;
    }

    function getPreviousEvent(blockNumber) {
      for (let index = state.eventPositions.length - 1; index >= 0; index -= 1) {
        if (state.eventPositions[index] < blockNumber) {
          return state.eventPositions[index];
        }
      }
      return undefined;
    }

    function getNextEvent(blockNumber) {
      for (const eventBlock of state.eventPositions) {
        if (eventBlock > blockNumber) {
          return eventBlock;
        }
      }
      return undefined;
    }

    function jumpToEvent(direction) {
      const centered = getCenteredBlockNumber();
      const target = direction < 0 ? getPreviousEvent(centered) : getNextEvent(centered);
      if (target === undefined) {
        return;
      }
      state.offsetPx = blockNumberToOffset(target);
      scheduleRender();
    }

    function render() {
      graphInner.querySelectorAll(".block-node, .lane-title").forEach((element) => element.remove());
      links.innerHTML = "";

      if (!state.entries.length) {
        focusValue.textContent = "No data";
        focusNote.textContent = "No rows were loaded.";
        rangeValue.textContent = "No range";
        timeRangeValue.textContent = "No range";
        timeRangeNote.textContent = "No blockchain timestamps loaded.";
        summaryValue.textContent = "0 blocks";
        differenceCountValue.textContent = "0";
        differenceCountNote.textContent = "No difference blocks loaded.";
        statusText.textContent = "The comparison dataset is empty.";
        navText.textContent = "No events available.";
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
      }

      const { startBlockNumber, endBlockNumber, visibleCount } = getVisibleRange();
      const centeredBlockNumber = getCenteredBlockNumber();
      const currentSegment = getCurrentSegment(centeredBlockNumber);
      const nodesByHash = new Map();
      const visibleEntries = [];
      let maxLogStack = 1;

      for (let number = startBlockNumber; number <= endBlockNumber; number += 1) {
        const entry = state.entriesByNumber[number];
        if (entry) {
          visibleEntries.push(entry);
          maxLogStack = Math.max(maxLogStack, entry.log_rows.length || 1);
        }
      }

      const finalizedTitle = document.createElement("div");
      finalizedTitle.className = "lane-title";
      finalizedTitle.textContent = "Finalized chain";
      finalizedTitle.style.top = "34px";
      graphInner.appendChild(finalizedTitle);

      const logTitle = document.createElement("div");
      logTitle.className = "lane-title";
      logTitle.textContent = "Real-time collected chain";
      logTitle.style.top = (layout.logBaseY - 42) + "px";
      graphInner.appendChild(logTitle);

      visibleEntries.forEach((entry) => {
        const finalizedNode = createNode(
          { ...entry.finalized, block_number: entry.block_number },
          "finalized",
          centeredBlockNumber === entry.block_number
        );
        graphInner.appendChild(finalizedNode);
        nodesByHash.set(`finalized-${entry.finalized.block_hash}`, finalizedNode);
      });

      visibleEntries.forEach((entry) => {
        const logRows = entry.log_rows.length ? entry.log_rows : [entry.missing_placeholder];
        logRows.forEach((row, index) => {
          const logNode = createNode(
            row,
            "log",
            centeredBlockNumber === entry.block_number,
            index
          );
          graphInner.appendChild(logNode);
          if (row.block_hash) {
            nodesByHash.set(`log-${row.block_hash}`, logNode);
          }
        });
      });

      const laneHeight = layout.logBaseY + Math.max(maxLogStack - 1, 0) * layout.logStackOffsetY + layout.cardHeight + 56;
      const width = Math.max(graph.clientWidth - 36, 1);
      graphInner.style.width = width + "px";
      graphInner.style.height = Math.max(laneHeight, 600) + "px";
      links.setAttribute("width", String(width));
      links.setAttribute("height", String(Math.max(laneHeight, 600)));

      let previousFinalized = null;
      visibleEntries.forEach((entry) => {
        const currentFinalized = nodesByHash.get(`finalized-${entry.finalized.block_hash}`);
        if (previousFinalized && currentFinalized) {
          drawArrow(previousFinalized, currentFinalized, "var(--line-main)");
        }
        previousFinalized = currentFinalized || previousFinalized;
      });

      visibleEntries.forEach((entry) => {
        if (!entry.log_rows.length) {
          return;
        }
        const topLog = nodesByHash.get(`log-${entry.log_rows[0].block_hash}`);
        const finalizedNode = nodesByHash.get(`finalized-${entry.finalized.block_hash}`);
        if (topLog && finalizedNode) {
          drawArrow(finalizedNode, topLog, entry.status === "difference" ? "var(--line-log)" : "var(--line-main)");
        }
      });

      let previousLog = null;
      visibleEntries.forEach((entry) => {
        if (!entry.log_rows.length) {
          return;
        }
        const primaryLog = nodesByHash.get(`log-${entry.log_rows[0].block_hash}`);
        if (previousLog && primaryLog) {
          drawArrow(previousLog, primaryLog, "var(--line-log)");
        }
        previousLog = primaryLog || previousLog;
      });

      focusValue.textContent = `#${centeredBlockNumber.toLocaleString()}`;
      focusNote.textContent = currentSegment
        ? `${currentSegment.label} from #${currentSegment.start_block.toLocaleString()} to #${currentSegment.end_block.toLocaleString()}`
        : "No active segment";
      rangeValue.textContent = `${startBlockNumber.toLocaleString()} - ${endBlockNumber.toLocaleString()}`;
      rangeNote.textContent = `Visible span: ${visibleCount} block numbers`;
      const firstTimestamp = state.entries[0]?.finalized?.timestamp || "";
      const lastTimestamp = state.entries[state.entries.length - 1]?.finalized?.timestamp || "";
      timeRangeValue.textContent = firstTimestamp && lastTimestamp ? `${firstTimestamp} to ${lastTimestamp}` : "Unknown";
      timeRangeNote.textContent = "Timestamp span from first finalized block to last finalized block.";
      summaryValue.textContent = `${state.entries.length.toLocaleString()} blocks`;
      summaryNote.textContent = `${state.segments.length.toLocaleString()} comparison segments, ${state.eventPositions.length.toLocaleString()} navigation event(s)`;
      differenceCountValue.textContent = state.entries
        .filter((entry) => entry.status === "difference")
        .length
        .toLocaleString();
      differenceCountNote.textContent = "Block numbers where log hash or parent differs from finalized.";
      statusText.textContent = currentSegment
        ? `Centered on ${currentSegment.label}.`
        : "No comparison segment found.";

      const prevEvent = getPreviousEvent(centeredBlockNumber);
      const nextEvent = getNextEvent(centeredBlockNumber);
      navText.textContent = `Prev event: ${prevEvent ? "#" + prevEvent.toLocaleString() : "none"} | Next event: ${nextEvent ? "#" + nextEvent.toLocaleString() : "none"}`;
      prevBtn.disabled = prevEvent === undefined;
      nextBtn.disabled = nextEvent === undefined;
    }

    function scheduleRender() {
      if (state.pendingFrame) {
        return;
      }
      state.pendingFrame = window.requestAnimationFrame(() => {
        state.pendingFrame = null;
        render();
      });
    }

    function beginDrag(clientX) {
      state.isDragging = true;
      state.dragStartX = clientX;
      state.dragStartOffsetPx = state.offsetPx;
      graph.classList.add("dragging");
    }

    function updateDrag(clientX) {
      if (!state.isDragging) {
        return;
      }
      const deltaX = clientX - state.dragStartX;
      state.offsetPx = clampOffset(state.dragStartOffsetPx - deltaX);
      scheduleRender();
    }

    function endDrag() {
      state.isDragging = false;
      graph.classList.remove("dragging");
    }

    async function loadData() {
      try {
        const response = await fetch("/data");
        const payload = await response.json();
        state.entries = payload.entries;
        state.entriesByNumber = Object.fromEntries(payload.entries.map((entry) => [entry.block_number, entry]));
        state.eventPositions = payload.event_positions;
        state.segments = payload.segments;
        state.minBlockNumber = payload.min_block_number;
        state.maxBlockNumber = payload.max_block_number;
        recalculateBounds();

        const firstInteresting = state.eventPositions[0];
        if (firstInteresting !== undefined) {
          state.offsetPx = blockNumberToOffset(firstInteresting);
        }
        render();
      } catch (error) {
        focusValue.textContent = "Load failed";
        focusNote.textContent = error.message;
        statusText.textContent = "The comparison graph could not be created.";
      }
    }

    prevBtn.addEventListener("click", () => jumpToEvent(-1));
    nextBtn.addEventListener("click", () => jumpToEvent(1));

    graph.addEventListener("mousedown", (event) => beginDrag(event.clientX));
    window.addEventListener("mousemove", (event) => updateDrag(event.clientX));
    window.addEventListener("mouseup", () => endDrag());
    graph.addEventListener("mouseleave", () => endDrag());
    graph.addEventListener("touchstart", (event) => {
      if (event.touches.length === 1) {
        beginDrag(event.touches[0].clientX);
      }
    }, { passive: true });
    graph.addEventListener("touchmove", (event) => {
      if (event.touches.length === 1) {
        updateDrag(event.touches[0].clientX);
      }
    }, { passive: true });
    graph.addEventListener("touchend", () => endDrag(), { passive: true });
    graph.addEventListener("wheel", (event) => {
      const primaryDelta = Math.abs(event.deltaX) >= Math.abs(event.deltaY)
        ? event.deltaX
        : event.deltaY;
      if (!primaryDelta) {
        return;
      }
      event.preventDefault();
      state.offsetPx = clampOffset(state.offsetPx + primaryDelta);
      scheduleRender();
    }, { passive: false });

    window.addEventListener("resize", () => {
      recalculateBounds();
      scheduleRender();
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        jumpToEvent(-1);
      } else if (event.key === "ArrowRight") {
        jumpToEvent(1);
      }
    });

    loadData();
  </script>
</body>
</html>
"""


def load_blocks(csv_path):
    blocks = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            block_number = (row.get("block_number") or "").strip()
            if not block_number or block_number == "block_number":
                continue
            try:
                row["block_number"] = int(block_number)
            except ValueError:
                continue
            blocks.append(row)
    blocks.sort(key=lambda item: (item["block_number"], item["timestamp"], item["block_hash"]))
    return blocks


def build_comparison_payload(finalized_path, log_path):
    finalized_blocks = load_blocks(finalized_path)
    log_blocks = load_blocks(log_path)

    log_by_number = defaultdict(list)
    for row in log_blocks:
        log_by_number[row["block_number"]].append(dict(row))

    entries = []

    for finalized in finalized_blocks:
        block_number = finalized["block_number"]
        log_rows = log_by_number.get(block_number, [])

        prepared_log_rows = []
        exact_match_exists = False
        differing_exists = False

        for row in log_rows:
            matches_hash = row["block_hash"] == finalized["block_hash"]
            matches_parent = row["parent_hash"] == finalized["parent_hash"]
            matches_finalized = matches_hash and matches_parent
            compare_parts = []
            compare_parts.append("Hash matches" if matches_hash else "Hash differs")
            compare_parts.append("Parent matches" if matches_parent else "Parent differs")
            prepared_row = {
                **row,
                "kind": "log",
                "matches_finalized": matches_finalized,
                "compare_note": " | ".join(compare_parts),
            }
            prepared_log_rows.append(prepared_row)
            exact_match_exists = exact_match_exists or matches_finalized
            differing_exists = differing_exists or not matches_finalized

        if not prepared_log_rows:
            status = "missing"
        elif differing_exists or not exact_match_exists:
            status = "difference"
        else:
            status = "match"

        missing_placeholder = {
            "block_number": block_number,
            "timestamp": "",
            "block_hash": "",
            "parent_hash": "",
            "kind": "missing",
            "matches_finalized": False,
            "compare_note": "Data not available",
        }

        entries.append(
            {
                "block_number": block_number,
                "finalized": dict(finalized),
                "log_rows": prepared_log_rows,
                "missing_placeholder": missing_placeholder,
                "status": status,
            }
        )

    segments = []
    if entries:
        current_status = entries[0]["status"]
        segment_start = entries[0]["block_number"]

        for index in range(1, len(entries)):
            entry = entries[index]
            if entry["status"] != current_status:
                previous_block = entries[index - 1]["block_number"]
                segments.append(make_segment(segment_start, previous_block, current_status))
                current_status = entry["status"]
                segment_start = entry["block_number"]

        segments.append(make_segment(segment_start, entries[-1]["block_number"], current_status))

    event_positions = []
    if segments:
        if segments[0]["status"] != "match":
            event_positions.append(segments[0]["start_block"])
        for index in range(1, len(segments)):
            event_positions.append(segments[index]["start_block"])

    return {
        "entries": entries,
        "segments": segments,
        "event_positions": event_positions,
        "min_block_number": entries[0]["block_number"] if entries else 0,
        "max_block_number": entries[-1]["block_number"] if entries else 0,
    }


def make_segment(start_block, end_block, status):
    if status == "difference":
        return {
            "status": status,
            "start_block": start_block,
            "end_block": end_block,
            "label": "difference segment",
            "short_label": "Difference",
            "description": "At least one log block differs in hash or parent from the finalized block.",
        }
    if status == "missing":
        return {
            "status": status,
            "start_block": start_block,
            "end_block": end_block,
            "label": "missing-data segment",
            "short_label": "Missing",
            "description": "No data is available in blocks_log.csv for these block numbers.",
        }
    return {
        "status": status,
        "start_block": start_block,
        "end_block": end_block,
        "label": "matching segment",
        "short_label": "Match",
        "description": "The log data matches the finalized block for these block numbers.",
    }


CHAIN_PAYLOAD = build_comparison_payload(
    os.path.join(os.path.dirname(__file__), FINALIZED_CSV_FILE),
    os.path.join(os.path.dirname(__file__), LOG_CSV_FILE),
)


class ChainViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/data":
            payload = json.dumps(CHAIN_PAYLOAD).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(404, "Not found")

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((HOST, PORT), ChainViewerHandler)
    print(f"Serving parallel blockchain compare viewer at http://{HOST}:{PORT}")
    print(f"Loaded {len(CHAIN_PAYLOAD['entries'])} block numbers")
    print(f"Computed {len(CHAIN_PAYLOAD['segments'])} segments and {len(CHAIN_PAYLOAD['event_positions'])} navigation events")
    server.serve_forever()


if __name__ == "__main__":
    main()
