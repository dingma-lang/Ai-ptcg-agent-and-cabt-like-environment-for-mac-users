# Paper Approval Catalog

Of 24 candidates, **17 are approved, 7 excluded and none pending**. The first batch
approved P01/P02/P03/P05 and excluded P04/P06. The second batch approved
P07/P08/P09/P12 and excluded P10/P11. The final response excluded P15/P19/P22
and accepted all other remaining candidates. Previous exclusions are preserved.
Earlier discussion or a preselected chat option does not count as approval.
The user waived the 20-paper minimum. The active article uses only the approved
set; excluded entries below remain solely as the approval history.

The chat choices use the same P01-P24 identifiers. Each source was checked at the level stated below; this is not a claim that every proof or experiment was independently replicated. Paper findings, our interpretation and the project's current implementation are kept separate.

The article uses approximately 500 words for decks/development, 600 for AI
lessons/data and 300 for future work. No replacement papers or minimum count
are required. [Draft v8](cross_deck_strategy_draft_v8.md) cites 12 of the 17
approved papers to keep the argument focused. P03, P18, P20, P21 and P24 remain
approved background; omission from v8 does not revoke approval. Earlier drafts
may contain candidates subsequently excluded.

## Candidates

### P01: Planning and acting in partially observable stochastic domains

