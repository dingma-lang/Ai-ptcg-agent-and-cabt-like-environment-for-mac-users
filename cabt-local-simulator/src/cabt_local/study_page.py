from __future__ import annotations

from .ui_theme import decorate_page


STUDY_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Battle Lab | Study</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #5e6b78;
      --line: #cbd5df;
      --soft: #f5f8fa;
      --accent: #176f8f;
      --green: #236b47;
      --red: #a33d3d;
      --amber: #8a5918;
      --white: #fff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--white);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      height: 58px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 20px;
      border-bottom: 1px solid var(--line);
      background: #eef5f7;
    }
    h1 { margin: 0; font-size: 20px; letter-spacing: 0; }
    h2 { margin: 0 0 10px; font-size: 15px; letter-spacing: 0; }
    h3 { margin: 0; font-size: 14px; letter-spacing: 0; }
    a { color: var(--accent); font-weight: 700; text-decoration: none; }
    main {
      display: grid;
      grid-template-columns: minmax(310px, 390px) minmax(0, 1fr);
      min-height: calc(100vh - 58px);
    }
    aside {
      padding: 16px;
      border-right: 1px solid var(--line);
      background: var(--soft);
      overflow: auto;
    }
    section { padding: 16px; min-width: 0; }
    .block { padding: 0 0 16px; margin: 0 0 16px; border-bottom: 1px solid var(--line); }
    .field { display: grid; gap: 6px; margin-bottom: 12px; }
    label, .label { color: var(--muted); font-size: 12px; font-weight: 750; }
    select, input, textarea, button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--white);
      color: var(--ink);
      font: inherit;
      letter-spacing: 0;
    }
    select, input { min-height: 36px; width: 100%; padding: 0 8px; }
    input[type="file"] { padding: 6px 8px; }
    textarea {
      width: 100%;
      min-height: 220px;
      padding: 9px;
      resize: vertical;
      font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    button { min-height: 36px; padding: 0 12px; cursor: pointer; font-weight: 700; }
    button.primary { color: white; border-color: var(--accent); background: var(--accent); }
    button.accept { color: white; border-color: var(--green); background: var(--green); }
    button.reject { color: white; border-color: var(--red); background: var(--red); }
    button:disabled { cursor: default; opacity: .55; }
    .toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .status {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
    }
    .status.good { color: var(--green); border-color: #a9d1ba; background: #f1faf5; }
    .status.bad { color: var(--red); border-color: #dfb4b4; background: #fff5f5; }
    .status.warn { color: var(--amber); border-color: #e2c798; background: #fff9ed; }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(100px, 1fr));
      gap: 8px;
      margin-bottom: 16px;
    }
    .metric { padding: 10px; border-top: 3px solid var(--accent); background: var(--soft); }
    .metric strong { display: block; font-size: 22px; }
    .metric span { color: var(--muted); font-size: 12px; }
    .notice { padding: 10px 12px; border-left: 3px solid var(--amber); background: #fff9ed; font-size: 13px; }
    .finding-list { display: grid; gap: 10px; }
    .finding {
      display: grid;
      gap: 9px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
    }
    .finding.accepted { border-left: 5px solid var(--green); }
    .finding.rejected { border-left: 5px solid var(--red); opacity: .78; }
    .finding-head { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
    .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .text { font-size: 13px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; }
    .muted { color: var(--muted); }
    details { border-top: 1px solid var(--line); padding-top: 8px; }
    summary { cursor: pointer; color: var(--accent); font-size: 12px; font-weight: 750; }
    .rule-editor { min-height: 150px; margin-top: 8px; }
    .timeline { display: grid; gap: 5px; max-height: 380px; overflow: auto; }
    .event { padding: 7px 9px; border-left: 3px solid var(--line); background: var(--soft); font-size: 12px; }
    .checkpoint-list { display: grid; gap: 7px; }
    .checkpoint { padding: 9px; border: 1px solid var(--line); border-radius: 6px; background: white; font-size: 12px; }
    @media (max-width: 820px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .summary-grid { grid-template-columns: repeat(2, minmax(100px, 1fr)); }
      header .status { display: none; }
    }
    @media (max-width: 480px) {
      header { padding: 0 12px; }
      header .toolbar { gap: 6px; }
    }
  </style>
</head>
<body>
  <header class="app-header">
    <a class="brand" href="/"><span class="brand-mark">__ICON_layers__</span><span><strong>Battle Lab</strong><small>cabt local simulator</small></span></a>
    <nav class="app-nav" aria-label="Main navigation"><a href="/">__ICON_swords__ Simulator</a><a href="/study" aria-current="page">__ICON_book-open__ Study</a></nav>
    <span id="saveStatus" class="status" role="status" aria-live="polite">Ready</span>
  </header>
  <main>
    <aside>
      <div class="block">
        <p class="eyebrow">New study</p>
        <h2>Agent &amp; battle log</h2>
        <div class="field">
          <label for="agentSelect">Agent</label>
          <select id="agentSelect"></select>
        </div>
        <div class="field">
          <label for="logFile">Battle Log File</label>
          <input id="logFile" type="file" accept=".txt,.log,.html">
        </div>
        <div class="field">
          <label for="logText">Battle Log</label>
          <textarea id="logText" placeholder="Paste battle log"></textarea>
        </div>
        <button id="analyzeBtn" class="primary">__ICON_sparkles__ Analyze battle</button>
      </div>
      <details class="fold" id="traceSettings"><summary>__ICON_layers__ Decision trace</summary><div class="fold-body">
        <div class="field"><label for="episodeSelect">Optional matching episode</label><select id="episodeSelect"></select></div>
      </div></details>
      <details class="fold" id="memorySettings"><summary>__ICON_cpu__ Agent memory</summary><div class="fold-body">
        <div id="memoryStatus" class="notice">Select an agent.</div>
        <div class="toolbar" style="margin-top:8px">
          <button id="validateMemoryBtn" type="button">Validate Agent &amp; Memory</button>
          <button id="installHookBtn" type="button" class="primary" hidden>Install Rule Hook</button>
        </div>
      </div></details>
      <details class="fold" id="checkpointSettings"><summary>__ICON_folder-open__ Checkpoints</summary><div class="fold-body">
        <button id="baselineBtn" type="button" style="margin-bottom:8px">Restore Baseline</button>
        <div id="checkpointList" class="checkpoint-list"></div>
      </div></details>
    </aside>
    <section>
      <div class="page-heading"><div><p class="eyebrow">Review &amp; learn</p><h1>Battle Study</h1></div><span class="status">Local review</span></div>
      <div id="integrationStatus" class="inline-status" role="status" hidden></div>
      <div id="emptyState" class="empty-view">__ICON_book-open__<h2>A fresh page for your next battle</h2><span>No study selected</span></div>
      <div id="studyView" hidden>
        <div id="summary" class="summary-grid"></div>
        <details class="fold" style="margin-bottom:20px"><summary>Evidence &amp; limitations</summary><div id="limitations" class="notice fold-body"></div></details>
        <div class="section-heading"><h2>Battle takeaways</h2>__ICON_sparkles__</div>
        <div class="finding-tools"><select id="findingFilter" aria-label="Filter findings"><option value="all">All findings</option><option value="pending">Pending</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option></select></div>
        <div id="findingList" class="finding-list"></div>
        <p id="noFilteredFindings" class="muted" hidden>No findings in this group.</p>
        <details class="fold" style="margin-top:20px"><summary>__ICON_layers__ Parsed timeline</summary><div id="timeline" class="timeline fold-body"></div></details>
      </div>
    </section>
  </main>
  <script>
    const state = { agents: [], episodes: [], study: null };
    const $ = (id) => document.getElementById(id);

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[char]));
    }

    async function getJson(url) {
      const response = await fetch(url, { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) throw new Error(payload.error || `Request failed: ${response.status}`);
      return payload;
    }

    async function postJson(url, body) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) throw new Error(payload.error || `Request failed: ${response.status}`);
      return payload;
    }

    function setStatus(text, kind = "") {
      $("saveStatus").textContent = text;
      $("saveStatus").className = `status ${kind}`;
    }

    async function loadStatus() {
      const payload = await getJson("/api/study/status");
      state.agents = payload.agents || [];
      state.episodes = payload.episodes || [];
      $("agentSelect").innerHTML = state.agents
        .filter((agent) => agent.spec !== "random")
        .map((agent) => `<option value="${escapeHtml(agent.spec)}">${escapeHtml(agent.name)}</option>`).join("");
      $("episodeSelect").innerHTML = `<option value="">No decision trace</option>` + state.episodes
        .map((episode) => `<option value="${escapeHtml(episode.path)}">${escapeHtml(episode.name)} (${episode.decisions})</option>`).join("");
      await loadCheckpoints();
    }

    async function analyze() {
      const logText = $("logText").value.trim();
      const agent = $("agentSelect").value;
      if (!agent || !logText) {
        setStatus("Agent and log required", "bad");
        return;
      }
      $("analyzeBtn").disabled = true;
      $("analyzeBtn").textContent = "Analyzing battle...";
      setStatus("Analyzing", "warn");
      try {
        state.study = await postJson("/api/study/analyze", {
          agent,
          log_text: logText,
          episode_path: $("episodeSelect").value
        });
        history.replaceState({}, "", `/study?study=${encodeURIComponent(state.study.study_id)}`);
        renderStudy();
        await loadCheckpoints();
        setStatus("Study saved", "good");
      } catch (error) {
        setStatus(String(error), "bad");
      } finally {
        $("analyzeBtn").disabled = false;
        $("analyzeBtn").innerHTML = `__ICON_sparkles__ Analyze battle`;
      }
    }

    function renderStudy() {
      const study = state.study;
      if (!study) return;
      $("emptyState").hidden = true;
      $("studyView").hidden = false;
      const summary = study.summary || {};
      const statuses = summary.by_status || {};
      const severities = summary.by_severity || {};
      $("summary").innerHTML = [
        [summary.total || 0, "Findings"],
        [statuses.pending || 0, "Pending"],
        [statuses.accepted || 0, "Accepted"],
        [(severities.critical || 0) + (severities.high || 0), "High priority"]
      ].map(([value, label]) => `<div class="metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join("");
      $("limitations").innerHTML = (study.limitations || []).map((text) => `<div>${escapeHtml(text)}</div>`).join("");
      $("memoryStatus").innerHTML = renderMemory(study.memory || {});
      updateHookButton(study.memory || {});
      $("findingList").innerHTML = (study.findings || []).map(renderFinding).join("") || `<div class="notice">No review findings.</div>`;
      const events = ((study.replay || {}).events || []);
      $("timeline").innerHTML = events.map((event) => `
        <div class="event"><strong>${escapeHtml(event.turn || "Setup")}</strong> · ${escapeHtml(event.action)} · ${escapeHtml(event.raw)}</div>
      `).join("") || `<div class="event">No events parsed.</div>`;
      bindFindingButtons();
      filterFindings();
    }

    function renderMemory(memory) {
      const integration = memory.runtime_integration || {};
      const checkpointOnly = Number(memory.accepted_rule_count || 0) > 0 && !integration.active;
      $("integrationStatus").hidden = !checkpointOnly;
      $("integrationStatus").textContent = checkpointOnly ? "Approved rules are checkpointed but not loaded by this agent at runtime." : "";
      const cls = integration.active ? "good" : "warn";
      return `<div><strong>${escapeHtml(memory.checkpoint_id || "No checkpoint")}</strong> · ${escapeHtml(memory.accepted_rule_count || 0)} accepted · ${escapeHtml(memory.rejected_rule_count || 0)} rejected</div>
        <div class="status ${cls}" style="margin-top:7px">${escapeHtml(integration.status || "Integration unknown")}</div>`;
    }

    function updateHookButton(memory) {
      const integration = memory.runtime_integration || {};
      $("installHookBtn").hidden = integration.active || !memory.hook_install_supported;
    }

    function renderFinding(finding) {
      const status = finding.status || "pending";
      const turnLabel = typeof finding.turn === "number" ? `Turn ${finding.turn}` : finding.turn || "General";
      const playerLabel = typeof finding.player === "number" ? `Player ${finding.player + 1}` : finding.player || "";
      const actionButtons = finding.actionable && status === "pending" ? `
        <button type="button" class="accept" data-decision="accepted" data-finding="${escapeHtml(finding.id)}">Accept</button>
        <button type="button" class="reject" data-decision="rejected" data-finding="${escapeHtml(finding.id)}">Reject</button>
      ` : `<span class="status ${status === "accepted" ? "good" : status === "rejected" ? "bad" : "warn"}">${escapeHtml(status)}</span>`;
      const ruleEditor = finding.actionable ? `
        <details>
          <summary>Review proposed rule</summary>
          <textarea class="rule-editor" id="rule-${escapeHtml(finding.id)}">${escapeHtml(JSON.stringify(finding.proposed_rule || {}, null, 2))}</textarea>
          <input id="note-${escapeHtml(finding.id)}" placeholder="Reviewer note" value="${escapeHtml(finding.reviewer_note || "")}">
        </details>` : "";
      return `<article class="finding ${escapeHtml(status)}" data-finding-status="${escapeHtml(status)}">
        <div class="finding-head">
          <div><h3>${escapeHtml(finding.title)}</h3><div class="meta"><span>${escapeHtml(turnLabel)}</span><span>${escapeHtml(playerLabel)}</span></div></div>
          <div class="meta"><span class="status">${escapeHtml(finding.severity)}</span><span class="status">${escapeHtml(finding.confidence)} confidence</span></div>
        </div>
        <div class="text"><strong>Evidence:</strong> ${escapeHtml(finding.evidence)}</div>
        <div class="text muted">${escapeHtml(finding.explanation)}</div>
        ${ruleEditor}
        <div class="toolbar">${actionButtons}${finding.checkpoint ? `<span class="status good">${escapeHtml(finding.checkpoint)}</span>` : ""}</div>
      </article>`;
    }

    function bindFindingButtons() {
      document.querySelectorAll("[data-decision]").forEach((button) => {
        button.addEventListener("click", () => decide(button.dataset.finding, button.dataset.decision));
      });
    }

    function filterFindings() {
      const filter = $("findingFilter").value;
      let visible = 0;
      document.querySelectorAll("[data-finding-status]").forEach(item => {
        item.hidden = filter !== "all" && item.dataset.findingStatus !== filter;
        if (!item.hidden) visible += 1;
      });
      $("noFilteredFindings").hidden = visible > 0 || filter === "all";
    }

    async function decide(findingId, decision) {
      const ruleText = $(`rule-${findingId}`)?.value || "{}";
      let editedRule;
      try { editedRule = JSON.parse(ruleText); }
      catch { setStatus("Rule JSON is invalid", "bad"); return; }
      setStatus(decision === "accepted" ? "Saving checkpoint" : "Saving rejection", "warn");
      try {
        const result = await postJson("/api/study/decision", {
          study_id: state.study.study_id,
          finding_id: findingId,
          decision,
          edited_rule: editedRule,
          reviewer_note: $(`note-${findingId}`)?.value || ""
        });
        state.study = result.study;
        renderStudy();
        await loadCheckpoints();
        setStatus(decision === "accepted" ? "Checkpoint saved" : "Rejection saved", "good");
      } catch (error) {
        setStatus(String(error), "bad");
      }
    }

    async function loadCheckpoints() {
      const agent = $("agentSelect").value;
      if (!agent) return;
      try {
        const payload = await getJson(`/api/study/checkpoints?agent=${encodeURIComponent(agent)}`);
        $("memoryStatus").innerHTML = renderMemory(payload.memory || {});
        updateHookButton(payload.memory || {});
        $("checkpointList").innerHTML = (payload.checkpoints || []).map((checkpoint) => `
          <div class="checkpoint">
            <strong>${escapeHtml(checkpoint.checkpoint_id)}</strong>
            <div>${escapeHtml(checkpoint.rule)}</div>
            <div class="meta"><span class="muted">${escapeHtml(checkpoint.created_at)}</span><span class="status warn">${escapeHtml((checkpoint.validation || {}).status || "unknown")}</span></div>
            <button type="button" data-restore="${escapeHtml(checkpoint.checkpoint_id)}">Restore</button>
          </div>
        `).join("") || `<div class="checkpoint muted">No checkpoints.</div>`;
        document.querySelectorAll("[data-restore]").forEach((button) => {
          button.addEventListener("click", () => restoreMemory(button.dataset.restore));
        });
      } catch (error) {
        $("checkpointList").textContent = String(error);
      }
    }

    async function restoreMemory(checkpointId) {
      if (!confirm(`Restore ${checkpointId}? A new rollback checkpoint will preserve the current history.`)) return;
      setStatus("Restoring checkpoint", "warn");
      try {
        const payload = await postJson("/api/study/rollback", {
          agent: $("agentSelect").value,
          checkpoint_id: checkpointId
        });
        $("memoryStatus").innerHTML = renderMemory(payload.memory || {});
        await loadCheckpoints();
        setStatus("Checkpoint restored", "good");
      } catch (error) {
        setStatus(String(error), "bad");
      }
    }

    async function validateMemory() {
      setStatus("Validating memory", "warn");
      try {
        const payload = await postJson("/api/study/validate", { agent: $("agentSelect").value });
        const validation = payload.validation || {};
        const passed = validation.status === "structural_pass" || validation.status === "baseline_pass";
        await loadCheckpoints();
        setStatus(passed ? validation.message : "Validation failed", passed ? "good" : "bad");
      } catch (error) {
        setStatus(String(error), "bad");
      }
    }

    async function installHook() {
      if (!confirm("Install the deterministic study-rule hook into this imported agent? A backup of policy.py will be kept.")) return;
      setStatus("Installing rule hook", "warn");
      try {
        const payload = await postJson("/api/study/install-hook", { agent: $("agentSelect").value });
        $("memoryStatus").innerHTML = renderMemory(payload.memory || {});
        updateHookButton(payload.memory || {});
        setStatus("Runtime rule hook installed", "good");
      } catch (error) {
        setStatus(String(error), "bad");
      }
    }

    $("logFile").addEventListener("change", async (event) => {
      const file = event.target.files && event.target.files[0];
      if (file) $("logText").value = await file.text();
    });
    $("agentSelect").addEventListener("change", loadCheckpoints);
    $("findingFilter").addEventListener("change", filterFindings);
    $("analyzeBtn").addEventListener("click", analyze);
    $("baselineBtn").addEventListener("click", () => restoreMemory("baseline"));
    $("validateMemoryBtn").addEventListener("click", validateMemory);
    $("installHookBtn").addEventListener("click", installHook);
    loadStatus().then(async () => {
      const studyId = new URLSearchParams(location.search).get("study");
      if (!studyId) return;
      state.study = await getJson(`/api/study/session?id=${encodeURIComponent(studyId)}`);
      if (state.study.agent && state.agents.some((agent) => agent.spec === state.study.agent.spec)) {
        $("agentSelect").value = state.study.agent.spec;
      }
      $("logText").value = state.study.log_text || "";
      $("episodeSelect").value = state.study.episode_path || "";
      renderStudy();
      await loadCheckpoints();
      setStatus("Study loaded", "good");
    }).catch((error) => setStatus(String(error), "bad"));
  </script>
</body>
</html>
"""


STUDY_HTML = decorate_page(STUDY_HTML, "study")

__all__ = ["STUDY_HTML"]
