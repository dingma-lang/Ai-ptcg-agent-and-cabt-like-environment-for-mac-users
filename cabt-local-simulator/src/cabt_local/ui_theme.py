"""Shared, offline presentation for the simulator, study and exported replays."""
from __future__ import annotations

import re

LUCIDE_LICENSE = "Lucide 0.468.0\nISC License\n\nCopyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2022.\n\nPermission to use, copy, modify, and/or distribute this software for any\npurpose with or without fee is hereby granted, provided that the above\ncopyright notice and this permission notice appear in all copies.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\" AND THE AUTHOR DISCLAIMS ALL WARRANTIES\nWITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF\nMERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR\nANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES\nWHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN\nACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF\nOR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE."

# Vendored Lucide 0.468.0 icons (ISC); license retained in THIRD_PARTY_NOTICES.md.
ICONS = {
    "arrow-left": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-arrow-left\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m12 19-7-7 7-7\" /> <path d=\"M19 12H5\" /> </svg>",
    "book-open": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-book-open\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M12 7v14\" /> <path d=\"M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z\" /> </svg>",
    "check": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-check\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M20 6 9 17l-5-5\" /> </svg>",
    "chevron-left": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-chevron-left\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m15 18-6-6 6-6\" /> </svg>",
    "chevron-right": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-chevron-right\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m9 18 6-6-6-6\" /> </svg>",
    "chevrons-left": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-chevrons-left\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m11 17-5-5 5-5\" /> <path d=\"m18 17-5-5 5-5\" /> </svg>",
    "chevrons-right": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-chevrons-right\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m6 17 5-5-5-5\" /> <path d=\"m13 17 5-5-5-5\" /> </svg>",
    "cpu": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-cpu\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <rect width=\"16\" height=\"16\" x=\"4\" y=\"4\" rx=\"2\" /> <rect width=\"6\" height=\"6\" x=\"9\" y=\"9\" rx=\"1\" /> <path d=\"M15 2v2\" /> <path d=\"M15 20v2\" /> <path d=\"M2 15h2\" /> <path d=\"M2 9h2\" /> <path d=\"M20 15h2\" /> <path d=\"M20 9h2\" /> <path d=\"M9 2v2\" /> <path d=\"M9 20v2\" /> </svg>",
    "download": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-download\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\" /> <polyline points=\"7 10 12 15 17 10\" /> <line x1=\"12\" x2=\"12\" y1=\"15\" y2=\"3\" /> </svg>",
    "folder-open": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-folder-open\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2\" /> </svg>",
    "layers": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-layers\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z\" /> <path d=\"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12\" /> <path d=\"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17\" /> </svg>",
    "pause": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-pause\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <rect x=\"14\" y=\"4\" width=\"4\" height=\"16\" rx=\"1\" /> <rect x=\"6\" y=\"4\" width=\"4\" height=\"16\" rx=\"1\" /> </svg>",
    "play": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-play\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <polygon points=\"6 3 20 12 6 21 6 3\" /> </svg>",
    "refresh-cw": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-refresh-cw\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8\" /> <path d=\"M21 3v5h-5\" /> <path d=\"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16\" /> <path d=\"M8 16H3v5\" /> </svg>",
    "search": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-search\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <circle cx=\"11\" cy=\"11\" r=\"8\" /> <path d=\"m21 21-4.3-4.3\" /> </svg>",
    "settings-2": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-settings-2\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M20 7h-9\" /> <path d=\"M14 17H5\" /> <circle cx=\"17\" cy=\"17\" r=\"3\" /> <circle cx=\"7\" cy=\"7\" r=\"3\" /> </svg>",
    "sparkles": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-sparkles\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z\" /> <path d=\"M20 3v4\" /> <path d=\"M22 5h-4\" /> <path d=\"M4 17v2\" /> <path d=\"M5 18H3\" /> </svg>",
    "swords": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-swords\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <polyline points=\"14.5 17.5 3 6 3 3 6 3 17.5 14.5\" /> <line x1=\"13\" x2=\"19\" y1=\"19\" y2=\"13\" /> <line x1=\"16\" x2=\"20\" y1=\"16\" y2=\"20\" /> <line x1=\"19\" x2=\"21\" y1=\"21\" y2=\"19\" /> <polyline points=\"14.5 6.5 18 3 21 3 21 6 17.5 9.5\" /> <line x1=\"5\" x2=\"9\" y1=\"14\" y2=\"18\" /> <line x1=\"7\" x2=\"4\" y1=\"17\" y2=\"20\" /> <line x1=\"3\" x2=\"5\" y1=\"19\" y2=\"21\" /> </svg>",
    "upload": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-upload\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\" /> <polyline points=\"17 8 12 3 7 8\" /> <line x1=\"12\" x2=\"12\" y1=\"3\" y2=\"15\" /> </svg>",
    "x": "<svg aria-hidden=\"true\" focusable=\"false\" class=\"lucide lucide-x\" xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" > <path d=\"M18 6 6 18\" /> <path d=\"m6 6 12 12\" /> </svg>"
}