**Citation:** Kaelbling, L. P.; Littman, M. L.; Cassandra, A. R. (1998). Artificial Intelligence 101:99-134. [Primary source](https://cs.brown.edu/courses/csci2951-k/papers/kaelbling98.pdf).

**Summary:** Explains decision making from incomplete observations, belief states and finite-memory controllers.

**Project connection:** Hidden cards and prior attack events mean the current board alone is insufficient.

**Limit:** Our explicit event memory is not an exact POMDP solver; adversarial play requires an opponent model.

**Placement:** Section 2: state and memory. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary PDF, state-estimation and partial-observability sections.

### P02: Between MDPs and semi-MDPs: A framework for temporal abstraction in reinforcement learning

**Citation:** Sutton, R. S.; Precup, D.; Singh, S. (1999). Artificial Intelligence 112:181-211. [Primary source](https://www.sciencedirect.com/science/article/pii/S0004370299000521).

**Summary:** Introduces options: closed-loop behaviors extending over multiple primitive actions.

**Project connection:** A reset or transformation route has prerequisites, intermediate moves and a completion condition.

**Limit:** Our route rules resemble temporal abstraction, but no options policy was trained.

**Placement:** Sections 1-2: switching as a multi-step skill. **Priority:** Core. **Approval:** Approved.

**Source check:** Publisher abstract and primary PDF abstract.

### P03: Deep Recurrent Q-Learning for Partially Observable MDPs

**Citation:** Hausknecht, M.; Stone, P. (2015). AAAI Fall Symposium on Sequential Decision Making for Intelligent Agents. [Primary source](https://arxiv.org/abs/1507.06527).

**Summary:** Tests recurrent value networks on Atari and flickering observations; memory can improve robustness when observability changes.

**Project connection:** A possible future learned history representation for attack restrictions and revealed information.

**Limit:** It does not prove a recurrent network outperforms our explicit memory, or that recurrence always helps.

**Placement:** Section 2: explicit versus learned memory. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Author publication page and primary abstract.

### P04: Information Set Monte Carlo Tree Search

**Citation:** Cowling, P. I.; Powley, E. J.; Whitehouse, D. (2012). IEEE TCIAIG 4(2):120-143. [Primary source](https://pure.york.ac.uk/portal/en/publications/information-set-monte-carlo-tree-search/).

**Summary:** Develops search over information sets and tests it in three hidden-information game domains.

**Project connection:** Future tactical search must respect uncertainty rather than use omniscient simulator cards.

**Limit:** No ISMCTS implementation or runtime improvement has been demonstrated here.

**Placement:** Section 3: bounded hidden-information search. **Priority:** Core. **Approval:** Excluded.

**Source check:** University record and primary PDF introduction.

### P05: A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning

**Citation:** Ross, S.; Gordon, G.; Bagnell, D. (2011). AISTATS, PMLR 15:627-635. [Primary source](https://proceedings.mlr.press/v15/ross11a.html).

**Summary:** DAgger gathers expert supervision on states visited by the learner to address sequential distribution shift.

**Project connection:** Review actual agent failures, not only ideal opening hands.

**Limit:** Our expert-directed code patches are not DAgger training.

**Placement:** Section 2: expert-feedback loop. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary proceedings abstract.

### P06: Deep Q-learning from Demonstrations

**Citation:** Hester, T., et al. (2018). AAAI 32; preprint 2017. [Primary source](https://research.google/pubs/deep-q-learning-from-demonstrations/).

**Summary:** Combines supervised demonstration objectives with temporal-difference learning and prioritized replay.

**Project connection:** Demonstrations may provide a useful starting policy before costly autonomous exploration.

**Limit:** Atari results are not a predicted Pokemon benefit or a result of our manual rule system.

**Reported external data:** Better first-million-step scores than PDD DQN on 41 of 42 Atari games; exceeded the best supplied demonstration on 14 of 42.

**Placement:** Section 2: external demonstration-learning evidence. **Priority:** Core. **Approval:** Excluded.

**Source check:** Author-institution publication abstract.

### P07: Deep reinforcement learning from human preferences

**Citation:** Christiano, P. F., et al. (2017). NeurIPS 30. [Primary source](https://arxiv.org/abs/1706.03741).

**Summary:** Learns a reward model from human comparisons of short behavior segments.

**Project connection:** Our action-alternative review UI could collect supervision, with sequence-level comparisons added later.

**Limit:** We have no learned reward model; single-action labels differ from trajectory preferences.

**Reported external data:** The reported tasks used feedback on less than 1% of environment interactions.

**Placement:** Section 2: external human-feedback evidence. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary abstract and proceedings PDF abstract.

### P08: Learning to Rank using Gradient Descent

**Citation:** Burges, C., et al. (2005). ICML 2005; Microsoft Research MSR-TR-2005-06. [Primary source](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/).

**Summary:** RankNet learns a scoring function from pairwise ranking preferences.

**Project connection:** A compact action ranker could learn preferred legal choices from expert review.

**Limit:** The original experiments concern ranking, including search-engine data, not sequential game value.

**Placement:** Section 2: proposed pairwise learning objective. **Priority:** Core. **Approval:** Approved.

**Source check:** Author-institution abstract.

### P09: A Closer Look at Invalid Action Masking in Policy Gradient Algorithms

**Citation:** Huang, S.; Ontanon, S. (2022). FLAIRS 35; preprint 2020. [Primary source](https://arxiv.org/abs/2006.14171).

**Summary:** Analyzes invalid-action masking in policy-gradient algorithms.

**Project connection:** A learned selector should remain restricted to the cabt legal-choice set.

**Limit:** Our current legal-index wrapper is not a policy-gradient method.

**Placement:** Section 2: legality and learning. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary abstract.

### P10: Policy invariance under reward transformations: Theory and application to reward shaping

**Citation:** Ng, A. Y.; Harada, D.; Russell, S. (1999). ICML 1999. [Primary source](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf).

**Summary:** Establishes policy-preserving potential-based reward shaping under the paper's MDP assumptions.

**Project connection:** Future training should reward useful progress without incentivizing endless setup or switching.

**Limit:** Hand-authored score bonuses are not automatically potential-based or policy-preserving.

**Placement:** Section 3: safe intermediate training rewards. **Priority:** Core. **Approval:** Excluded.

**Source check:** Primary PDF abstract and introduction.

### P11: Hidden Technical Debt in Machine Learning Systems

**Citation:** Sculley, D., et al. (2015). NeurIPS 28. [Primary source](https://proceedings.neurips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html).

**Summary:** Describes maintenance risks from dependencies, entanglement, configuration and feedback loops.

**Project connection:** Cross-deck contamination, stale packaging and interacting guards are system problems.

**Limit:** These analogies do not turn software regressions into neural catastrophic forgetting.

**Placement:** Section 1: isolation and deployment. **Priority:** Core. **Approval:** Excluded.

**Source check:** Primary proceedings abstract.

### P12: The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction

**Citation:** Breck, E.; Cai, S.; Nielsen, E.; Salib, M.; Sculley, D. (2017). IEEE Big Data 2017. [Primary source](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/).

**Summary:** Proposes testing and monitoring practices for reliable deployed learning systems.

**Project connection:** Separate parsing, legality, strategic regressions and packaged-runtime verification.

**Limit:** Its rubric does not certify our agent or convert unit-test totals into performance.

**Reported external data:** The rubric contains 28 tests and monitoring needs; this is a framework count, not an experimental sample size.

**Placement:** Section 1: tests and deployment. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Author-institution abstract and primary PDF opening.

### P13: Deep Reinforcement Learning at the Edge of the Statistical Precipice

**Citation:** Agarwal, R.; Schwarzer, M.; Castro, P. S.; Courville, A.; Bellemare, M. G. (2021). NeurIPS 34. [Primary source](https://arxiv.org/abs/2108.13264).

**Summary:** Shows how few-run aggregate estimates can mislead; advocates intervals, robust summaries and performance profiles.

**Project connection:** Three version-comparison games cannot establish a reliable improvement.

**Limit:** Its Atari analysis does not prescribe a universal Pokemon sample size.

**Reported external data:** The case study evaluated five algorithms with 100 runs across 26 games, producing 26 x 100 scores per algorithm.

**Placement:** Section 2: uncertainty and sample size. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary PDF, Section 3 and evaluation recommendations.

### P14: Deep Reinforcement Learning That Matters

**Citation:** Henderson, P., et al. (2018). AAAI 32. [Primary source](https://ojs.aaai.org/index.php/AAAI/article/view/11694).

**Summary:** Investigates reproducibility and variation in deep-RL comparisons.

**Project connection:** Keep seeds, opponent policies, initialization and reported metrics controlled and visible.

**Limit:** Our deterministic action selector still faces stochastic games; the paper's algorithms were not used.

**Placement:** Section 2: evaluation design. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary proceedings abstract.

### P15: Doubly Robust Off-policy Value Evaluation for Reinforcement Learning

**Citation:** Jiang, N.; Li, L. (2016). ICML, PMLR 48:652-661. [Primary source](https://proceedings.mlr.press/v48/jiang16.html).

**Summary:** Studies estimating a new policy's value from data collected by another policy.

**Project connection:** Saved-state action changes do not directly determine the changed full-game outcome.

**Limit:** Our deterministic logs may lack coverage and action probabilities required for useful off-policy estimation; none was implemented.

**Placement:** Section 2: ablation versus win rate. **Priority:** Core. **Approval:** Excluded.

**Source check:** Primary proceedings abstract.

### P16: Deep TAMER: Interactive agent shaping in high-dimensional state spaces

**Citation:** Warnell, G.; Waytowich, N.; Lawhern, V.; Stone, P. (2018). AAAI 32. [Primary source](https://www.cs.utexas.edu/~pstone/Papers/bib2html/b2hd-AAAI18-Warnell.html).

**Summary:** Extends human-feedback modeling with neural representations for high-dimensional inputs.

**Project connection:** A concrete example of interactive feedback becoming a learned policy signal.

**Limit:** Its task, feedback format and sample efficiency do not establish a Pokemon training budget.

**Reported external data:** Reports training an Atari Bowling agent with 15 minutes of human feedback.

**Placement:** Section 2: external feedback data. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Author publication page abstract.

### P17: OpenSpiel: A Framework for Reinforcement Learning in Games

**Citation:** Lanctot, M., et al. (2019). Research framework paper, arXiv:1908.09453. [Primary source](https://arxiv.org/abs/1908.09453).

**Summary:** Describes shared game, agent, learning and evaluation infrastructure spanning multiple information structures.

**Project connection:** Supports clear boundaries between the official engine, deck policies and research tools.

**Limit:** We use cabt, not OpenSpiel, for Pokemon game dynamics.

**Placement:** Section 1: simulator and tooling. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Primary abstract.

### P18: DouZero: Mastering DouDizhu with Self-Play Deep Reinforcement Learning

**Citation:** Zha, D., et al. (2021). ICML, PMLR 139. [Primary source](https://proceedings.mlr.press/v139/zha21a.html).

**Summary:** Combines action encoding, self-play and deep Monte Carlo learning for a complex card game.

**Project connection:** Variable legal actions and hidden information can support learning when representation and infrastructure are designed for them.

**Limit:** DouDizhu differs from Pokemon; its reported leaderboard rank is historical, not a current ranking or our result.

**Reported external data:** Reports first place among 344 Botzone agents after days of training on a server with four GPUs.

**Placement:** Section 3: self-play feasibility and compute. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary proceedings abstract.

### P19: Combining Deep Reinforcement Learning and Search for Imperfect-Information Games

**Citation:** Brown, N.; Bakhtin, A.; Lerer, A.; Gong, Q. (2020). NeurIPS 33. [Primary source](https://arxiv.org/abs/2007.13544).

**Summary:** ReBeL combines public-belief-state reasoning, self-play and search for imperfect-information games.

**Project connection:** Longer-term planning must respect information structure rather than import perfect-information search assumptions.

**Limit:** Its convergence results have assumptions, and no comparable ReBeL implementation or poker-level result exists here.

**Placement:** Section 3: longer-term research. **Priority:** Supporting. **Approval:** Excluded.

**Source check:** Primary abstract and PDF introduction.

### P20: The Hanabi Challenge: A New Frontier for AI Research

**Citation:** Bard, N., et al. (2020). Artificial Intelligence 280:103216; preprint 2019. [Primary source](https://www.sciencedirect.com/science/article/pii/S0004370219300116).

**Summary:** Proposes a cooperative hidden-information benchmark and an evaluation framework for coordination.

**Project connection:** Evaluation should test interactions beyond familiar partners or opponents, not self-play alone.

**Limit:** Cooperative Hanabi and competitive Pokemon have different objectives; this is supporting benchmark context.

**Placement:** Section 3: generalization. **Priority:** Optional. **Approval:** Approved.

**Source check:** Primary publisher abstract.

### P21: Interactively Shaping Agents via Human Reinforcement: The TAMER Framework

**Citation:** Knox, W. B.; Stone, P. (2009). K-CAP 2009. [Primary source](https://www.cs.utexas.edu/~pstone/Papers/bib2html/b2hd-KCAP09-knox.html).

**Summary:** Learns a model of human evaluative reinforcement and uses it to guide actions.

**Project connection:** Distinguish scalar feedback, pairwise preferences and direct demonstrations in the study tool.

**Limit:** Free-text comments and manually edited JSON are not themselves a learned feedback model.

**Placement:** Section 2: feedback representation. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Author publication record and primary PDF abstract.

### P22: Hierarchical Imitation and Reinforcement Learning

**Citation:** Le, H.; Jiang, N.; Agarwal, A.; Dudik, M.; Yue, Y.; Daume III, H. (2018). ICML, PMLR 80:2917-2926. [Primary source](https://proceedings.mlr.press/v80/le18a.html).

**Summary:** Uses expert guidance at different planning levels for sparse-reward, long-horizon tasks.

**Project connection:** Label the goal of a switch sequence separately from the legal moves that implement it.

**Limit:** We implemented rules and route checks, not the paper's hierarchical learning algorithm.

**Placement:** Sections 1 and 3: sequence-level supervision. **Priority:** Core. **Approval:** Excluded.

**Source check:** Primary proceedings abstract.

### P23: A Survey of Preference-Based Reinforcement Learning Methods

**Citation:** Wirth, C.; Akrour, R.; Neumann, G.; Furnkranz, J. (2017). JMLR 18(136):1-46. [Primary source](https://jmlr.org/papers/v18/16-634.html).

**Summary:** Organizes preference-learning methods by feedback format, representation, optimization and exploration.

**Project connection:** Choose labels appropriate to the expert's knowledge, including uncertainty and multiple acceptable actions.

**Limit:** A survey supplies design context, not an empirical result for this agent.

**Placement:** Section 2: learning takeaways. **Priority:** Supporting. **Approval:** Approved.

**Source check:** Primary journal abstract.

### P24: Alpha-Rank: Multi-Agent Evaluation by Evolution

**Citation:** Omidshafiei, S., et al. (2019). Scientific Reports 9:9937. [Primary source](https://www.nature.com/articles/s41598-019-45619-9).

**Summary:** Ranks agents through empirical interactions and evolutionary dynamics, including cyclic strategic relationships.

**Project connection:** A multi-deck matchup matrix is more informative than a universal ranking inferred from one opponent.

**Limit:** Alpha-Rank has not been run here, and sparse matchup data would limit its usefulness.

**Placement:** Section 3: opponent populations and ranking. **Priority:** Core. **Approval:** Approved.

**Source check:** Primary article abstract and algorithm overview.

## External Data Suitable for a Table

| Candidate | Published result or study scale | Proper use |
| --- | --- | --- |
| P07, human preferences | Feedback on under 1% of interactions in reported tasks | An example of sparse supervision, not our label requirement |
| P13, statistical evaluation | Five algorithms, 100 runs and 26 games | Evidence that few-run conclusions need scrutiny |
| P16, Deep TAMER | 15 minutes of human feedback for Atari Bowling | Interactive-learning example; no transfer of the time budget |
| P18, DouZero | Historical rank 1 among 344 agents; four GPUs | Card-game learning feasibility and training-resource context |

Values are not commensurate and must not be plotted as a common performance ranking. Sources are linked in the corresponding candidate entries. None evaluated our Pokemon agents. P06's result is retained only in its excluded catalog entry, not proposed for the article.

## Background Not Counted Among the 24 Papers

The prior Nobel discussion remains background: associative-memory and Boltzmann-machine history do not describe our rule-based runtime. NIST's Wilson-interval handbook and SciPy's hypergeometric documentation remain method references, not research papers used to pad the paper count. No Efron paper is included in this shortlist because its full primary text was not accessible during this check.

Local evidence comes from [the cross-deck evidence map](CROSS_DECK_EVIDENCE.md), [the data audit](DATA_AUDIT.md), and [the scientific methods/results](SCIENTIFIC_METHODS_AND_RESULTS.md). The machine-readable status ledger is [paper_approval_registry.json](paper_approval_registry.json).
