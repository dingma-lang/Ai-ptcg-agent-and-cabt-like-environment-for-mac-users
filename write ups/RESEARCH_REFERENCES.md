# Research References and Claim Boundaries

For draft v8, use `PAPER_APPROVAL_CATALOG.md` and
`paper_approval_registry.json`: 17 papers are approved and seven excluded,
with no minimum count required. The notes below are historical research,
not an instruction to restore excluded citations to the current article.

Research companion for drafts v3-v4, not text to append wholesale to the 2,000-word
submission. Sources were checked online on September 9, 2026, local time.
These references contextualize our engineering; they do not independently
validate our agent or establish a competitive result.

## Best References for the Main Report

### 1. Expert Feedback on Agent-Visited States

Ross, S., Gordon, G., and Bagnell, D. (2011). **A Reduction of Imitation Learning
and Structured Prediction to No-Regret Online Learning.** AISTATS, PMLR 15,
627-635. [Primary paper and citation](https://proceedings.mlr.press/v15/ross11a.html).

The paper addresses distribution changes caused by a policy's own sequential
decisions. DAgger iteratively collects expert supervision on visited states.
This is relevant to asking the player to review actual failed turns rather
than only ideal openings. Our existing manual rule corrections are not DAgger:
we have not fitted and repeatedly retrained an imitation policy.

Use in: development loop and proposed offline learning. Useful future data:
complete match ID, observation, legal actions, expert alternatives, and label
confidence. Do not describe reviewing 14 decisions as a trained imitation model.

### 2. Reliable Evaluation with Few Runs

Agarwal, R., Schwarzer, M., Castro, P. S., Courville, A., and Bellemare, M. G.
(2021). **Deep Reinforcement Learning at the Edge of the Statistical
Precipice.** NeurIPS 34.
[Primary paper](https://arxiv.org/abs/2108.13264).

The authors demonstrate how few-run point estimates can mislead and advocate
uncertainty-aware reporting. This motivates exposing our three-game version
comparison and its uncertainty rather than emphasizing two random wins.
The paper studies deep RL benchmarks; we borrow evaluation discipline, not
its benchmark results or a claim that our policy uses reinforcement learning.

Use in: limitations, repeated trials, reporting variability. Our Wilson
calculation below is not the paper's full multi-task evaluation framework.

### 3. Confidence Intervals for Win Proportions

NIST/SEMATECH. **e-Handbook of Statistical Methods, Section 7.2.4.1:
Confidence intervals.**
[Official method and formula](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

The handbook provides the Wilson interval for proportions. Our audit implements
that formula with z = 1.959963984540054. For one win in three games, the
illustrative 95% interval is 6.1%-79.2%; for two wins in two, 34.2%-100%.
Independent Bernoulli sampling is an assumption, not a property established
by our convenience sample. These intervals do not correct seat bias,
opponent selection, unknown seeds, or repeated tuning.

Use in: results table and figure caption. Do not calculate uncertainty using
5,943 action rows as independent games. Do not interpret interval coverage as
a 95% posterior probability about our win rate.

### 4. Observation History and Partial Information

Kaelbling, L. P., Littman, M. L., and Cassandra, A. R. (1998).
**Planning and acting in partially observable stochastic domains.**
Artificial Intelligence 101, 99-134.
[Primary paper, university-hosted PDF](https://cs.brown.edu/courses/csci2951-k/papers/kaelbling98.pdf).

This provides the conceptual distinction between observations and underlying
state, with history informing decisions. In our game, hidden cards and
previous-turn attack restrictions make current visual appearance insufficient.
Our implementation tracks selected facts, not a complete Bayesian belief state
or an exact POMDP solution. An adversarial card game is not automatically the
paper's single-agent model without specifying the opponent's behavior.

Use in: state representation and hidden-information boundaries. Do not call
our dictionary memory a trained recurrent network.

### 5. Legal Action Constraints

Huang, S., and Ontanon, S. (2022; preprint 2020). **A Closer Look at Invalid
Action Masking in Policy Gradient Algorithms.** FLAIRS 35.
[Primary paper](https://arxiv.org/abs/2006.14171),
[publication DOI](https://doi.org/10.32473/flairs.v35i.130584).

The paper analyzes masking invalid actions in policy-gradient learning.
The analogous constraint in our system is narrower: cabt supplies legal
options, and the agent selects valid indices. No policy gradients are used.
If we train a ranker later, the legal action set must remain authoritative.

Use in: legal-option architecture or future training. The observed absence of
invalid indices does not imply strategically good choices or formally verified
agent correctness.

## Useful Supporting References

### 6. Learning from Human Preferences

Christiano, P. F., Leike, J., Brown, T. B., Martic, M., Legg, S., and Amodei, D.
(2017). **Deep reinforcement learning from human preferences.** NeurIPS 30.
[Primary paper](https://arxiv.org/abs/1706.03741).

This learns a reward model from human comparisons of trajectory segments.
Our review UI instead records preferred legal alternatives and comments.
That is a potential source of supervision, but neither a learned reward model
nor RLHF currently exists here. A future single-action ranker would be a
different, smaller formulation than reproducing the paper's pipeline.

Use in: future work. Retain ties, uncertainty, and multiple acceptable actions;
an expert annotation is not automatically an optimal-action oracle.

### 7. Interacting Rules and System Dependencies

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
Chaudhary, V., Young, M., Crespo, J.-F., and Dennison, D. (2015).
**Hidden Technical Debt in Machine Learning Systems.** NeurIPS 28.
[Primary proceedings page](https://proceedings.neurips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html).

The paper identifies system-level maintenance risks involving dependencies
and configuration, beyond the model itself. Our cross-deck rule carryover,
shortcut bypasses, and stale submission imports are related engineering
examples, not evidence of neural catastrophic forgetting.

Use in: discussion of regression risk and deployment provenance. Compare
code, tests, and packaged artifacts instead of assuming a new score means
new runtime behavior.

### 8. Game Research Infrastructure

Lanctot, M., et al. (2019). **OpenSpiel: A Framework for Reinforcement Learning
in Games.** [Primary paper](https://arxiv.org/abs/1908.09453).

OpenSpiel supports research across perfect- and imperfect-information games
and multiple planning/learning methods. It is a useful infrastructure reference
for separating game dynamics, agents, and evaluation. We do not use OpenSpiel
to simulate Pokemon: the official cabt engine remains the authority.

Use in: optional tooling discussion, not a claim about libraries we deployed.

### 9. The 2024 Nobel Physics Connection

Royal Swedish Academy of Sciences (2024). **The Nobel Prize in Physics 2024.**
[Official press-release PDF](https://www.nobelprize.org/uploads/2024/11/press-physicsprize2024-2.pdf).

The prize recognized Hopfield's associative-memory networks and Hinton's
contributions including Boltzmann machines. This is neural-network history,
not an explanation of our hand-authored policy or JSON checkpoints. It should
not be summarized simply as a prize for the RNN method used by our agent:
our agent has no such trained network.

Recommendation: keep this in background notes, not the main 2,000-word report.
DAgger, partial observability, and evaluation methodology are more directly
relevant to what we built and what we can test next.

## Citation Placement and Wording

- Cite local audit tables for our numbers, not academic papers that never
  evaluated this project.
- Cite papers beside the methodological claim, not as a decorative bibliography.
- Distinguish implemented behavior, reported player experience, and proposed
  experiments throughout.
- Describe current scores as heuristic preferences. Avoid "Q-values",
  "confidence", or "win probability" unless those quantities are actually
  learned or calibrated.
- The evidence supports a documented engineering process with measured
  limitations. It does not yet support "state of the art", guaranteed stronger
  play, automatic self-improvement, or statistically significant improvement.

## Additional Sources for the Mathematical Analysis

### 10. Exact Card-Access Probabilities

SciPy developers. **Hypergeometric distribution documentation.**
[Official formula](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.hypergeom.html).

The sampling-without-replacement model supports the opening-access calculations.
The actual counts come from our deck and organizer-derived metadata, not from
the documentation. Draft v4 conditions on a valid Basic-containing opening;
the supplement derives multi-group access with inclusion-exclusion. These are
offline analytic probabilities, not a newly fitted model or attack-success rate.

### 11. Logged Decisions Versus New-Policy Value

Jiang, N., and Li, L. (2016). **Doubly Robust Off-policy Value Evaluation for
Reinforcement Learning.** ICML, PMLR 48:652-661.
[Primary paper](https://proceedings.mlr.press/v48/jiang16.html).

This addresses evaluating a new policy from trajectories generated by another
policy. It provides relevant context for why our fixed-observation ablation is
not a win-rate experiment. We did not implement a doubly robust estimator or
importance weighting, and the sparse deterministic logs are not assumed to
provide the required coverage for such an estimate.

New analysis and experiment details are in `SCIENTIFIC_METHODS_AND_RESULTS.md`.
The numerical results belong to this project; papers support the methods and
interpretation, not independent validation of our agent.
