from __future__ import annotations

from typing import Any


def selection_contract(select: dict[str, Any]) -> dict[str, Any]:
    options = select.get("option")
    low, high = select.get("minCount"), select.get("maxCount")
    valid = (isinstance(options, list) and type(low) is int and type(high) is int
             and 0 <= low <= high <= len(options))
    return {"editable": valid, "min_count": low, "max_count": high,
            "unavailable_reason": "" if valid else "Legal options or selection limits were not recorded. Comment only."}


REVIEW_CSS = r"""
    .review-toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:8px; padding:10px 0; border-bottom:1px solid var(--line); }
    .review-toolbar select, .review-command { font:inherit; font-size:12px; min-height:34px; border:1px solid var(--line); border-radius:5px; background:white; padding:6px 10px; }
    .review-command.primary { background:var(--active); color:white; border-color:var(--active); }
    .review-command:disabled { opacity:.5; cursor:default; }
    .review-status { font-size:12px; color:var(--good); overflow-wrap:anywhere; }
    .review-warning, .review-error { color:var(--bad); }
    .review-editor { border-top:1px solid var(--line); padding-top:8px; }
    .review-editor > summary { color:var(--active); min-height:28px; }
    .review-body { display:grid; gap:8px; padding-top:8px; }
    .review-facts, .review-count { font-size:11px; line-height:1.5; margin:0; overflow-wrap:anywhere; }
    .review-filter, .review-comment { width:100%; min-width:0; font:inherit; font-size:13px; color:var(--ink); background:white; border:1px solid var(--line); border-radius:5px; padding:8px; }
    .review-comment { resize:vertical; min-height:70px; }
    .review-options { max-height:290px; overflow:auto; border-block:1px solid var(--line); }
    .review-option { display:grid; grid-template-columns:20px minmax(0,1fr); align-items:start; gap:7px; padding:9px 4px; border-bottom:1px solid #e4eaee; cursor:pointer; }
    .review-option:last-child { border-bottom:0; }
    .review-option:has(input:checked) { background:var(--active-soft); }
    .review-option:has(input:disabled) { opacity:.5; cursor:default; }
    .review-option input { margin:3px 0; accent-color:var(--active); }
    .review-option strong { display:block; color:var(--ink); font-size:12px; overflow-wrap:anywhere; }
    .review-option small { display:block; padding-top:3px; color:var(--muted); overflow-wrap:anywhere; }
    .review-footer { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
    .review-notice { font-size:11px; color:var(--muted); margin:0; }
    .review-editor.changed > summary { color:var(--good); }
"""