THEME_CSS = r"""
:root {
  --ink:#243c37; --muted:#64736f; --line:#dce6e1; --panel:#f5f9f6;
  --soft:#f5f9f6; --white:#fff; --accent:#24745e; --accent-2:#a94f62;
  --active:#24745e; --active-soft:#e9f5ee; --good:#25704e; --green:#25704e;
  --warn:#805c18; --amber:#805c18; --bad:#b23e51; --red:#b23e51;
}
* { box-sizing:border-box; letter-spacing:0; }
[hidden] { display:none !important; }
body { background:#fff; color:var(--ink); font-size:14px; line-height:1.5; }
h1,h2,h3,p { overflow-wrap:anywhere; }
button,input,select,textarea { max-width:100%; }
button,a,input,select,textarea,summary { -webkit-tap-highlight-color:transparent; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible {
  outline:3px solid #a9c9f1; outline-offset:3px;
}
button { transition:background .15s,border-color .15s; }
button:disabled { cursor:not-allowed; opacity:.5; }
button:not(:disabled):hover { border-color:#80ab97; background:#edf6f0; }
button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
button.primary:not(:disabled):hover { background:#195941; }
button.secondary { background:#edf6f0; color:#24583f; border-color:#cfdfd4; }
button svg, a svg, summary svg { flex:none; vertical-align:middle; }
svg.lucide { width:18px; height:18px; stroke-width:1.8; }
.app-header {
  position:sticky; top:0; z-index:30; min-height:72px; height:auto;
  padding:12px 28px; display:flex; flex-wrap:wrap; gap:16px;
  border-bottom:1px solid var(--line); background:#fff;
}
.brand { display:flex; align-items:center; gap:11px; color:var(--ink); text-decoration:none; flex-shrink:0; }
.brand-mark { display:grid; place-items:center; width:40px; height:40px; border-radius:8px; background:#e4f2e9; color:#24745e; }
.brand-mark svg { width:23px; height:23px; }
.brand strong { display:block; font-size:18px; line-height:1.2; }
.brand small { display:block; font-size:11px; color:var(--muted); font-weight:500; }
.app-nav { display:flex; gap:6px; align-items:center; padding:0; background:none; border:0; overflow:visible; }
.app-nav a { display:flex; align-items:center; gap:7px; padding:8px 12px; border-radius:6px; color:var(--muted); font-size:13px; }
.app-nav a[aria-current="page"] { color:#205e47; background:#eaf4ed; }
.app-nav a:hover { background:#f4f7f5; }
.header-tools { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
.icon-button { display:inline-grid; place-items:center; width:38px; height:38px; min-height:38px; padding:0; border:1px solid var(--line); border-radius:6px; background:#fff; }
.page-heading { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px; margin-bottom:22px; }
.page-heading h1 { font-size:24px; line-height:1.25; margin:0; }
.eyebrow { color:var(--muted); font-size:11px; font-weight:700; text-transform:uppercase; margin:0 0 5px; }
.section-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:0 0 14px; }
.section-heading h2 { font-size:16px; margin:0; }
.fold { padding:0; margin:0; border:0; border-top:1px solid var(--line); }
.fold > summary { padding:15px 0; font-size:13px; font-weight:700; color:var(--ink); cursor:pointer; }
.fold > summary::marker { color:#82958b; }
.fold > summary svg { margin:0 7px 0 3px; }
.fold > .fold-body { padding:0 0 18px; min-width:0; }
.fold[open] > summary { color:var(--accent); }
.field { min-width:0; }
.field label { color:#53665e; font-size:12px; }
.field select,.field input { min-height:40px; font-size:13px; }
input[type="file"] { font-size:12px; overflow:hidden; }
input[type="file"]::file-selector-button { padding:7px 9px; border:0; border-radius:4px; background:#eef4f0; color:#345b48; margin-right:7px; }
select { text-overflow:ellipsis; }
textarea { line-height:1.6; }
.toolbar button { display:inline-flex; align-items:center; justify-content:center; gap:7px; }
.status { border-radius:6px; max-width:100%; overflow-wrap:anywhere; white-space:normal; }
.empty-view { display:grid; justify-items:center; gap:12px; text-align:center; padding:54px 20px; color:var(--muted); }
.empty-view > svg { width:56px; height:56px; color:#80a391; stroke-width:1.2; }
.empty-view h2 { margin:0; color:var(--ink); font-size:18px; }
.muted { color:var(--muted); }
.inline-status { font-size:13px; margin:0 0 16px; padding:10px 12px; background:#f1f7f3; border-left:3px solid #89af99; overflow-wrap:anywhere; }
.inline-status:empty { display:none; }
.inline-status.bad { background:#fff0f2; border-color:#ba5367; color:#97344b; }
table { table-layout:fixed; }
td,th { overflow-wrap:anywhere; }
button,select,input { border-radius:6px; }
body.simulator-page main,body.study-page main { grid-template-columns:320px minmax(0,1fr); min-height:calc(100vh - 73px); }
body.simulator-page main > aside,body.study-page main > aside { padding:24px; background:#f6f9f6; overflow:visible; min-width:0; }
body.simulator-page main > section,body.study-page main > section { padding:28px 32px; min-width:0; }
.match-form { padding-bottom:24px; }
.match-form h2 { font-size:18px; margin-bottom:20px; }
.agent-label { display:flex; align-items:center; gap:8px; }
.side-mark { display:inline-grid; place-items:center; width:23px; height:23px; border-radius:5px; font-size:11px; color:#32694c; background:#dceee2; font-weight:800; }
.side-mark.b { color:#97465d; background:#f6e3e9; }
.match-actions { display:grid; grid-template-columns:1fr auto; gap:8px; margin-top:18px; }
.match-actions button { min-height:43px; }
.match-actions .primary { display:flex; align-items:center; justify-content:center; gap:8px; }
.library-heading { display:flex; gap:12px; align-items:center; justify-content:space-between; margin-bottom:14px; flex-wrap:wrap; }
.library-heading h2 { margin:0; font-size:16px; }
.library-heading input { min-height:36px; padding:7px 10px; width:220px; font-size:13px; }
.battle-list { display:grid; }
.battle-row { display:grid; grid-template-columns:42px minmax(0,1fr) 22px; align-items:center; gap:14px; padding:15px 8px; border-bottom:1px solid var(--line); color:var(--ink); font-weight:500; }
.battle-row:hover { background:#f6faf7; }
.battle-art { width:40px; height:46px; border-radius:6px; border:1px solid #c3dccc; display:grid; place-items:center; background:#eaf4ed; color:#337551; }
.battle-row:nth-child(3n+2) .battle-art { background:#f8eaf0; border-color:#ead1dc; color:#a65d76; }
.battle-row:nth-child(3n) .battle-art { background:#fff5d6; border-color:#e7dbaf; color:#8a762e; }
.battle-row strong { display:block; font-size:14px; }
.battle-row small { display:block; margin-top:2px; color:var(--muted); font-size:12px; overflow-wrap:anywhere; }
.battle-row > svg { color:#81998c; }
.result-library { margin-bottom:24px; }
.deck-list { gap:8px; }
.deck-row { border-radius:6px; padding:10px; }
.output { background:#f5f7f5; color:#3e5246; height:auto; max-height:430px; }
.visualizer { margin:20px 0; }
.visualizer:empty { display:none; }
.player-board { border-top:3px solid #89b29a; }
.player-board:nth-child(2) { border-top-color:#d49bb0; }
.board-view { width:100%; }
.pill { border-radius:5px; }
.study-page .block { margin-bottom:18px; }
.study-page .summary-grid { gap:0; border-block:1px solid var(--line); margin:0 0 24px; }
.study-page .metric { background:transparent; padding:16px 12px; border-top:0; border-right:1px solid var(--line); }
.study-page .metric:last-child { border-right:0; }
.study-page .metric strong { font-size:26px; color:var(--ink); }
.study-page .metric:nth-child(2) strong { color:#967431; }
.study-page .metric:nth-child(3) strong { color:var(--good); }
.study-page .metric:nth-child(4) strong { color:#ac566d; }
.study-page .finding { padding:18px; gap:12px; border-radius:8px; border-left:4px solid #e5cd82; }
.study-page .finding.accepted { border-left-color:var(--good); }
.study-page .finding.rejected { border-left-color:var(--red); }
.study-page .finding h3 { font-size:15px; }
.study-page .finding-head { flex-wrap:wrap; }
.study-page .finding .meta { color:var(--muted); font-size:11px; margin-top:5px; }
.study-page button.reject { background:#fff; color:#934157; border-color:#e4c4ce; }
.study-page #analyzeBtn { width:100%; display:flex; align-items:center; justify-content:center; gap:8px; min-height:43px; }
.study-page #logText { min-height:220px; }
.study-page .notice { background:#fff8e3; border-color:#ceb05e; color:#655526; line-height:1.6; }
.study-page #emptyState { min-height:380px; }
.finding-tools { margin-bottom:16px; display:flex; gap:8px; }
.finding-tools select { width:auto; min-width:140px; }
body.replay-page main { grid-template-columns:176px minmax(360px,1fr) 330px; }
.replay-page main > nav { background:#f5f9f6; padding:16px 12px; }
.replay-page .turn-button { min-height:52px; padding:9px 10px; margin-bottom:3px; }
.replay-page .turn-button.current { background:#e4f2e8; border-color:#a8c9b4; color:#215d40; }
.replay-page .turn-button strong { font-size:13px; }
.replay-page .procedure { padding:24px; }
.replay-page .turn-heading h2 { font-size:22px; }
.replay-page main > aside { background:#fbfcfa; padding:18px; }
.replay-page .board-player { padding:12px 0; border:0; border-bottom:1px solid var(--line); border-radius:0; background:transparent; }
.replay-page .board-player-head { border-left:3px solid #6caa84; padding-left:8px; flex-wrap:wrap; }
.replay-page .board-player:nth-child(2) .board-player-head { border-color:#ca8da4; }
.replay-page .stats { font-size:11px; }
.replay-page .pokemon { border-radius:7px; padding:10px; background:#fff; min-height:76px; border-top:3px solid #b1cdbb; }
.replay-page .board-player:nth-child(2) .pokemon { border-top-color:#e5bed0; }
.replay-page .pokemon strong { font-size:13px; }
.replay-page .pokemon span { font-size:11px; }
.replay-page .hp { height:6px; }
.replay-page .action { padding:12px 0; border-bottom:1px solid var(--line); border-radius:0; }
.replay-page .action.current { background:#f3f9f4; box-shadow:inset 3px 0 #669976; }
.replay-page .action-number { background:#edf4ef; color:#4b715b; border-radius:6px; }
.replay-page .action.current .action-number { background:#e2eecf; color:#3f6435; }
.replay-page .action-jump { font-size:14px; line-height:1.5; }
.replay-page .thought { background:#f5f8fa; border-left-color:#99b4cd; border-radius:0; }
.replay-page .card-chip { background:#f8faf7; border-color:#dce6db; padding:6px 8px; min-height:31px; }
.replay-page .section-title h3 { font-size:14px; }
.replay-page .review-toolbar { background:transparent; border:0; border-bottom:1px solid var(--line); padding:10px 0 16px; }
.replay-page .context-section { min-width:0; }
.replay-page .fold { margin-top:10px; }
.replay-page .fold > summary { padding:12px 0; }
.replay-page .zone-controls { margin-top:12px; }
.replay-page .zone-players { gap:12px; }
.replay-page .controls .status { font-variant-numeric:tabular-nums; }
.replay-page .score-guide { margin-top:10px; }
@media (min-width:1101px) {
 .replay-page main > nav { position:sticky; top:73px; height:calc(100vh - 73px); }
 .replay-page main > aside { position:sticky; top:73px; max-height:calc(100vh - 73px); }
}
@media (max-width:1100px) {
 body.replay-page main { grid-template-columns:160px minmax(0,1fr); }
 .replay-page main > aside { grid-column:1/-1; grid-template-columns:repeat(2,minmax(0,1fr)); border-left:0; }
}
@media (max-width:800px) {
 .app-header { padding:12px 16px; gap:10px; }
 .app-nav a { padding:8px; }
 .brand strong { font-size:16px; }
 body.simulator-page main,body.study-page main { grid-template-columns:1fr; }
 body.simulator-page main > aside,body.study-page main > aside { padding:22px 20px; border-right:0; }
 body.simulator-page main > section,body.study-page main > section { padding:24px 20px; }
 .study-page .summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
 .study-page .metric { border-bottom:1px solid var(--line); }
 .grid,.board-view { grid-template-columns:1fr; }
 .header-tools { margin-left:auto; }
 .app-header .status { display:inline-flex; }
}
@media (max-width:720px) {
 .replay-page .app-header { position:static; flex-direction:row; align-items:center; }
 body.replay-page main { grid-template-columns:1fr; }
 .replay-page main > nav { max-height:160px; padding:10px 14px; }
 .replay-page .turn-list { display:flex; gap:6px; }
 .replay-page .turn-button { flex:0 0 140px; }
 .replay-page .procedure { padding:20px 16px; }
 .replay-page main > aside { grid-template-columns:1fr; grid-column:auto; }
 .replay-page .zone-players { grid-template-columns:1fr; }
 .replay-page .bench { grid-template-columns:repeat(2,minmax(0,1fr)); }
 .replay-page .controls { width:100%; }
 .finding-tools { flex-wrap:wrap; }
 .library-heading input { width:100%; }
 .battle-row { gap:10px; }
}
@media (prefers-reduced-motion:reduce) { * { transition:none !important; scroll-behavior:auto !important; } }
"""

def decorate_page(page: str, kind: str) -> str:
    """Inline shared assets so saved replay files also work offline."""
    assets = "<!-- " + LUCIDE_LICENSE + " -->\n<style>" + THEME_CSS + "</style>"
    page = page.replace("</head>", assets + "</head>", 1)
    page = page.replace("<body>", '<body class="' + kind + '-page">', 1)
    return re.sub(r"__ICON_([a-z0-9-]+)__", lambda match: ICONS[match.group(1)], page)
