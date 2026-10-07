# Review Checklist for Cross-Deck Draft v8

This is an editorial companion, not part of the Kaggle report or its word count.
No agent, deck, submission archive, or approved study rule was changed.
The active draft is `cross_deck_strategy_draft_v8.md`, covering three deck strategies
in the requested approximately 500/600/300-word structure. `ARTICLE_REVIEW_v8.md`
records changes, evidence boundaries and remaining publication checks.
`PAPER_APPROVAL_CATALOG.md` and `paper_approval_registry.json` track 24 proposed
papers: 17 approved, seven excluded and none pending. The user waived the
20-paper minimum. The article cites 12 of the 17 approved papers; the other five
remain approved background sources, not newly excluded papers.
`PALFINGON_CURRENT_LOGIC.md` remains a technical appendix, not the article scope.
`CROSS_DECK_EVIDENCE.md` records historical checks;
`DATA_AUDIT.md` adds the current retrospective measurements and limitations.
`RESEARCH_REFERENCES.md` explains which claims each primary reference supports.
`SCIENTIFIC_METHODS_AND_RESULTS.md` supplies equations, exact deck probabilities,
and new isolated archive experiments. Its workbook is
`scientific_data/scientific_evidence.xlsx`.

## First Review

- [ ] Confirm the submitted entry the multi-deck development report will accompany.
      The current workspace matches all 76 packaged files; this is not proof
      of which artifact was actually uploaded to Kaggle.
- [x] Cover all development cases, merging the earlier and later Palafin ex
      deck iterations while preserving their distinct version histories.
- [x] Draft approximately 500 words on development, 600 on AI/data lessons,
      and 300 on future improvements.
- [x] Complete paper approval: 17 approved, seven excluded; minimum waived.
- [x] Reconcile article citations with the approved set.
- [x] Connect deck failures to diagnostic experiments and three testable next steps.
- [x] Keep the proposed ranking-loss objective in future work, not measured results.
- [x] Include one cross-deck comparison table and the preparation-ablation figure.
- [x] Distinguish implemented policy changes from offline analysis and future learning.
- [ ] Check the 1.20 -> 1.21 -> 1.22 explanation against your recollection;
      the code change is verified, but the score decline is a player report.
- [ ] Check that the opening, transformation, pivot, and Dragonite attack plans
      reflect your intended strategy, not only the implemented approximation.
- [x] Move the Nobel discussion to background references. The active draft prioritizes
      directly relevant research and measured failure cases.
- [x] Include the three imported 1.3-vs-1.2 games, including both losses.
- [x] Separate recorded legal selections from raw invalid-response sidecars,
      missing outcomes, pass-only turns, and true strategic errors.
- [x] Correct the opening-order description: smoke games reversed seats but
      the Palafin ex deck went first in both games.
- [ ] Review the explanation of decision 136: Water completion before Petrel,
      rather than claiming all 14 proposed indices were copied exactly.
- [x] Create an original aggregate-data figure without card artwork:
      `data/evidence_figure.png`. Source CSVs and plotting script are included.
- [ ] Approve the figure and caption before attaching them to the Writeup.
- [x] Add exact conditional opening probabilities using the actual deck and
      validate the formulas against exhaustive small-deck enumeration.
- [x] Compare frozen archives on 29 observations, with three repetitions and
      a one-function preparation-check ablation. All 348 calls returned legal
      indices; the ablation changed 6/14 reviewed choices.
- [x] Preserve distinct original expert and regression labels for decision 136.
- [x] Add score-discordance, typed Energy deficit, and pass-transition definitions
      with actual recorded counts and explicit statistical units.
- [x] Document the actual bounded Secret Box cost optimization: at most
      220 candidate triples, with recovery and Item-slot constraints.
- [ ] Review current-versus-earlier-request differences: conditional Poffin use,
      Dragonair's first-Energy priority, the ex-only energy-satisfaction helper,
      preparation before ordinary KOs, and additional productive switch routes.
- [x] Retain the ablation figure in v8; final user approval of its caption remains
      open above. Do not present development-set compliance as win rate.

## Evidence Still Needed

- [ ] Record the actual final Kaggle submission identity, track, score, and date.
      The draft deliberately supplies no invented leaderboard result.
- [ ] Run larger old-versus-new comparisons before claiming a win-rate gain.
- [ ] Test a wider opponent pool and weak openings, not only random and mirror.
- [ ] Extend the fixed-state preparation-hook ablation to balanced full games
      before attributing a competitive gain to that rule.
- [ ] Keep complete games separate between development and held-out evaluation.
- [ ] Label regression, smoke-test, and competitive-performance evidence separately.

## Local Evidence Sources

- `write ups/CROSS_DECK_EVIDENCE.md`: requested versus implemented behavior,
  archive comparisons, focused rechecks, and stale historical documentation.
- `write ups/DATA_AUDIT.md`: 41 summaries, 5,943 decisions, missing-data scope,
  three-game comparison, and a proposed controlled evaluation protocol.
- `write ups/data/match_inventory.csv`, `turn_metrics.csv`, and
  `audit_summary.json`: reproducible metrics and input SHA-256 manifest.
- `write ups/PALFINGON_CURRENT_LOGIC.md`: current 1.3 entry path, actual branch
  order, 25 card/printing roles, score offsets, bounded discard optimization,
  and explicit implementation limits.
- `write ups/RESEARCH_REFERENCES.md`: primary/official references with
  implemented-versus-proposed boundaries.
- `palfingon/docs/BATTLE_REVIEW_1.3.md`: 14 annotations, cost accounting,
  recorded test totals, latency and smoke games.
- `palfingon/docs/STALL_FIX_1.2.md`: battle 15's legal-but-unproductive turns.
- `palfingon/STRATEGY_NOTES.md`: card roles, exact attack costs, inherited scope.
- `cabt-local-simulator/ENGINE_BUILD_NOTES.md`: native-engine compatibility
  diagnosis and the official engine's Lima/Rosetta runtime.
- `palfingon/submission palfingon 1.3.zip`: verified archive SHA-256
  `c473bc1209b253be6b0f6604905d81dbc2972e9b8b69b9ee457c572a73a97863`.

## Before Publication

- [ ] Reconcile the report with whichever numbered archive is actually final.
- [ ] Recheck the 2,000-word limit after adding captions or editing in Kaggle.
- [ ] Keep the research and audit companions separate from the main word limit;
      do not append all their text to the report.
- [x] Supply an article title and subtitle.
- [ ] Select the required track in Kaggle.
- [ ] Confirm public attachments contain only material intended for release.
- [ ] Submit the Writeup, rather than leaving it saved as a draft.
- [ ] Keep claims precise: no trained RNN, RLHF, DAgger implementation,
  guaranteed stall elimination, or proven competitive improvement in 1.3.