REVIEW_JS = r"""
    const reviewMeta = JSON.parse(document.getElementById('review-meta').textContent);
    const reviewActions = turns.flatMap(group => group.actions.map(action => ({...action, turn:group.turn, turn_label:group.label})));
    const reviewByFrame = new Map(reviewActions.map(action => [String(action.frame), action]));
    const reviewKey = `cabt-review-v1:${reviewMeta.id}`;
    let reviewDraft = {};
    let storageAvailable = true;
    let restoreWarning = '';

    function sameIndexes(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
    function reviewError(contract, indexes) {
      if (!contract.editable) return contract.unavailable_reason || 'Selection unavailable.';
      if (!Array.isArray(indexes) || indexes.some(i => !Number.isInteger(i) || i < 0 || i >= contract.options.length)) return 'Invalid option index.';
      if (new Set(indexes).size !== indexes.length) return 'Each option can be selected only once.';
      if (indexes.length < contract.min_count || indexes.length > contract.max_count) return `Select ${contract.min_count} to ${contract.max_count} options.`;
      return '';
    }
    function restoreReview() {
      try {
        const raw = sessionStorage.getItem(reviewKey);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (saved.id !== reviewMeta.id || saved.schema_version !== 1 || !saved.edits || typeof saved.edits !== 'object') throw new Error('Invalid draft');
        for (const [key, entry] of Object.entries(saved.edits)) {
          const action = reviewByFrame.get(key);
          if (!action || !entry || typeof entry.comment !== 'string' || !Array.isArray(entry.indexes)) { restoreWarning = 'Some stale draft entries were skipped.'; continue; }
          const c = action.review;
          const indexes = entry.indexes;
          if (indexes.some(i => !Number.isInteger(i) || i < 0 || i >= c.options.length) || new Set(indexes).size !== indexes.length ||
              (c.editable && indexes.length > c.max_count) || (!c.editable && !sameIndexes(indexes, c.original))) {
            restoreWarning = 'Some stale draft entries were skipped.'; continue;
          }
          reviewDraft[key] = {indexes:[...indexes], comment:entry.comment.slice(0, 4000), updated_at:entry.updated_at || ''};
        }
      } catch (error) { storageAvailable = false; restoreWarning = 'Draft storage unavailable; changes stay in this page until export.'; }
    }
    function persistReview() {
      try {
        if (Object.keys(reviewDraft).length) sessionStorage.setItem(reviewKey, JSON.stringify({schema_version:1, id:reviewMeta.id, edits:reviewDraft}));
        else sessionStorage.removeItem(reviewKey);
        storageAvailable = true;
      } catch (error) { storageAvailable = false; }
      updateReviewStatus();
    }
    function draftFor(action) {
      return reviewDraft[String(action.frame)] || {indexes:[...(action.review.original || [])], comment:''};
    }
    function storeReview(action, indexes, comment) {
      const key = String(action.frame);
      if (sameIndexes(indexes, action.review.original) && !comment.trim()) delete reviewDraft[key];
      else reviewDraft[key] = {indexes:[...indexes], comment:comment.slice(0,4000), updated_at:new Date().toISOString()};
      persistReview();
    }
    function reviewEntries() {
      return reviewActions.filter(action => Object.hasOwn ? Object.hasOwn(reviewDraft, String(action.frame)) : Object.prototype.hasOwnProperty.call(reviewDraft, String(action.frame)));
    }
    function entryError(action) {
      const entry = draftFor(action);
      return sameIndexes(entry.indexes, action.review.original) ? '' : reviewError(action.review, entry.indexes);
    }
    function updateReviewStatus() {
      const entries = reviewEntries();
      const errors = entries.filter(entryError);
      $('reviewStatus').textContent = `${entries.length} reviewed actions${errors.length ? ` | ${errors.length} incomplete selections` : ''} | ${storageAvailable ? 'Saved in this tab' : 'Page memory only'}`;
      $('reviewStatus').className = `review-status ${errors.length || !storageAvailable ? 'review-warning' : ''}`;
      $('exportReview').disabled = entries.length === 0 || errors.length > 0;
      $('clearReview').disabled = entries.length === 0;
      $('reviewNotice').textContent = restoreWarning || 'Annotations only. Original replay and agent unchanged.';
    }
    function reviewPanel(action) {
      const c = action.review;
      if (!c) return '';
      const draft = draftFor(action);
      const isChanged = !!reviewDraft[String(action.frame)];
      const multi = c.max_count !== 1;
      const facts = c.facts || {};
      const factNames = {supporterPlayed:'Supporter used', energyAttached:'Energy attached', retreated:'Retreat used', stadiumPlayed:'Stadium played'};
      const factsText = Object.entries(factNames).filter(([key]) => key in facts).map(([key, name]) => `${name}: ${facts[key] ? 'yes' : 'no'}`).join(' | ');
      const choiceRows = c.options.map(option => `<label class="review-option" data-review-row>
        <input type="${multi ? 'checkbox' : 'radio'}" name="review-${action.frame}" value="${option.index}" data-review-option="${action.frame}" ${draft.indexes.includes(option.index) ? 'checked' : ''}>
        <span><strong>#${option.index} ${esc(option.label)}</strong><small>${esc(option.detail)}${c.original.includes(option.index) ? ' | Original choice' : ''}</small></span></label>`).join('');
      const optional = c.editable && !multi && c.min_count === 0 ? `<label class="review-option"><input type="radio" name="review-${action.frame}" value="none" data-review-option="${action.frame}" ${draft.indexes.length ? '' : 'checked'}><span><strong>No selection</strong></span></label>` : '';
      return `<details class="review-editor ${isChanged ? 'changed' : ''}" data-review-frame="${action.frame}"><summary>${isChanged ? 'Review edited choice' : 'Review choice'}</summary><div class="review-body">
        ${c.effect ? `<strong>Effect: ${esc(c.effect.name)}</strong>` : ''}
        <p class="review-facts">${c.editable ? `Recorded limit: ${c.min_count}-${c.max_count} unique options | Bench spaces: ${facts.bench_spaces}` : esc(c.unavailable_reason)}</p>
        <p class="review-facts">${esc(factsText)}</p>
        ${c.remaining_energy_cost ? `<p class="review-facts">Remaining Energy cost: ${Number(c.remaining_energy_cost)}</p>` : ''}
        ${c.remaining_damage_counters ? `<p class="review-facts">Remaining damage counters: ${Number(c.remaining_damage_counters)}</p>` : ''}
        ${c.editable ? `<input class="review-filter" type="search" aria-label="Filter legal choices" placeholder="Filter legal choices" data-review-filter="${action.frame}"><div class="review-options">${optional}${choiceRows}</div>` : ''}
        <p class="review-count" data-review-count aria-live="polite"></p>
        <label for="review-comment-${action.frame}">Comment</label><textarea class="review-comment" id="review-comment-${action.frame}" maxlength="4000" data-review-comment="${action.frame}">${esc(draft.comment)}</textarea>
        <div class="review-footer"><button class="review-command" data-review-reset="${action.frame}">Reset this review</button><span class="review-notice" data-review-dependency></span></div>
      </div></details>`;
    }
    function syncReviewPanels() {
      const changed = reviewEntries().filter(action => !sameIndexes(draftFor(action).indexes, action.review.original)).map(action => action.frame);
      document.querySelectorAll('[data-review-frame]').forEach(panel => {
        const action = reviewByFrame.get(panel.dataset.reviewFrame);
        const c = action.review, draft = draftFor(action);
        const error = entryError(action);
        const counter = panel.querySelector('[data-review-count]');
        counter.textContent = c.editable ? `${draft.indexes.length} selected: [${draft.indexes.join(', ')}]${error ? ` | ${error}` : ''}` : '';
        counter.className = `review-count ${error ? 'review-error' : ''}`;
        panel.classList.toggle('changed', !!reviewDraft[String(action.frame)]);
        panel.querySelector('summary').textContent = reviewDraft[String(action.frame)] ? 'Review edited choice' : 'Review choice';
        panel.querySelectorAll('[data-review-option]').forEach(input => {
          input.disabled = c.max_count !== 1 && !input.checked && draft.indexes.length >= c.max_count;
        });
        panel.querySelector('[data-review-dependency]').textContent = changed.some(frame => frame < action.frame) ? 'Earlier action edited. These choices belong to the original position.' : '';
      });
      updateReviewStatus();
    }
    function reviewExport() {
      const entries = reviewEntries();
      if (!entries.length || entries.some(entryError)) throw new Error('Complete the selections before exporting.');
      const changes = entries.map(action => {
        const c = action.review, draft = draftFor(action);
        const describe = indexes => indexes.map(i => c.options[i]).filter(Boolean).map(o => ({index:o.index, label:o.label, detail:o.detail, option:o.option}));
        const earlier = entries.filter(a => a.frame < action.frame && !sameIndexes(draftFor(a).indexes, a.review.original)).map(a => a.frame);
        return {decision_index:action.frame, turn:action.turn, player_index:action.actor, context:action.context,
          original_action:action.title, effect:c.effect, original_indexes:c.original,
          proposed_indexes:draft.indexes, original_options:describe(c.original), proposed_options:describe(draft.indexes),
          selection_changed:!sameIndexes(draft.indexes,c.original), min_count:c.min_count, max_count:c.max_count,
          legality_scope:c.editable ? 'recorded decision window only' : 'comment only; no validated alternative',
          after_edited_decisions:earlier, comment:draft.comment, updated_at:draft.updated_at};
      });
      return {schema_version:1, type:'cabt_replay_review', replay:reviewMeta.name, replay_sha256:reviewMeta.id,
        exported_at:new Date().toISOString(), exported_local:new Date().toString(),
        notice:'Review annotations, not a simulated alternate battle. Each choice was checked only against its original legal window. Later positions and agent code are unchanged.', changes};
    }
    function reviewText(log) {
      const out = [`Battle review: ${log.replay}`, `Exported: ${log.exported_local}`, log.notice, ''];
      for (const c of log.changes) {
        out.push(`Turn ${c.turn} | Player ${c.player_index + 1} | Decision #${c.decision_index} | ${c.context}`);
        if (c.effect) out.push(`Effect: ${c.effect.name}`);
        out.push(`Original: ${c.original_action} [${c.original_indexes.join(', ')}]`);
        if (c.selection_changed) out.push(`Proposed: ${c.proposed_options.map(o => `#${o.index} ${o.label}${o.detail ? ` (${o.detail})` : ''}`).join('; ') || 'No selection'}`);
        else out.push('Choice unchanged.');
        out.push(`Selection limit: ${c.min_count}-${c.max_count} | ${c.legality_scope}`);
        if (c.after_edited_decisions.length) out.push('Dependency: earlier edits may change this position; re-simulation required.');
        if (c.comment) out.push(`Comment: ${c.comment}`);
        out.push('');
      }
      return out.join('\n');
    }
    function downloadReview() {
      try {
        const log = reviewExport();
        const json = $('reviewFormat').value === 'json';
        const blob = new Blob([json ? JSON.stringify(log, null, 2) : reviewText(log)], {type:json ? 'application/json' : 'text/plain;charset=utf-8'});
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url; link.download = `${reviewMeta.name.replace(/[^a-zA-Z0-9_.-]/g, '_')}_review.${json ? 'json' : 'txt'}`;
        document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (error) { $('reviewNotice').textContent = error.message; }
    }
    document.addEventListener('change', event => {
      const input = event.target.closest('[data-review-option]');
      if (!input) return;
      stop();
      const action = reviewByFrame.get(input.dataset.reviewOption), c = action.review, draft = draftFor(action);
      const index = input.value === 'none' ? null : Number(input.value);
      let indexes = [...draft.indexes];
      if (c.max_count === 1) indexes = index === null ? [] : [index];
      else if (input.checked && !indexes.includes(index) && indexes.length < c.max_count) indexes.push(index);
      else if (!input.checked) indexes = indexes.filter(i => i !== index);
      else input.checked = false;
      storeReview(action, indexes, draft.comment); syncReviewPanels();
    });
    document.addEventListener('input', event => {
      const comment = event.target.closest('[data-review-comment]');
      if (comment) {
        stop(); const action = reviewByFrame.get(comment.dataset.reviewComment);
        storeReview(action, draftFor(action).indexes, comment.value); syncReviewPanels(); return;
      }
      const filter = event.target.closest('[data-review-filter]');
      if (filter) filter.closest('[data-review-frame]').querySelectorAll('[data-review-row]').forEach(row => { row.hidden = !row.textContent.toLowerCase().includes(filter.value.toLowerCase()); row.style.display = row.hidden ? 'none' : ''; });
    });
    document.addEventListener('click', event => {
      const button = event.target.closest('[data-review-reset]');
      if (!button) return;
      const panel = button.closest('[data-review-frame]');
      delete reviewDraft[button.dataset.reviewReset]; persistReview();
      panel.outerHTML = reviewPanel(reviewByFrame.get(button.dataset.reviewReset)); syncReviewPanels();
    });
    // Editing must not be interrupted by timed playback or a full-page card re-render.
    document.addEventListener('toggle', event => { if (event.target.matches('[data-review-frame]') && event.target.open) stop(); }, true);
    $('exportReview').onclick = downloadReview;
    $('clearReview').onclick = () => { if (confirm('Clear all review choices and comments for this battle?')) { reviewDraft = {}; persistReview(); render(); } };
    restoreReview();
"""
