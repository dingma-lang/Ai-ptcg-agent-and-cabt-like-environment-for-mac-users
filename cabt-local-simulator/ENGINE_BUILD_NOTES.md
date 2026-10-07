# Engine Recovery Notes

## What the HTML audit found

The browser app was started before implementation and its `/api/status` report showed:

1. `cg.game` was not importable in the local Python environment.
2. `cabt.game` was not importable in the local Python environment.
3. `kaggle_environments` was not installed.
4. Official wrapper source files still existed under the workspace's `sample_submission/cg/` folders.
5. The wrapper loads `libcg.so` or `cg.dll` through `ctypes`.
6. The available `libcg.so` is Linux x86-64 ELF and `cg.dll` is Windows PE/DLL. Neither is a macOS ARM64 library.

The official match engine was therefore not lost as Python source. The unavailable component was a compatible process in which to load the organizer's Linux x86-64 rules core.

## Official engine recovery

The Mac is Apple Silicon and has Rosetta installed. A private Lima 2.2.0 runtime now provides an ARM64 Linux VM using Apple's Virtualization framework. Rootless containerd launches a `linux/amd64` Python container with Lima's Rosetta device, where the unchanged organizer wrapper successfully loads `libcg.so`.

The verified worker reports:

- process architecture: `x86_64`
- Python: 3.11
- `kaggle-environments`: 1.32.7
- registered Kaggle environment: `cabt`
- official CABT visualizer: available
- cards from `all_card_data()`: 1,267
- attacks from `all_attack()`: 1,556

The browser's **Verify Environment** action starts a separate runtime process and executes `kaggle_environments.make("cabt").run(...)` with two official random agents. This tests environment registration, native engine startup, action stepping, and terminal rewards rather than relying on an import check alone.

`engine_worker/worker.py` owns the native process-global battle pointer. It serializes battle calls and exposes health, metadata, start, select, visualize, finish, and documented search operations on port 8780. Session IDs prevent stale callers from selecting into a different match, and search IDs are tracked and released independently.

`src/cabt_local/remote_engine.py` mirrors the `cg.game` method shape for the host runner. `src/cabt_local/local_runtime.py` manages the VM and worker. The browser starts and stops the worker without requiring engine commands in Terminal.

## What was rebuilt locally

`src/cabt_local/replay_engine.py` provides a deterministic, event-sourced replay engine. It accepts cabt/Kaggle text or visible HTML logs and exposes an event cursor, immutable state snapshots, parser coverage, and unparsed-line diagnostics.

`src/cabt_local/replay_visualizer.py` reconstructs public information from setup, turns, draws, board placement, searches to the Bench, evolutions, attachments, switches, attacks and abilities, damage, Special Conditions, Knock Outs, Prize taking, timeouts, and winner lines. Hidden cards remain hidden.

`src/cabt_local/webapp.py` displays the official engine, local runtime, and replay engine separately. `src/cabt_local/official_visualizer.py` turns native `VisualizeData()` frames into a standalone seekable battle board. The text-log replay view can seek to any event with first, previous, next, last, range, or timeline controls.

The web app also imports complete agent packages. A submission ZIP keeps `agent.py`, local helper modules, and `deck.csv` together; selecting that agent automatically supplies its deck to the match runner. Standalone Python agents can be paired with an explicit fallback deck. Agent code still runs in isolated spawned processes and every returned selection is checked against the current legal options.

## Build and verification process

1. Start the existing HTML app and save `/api/status` as the baseline.
2. Identify wrapper, package, operating-system, and CPU compatibility separately.
3. Audit real logs and count unclassified lines before adding parser rules.
4. Add one parser rule and one state transition for each recoverable public event.
5. Keep an `UNKNOWN` event and line-number report instead of guessing unfamiliar effects.
6. Build immutable snapshots after every parsed event so backward navigation cannot mutate later states.
7. Test text logs, HTML logs, plural Prize selection, Bench search, damage, promotion, and replay seeking.
8. Re-run the available real battle logs and the complete unit suite.
9. Execute the official Linux x86-64 engine locally through Lima/Rosetta.
10. Run browser-triggered random, file-agent, and mirror matches; verify winners, frame counts, decision counts, and invalid-response logs.

## Boundary

The reconstructed text-log replay engine does not generate legal options, calculate card effects, shuffle decks, or resolve attacks. Those responsibilities now run locally in the official cabt native engine. Native `VisualizeData()` contains complete replay information and is saved only as a local review artifact; agents still receive only their normal observation dictionaries.
