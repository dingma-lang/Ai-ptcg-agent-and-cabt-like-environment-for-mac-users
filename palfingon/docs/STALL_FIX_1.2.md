# Battle #15 Stall Fix: palfingon 1.2

Scope: palfingon only. No deck changes, other-deck edits, engine replacements,
runtime LLM calls, or automatic Battle Study approvals. Keep older ZIPs intact.

## Diagnosis

Reference: battle15_01-14_2026-09-08_sub_vs_sub, both seats using imported 1.1.
It completed 206 decisions and 41 engine turns without invalid responses.
Turns 12-26 contained 15 End selections; turns 19-26 were eight consecutive
pass-only turns. Turn ownership and Supporter flags were correct.

The turn-9 attack was a numeric log event (type 15, cardId 107, attackId 134,
serial 5). A text-only lock reader missed it. On turn 11, one heuristic requested
a reset but target scoring rejected every Bench choice equally at -18000.
Index order therefore promoted a Mega Dragonite missing Water. Rules then
rejected its free Sky Transport as well as paid retreat. Meanwhile, an estimated
Zero to Hero route vetoed Lillie; Judge judged hand size instead of usability;
and the under-500 override forced End. Legality tests alone missed the deadlock.

## Staged Changes

1. Lock tracking: read attack, switch, move, and turn-start events. Track the
   affected serial and exact next own turn (absolute attack turn + 2). Retain
   this map across prompts, separately for each observer. Clear after leaving
   Active, expiry, changed game ID, backwards turn counter, or setup handshake.
   A legal Giga Impact overrides stale inference. English fallback remains.
2. Movement: share destination utility between move initiation and target
   resolution. A free switch may escape a stranded Active, reach a powered
   attacker, or stage a productive pivot. Prefer Sky Transport to spending
   Switch for the same goal. Do not extend the paid-Dragonite-retreat ban to
   switch effects. Mandatory target resolution no longer rejects every target
   based on whether the initiating move would now be desirable. A Balloon
   Tatsugiri return pivot can be chosen without prior process memory.
3. Refresh and passing: Lillie defers to useful legal pre-refresh actions, not
   a speculative movement count. Judge/Lillie recognize large unproductive
   hands. The 500-point forced-End cutoff is removed; all-nonpositive choices
   still permit passing. The anti-stall check can identify a productive move
   independently of aggregate scores. Supporter diagnostics now distinguish
   legal-but-rejected cards from no legal Supporter.
4. Resource accounting: count the currently legal Stadium ability, not merely
   a Stadium sitting on the board. A newly playable Beach requires the Water
   pairing before being counted as an immediately available movement. Spent or
   unavailable retreat is not counted. These remain conservative heuristics,
   not a complete future-action search.
5. Speed: cache repeated damage and pre-refresh calculations within one
   immutable observation/decision only. New decision windows get a fresh cache.

## Regression Evidence

Curated original observations are in `tests/fixtures/battle15_stall.json`, with
the source episode SHA-256. They are excluded from the submission ZIP.

| Saved situation | Verified result |
| --- | --- |
| Turn 11 attack lock across three decision windows | Numeric event detected; lock retained after the attack log is no longer present |
| Turn 11 switch target | Balloon Tatsugiri, not the unpowered first Bench option |
| Turn 12 stranded Active Mega Dragonite | Uses its legal Sky Transport |
| Turn 13, two powered Palafin ex on Bench | Sky Transport -> powered Palafin -> legal Giga Impact KO |
| Same position, Sky unavailable but Switch legal | Uses Switch; does not pay Dragonite retreat Energy |
| Same position, no productive movement but Lillie legal | Refreshes the hand |
| Large dead hand with Judge only | Uses Judge |
| Only harmful Energy attachments remain | Still passes safely |

202 unit tests pass, including isolated submission import and the actual
battle-15 windows. Rechecking all 206 saved observations returns legal choices.
All 15 saved End decisions in turns 12-26 instead choose a legal movement.
This is an observation recheck, not a counterfactual replay of the same game:
after a changed action, future real observations would differ.

## Official-Engine Checks

- battle16_20-39_2026-09-08_pal_vs_pal: 146 decisions, 18 engine turns.
- battle17_20-39_2026-09-08_pal_vs_pal: 173 decisions, 18 engine turns.
- Both mirrors: 10 attacking turns each, no pass-only turns, all decisions
  traced, no invalid responses or engine error. Rechecking them with the
  optimized source reproduced every recorded choice.
- battle18_20-42_2026-09-08_pal_vs_ran: 114 decisions, 17 engine turns, win.

Local timing over battle-15 observations: approximately 11 ms median, 132 ms
p95, 267 ms maximum; excludes engine/IPC time and is not a hard real-time bound.
The final audit is in `local_results/stall_fix_1.2_validation.json`.

These small smoke samples establish progress and integration, not a proven
win-rate gain or freedom from every possible stall. Unknown effects, imperfect
future route estimates, and other deck families need their own regression logs.

## Use

Import `submission palfingon 1.2.zip` and choose the newly imported agent.
Existing imported 1.1 copies do not update automatically. The original battle
#15 and prior submission ZIPs are retained as comparison evidence.
