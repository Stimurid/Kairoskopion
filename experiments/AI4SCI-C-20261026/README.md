# AI4SCI-C — evaluator-drift research case (26 Oct 2026)

**Existing** [Kairoskopion / Trimurti case #79](https://github.com/Stimurid/Kairoskopion/issues/79). This is experimental research evidence for the original article family; **not** a separate publication engine, author-accepted ArticleSeed, World claim, or submission route.

## Research sources and version discipline

- Original **Iris** UCI data, 150 botanical observations × 4 numerical features, frozen raw SHA256 `6f608b71a7317216319b4d27b4d9bc84e6abd734eda7872b71a458569e2656c0` — [UCI raw CSV](https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data). The UCI original includes two entries subsequently corrected in scikit-learn; **do not mix editions**.
- Original **Wine** UCI data, 178 chemical measurements × 13 features, SHA256 `6be6b1203f3d51df0b553a70e57b8a723cd405683958204f96d23d7cd6aea659` — [UCI raw CSV](https://archive.ics.uci.edu/ml/machine-learning-databases/wine/wine.data).
- Historical counterpositions, with real raw PDF byte SHA and mandatory **in-body** citation for C01/C09: [Carlile 2002/2004, Star & Griesemer 1989, Galison source register](https://docs.google.com/document/d/1Bs98LbCtjcJp26oaPwysPA2_lPEeNEpbOnL_2N3sM88/edit).

## Immutable experiment, no retcon

1. Full preregistration: [EVAL-DRIFT P2, before first generator output](https://docs.google.com/document/d/1fDne12VOGTc1l_OdByOuN3Gnvcm9KFAuYX5eWicHzQU/edit). Lock files on owner AORUS: `evaldrift_P2/lock.json`, `design.json`, `holdout_vault.json` (the last file *never* supplied to the generator). Frozen original design SHA `75337bfacb25e06a6c6a2dac1bc566b4870a45792437dfe397c0719d46b258c0`; held-out gold SHA `b183da428436e43129205e823b66458466b58fc201c4d167c3e6ab800e216066`; lock receipt SHA `d0a0c71d922cf87f5e56bcb0e266484622335a39681b4a674eed1e112a428876`.
2. **Original** Qwen3.5:9b two-step proposal run was successful by full JSON contract for **5 of 8 task cases**, blocked for **3 of 8** by rationale overrun at exactly 420 output tokens. Original append-only raw generator SHA `d937a52256f21eb7612b725477b60d39991512a4464dcab88b5f60d0b0ec4238`. This scientific/engineering failure is permanently visible.
3. Only *after* seeing those failures, the prereg document explicitly added **posthoc exploratory P2b** recovery. `recover_p2b_numeric_only.py` extracts numerically complete weight vectors from two matching truncated responses without inventing a rationale, and makes **one** new development-only Qwen call for the never-issued WINE-41 second revision. Original 5/8 status **never becomes 8/8**; exploratory numeric histories are 8/8. Recovery SHA `a7299507c337d0f89587a64df711cd24ad21b8ef2f05cabe04c5e483c7eaa080`; new frozen policy history SHA `de48b651d6ae1c9bce7384e18e9a5e9c6f3decc18cc6bc905b29a5049c794176`.
4. A separate Phi4-mini:3.8b model performed all 48 hidden S/M/H × FULL/SUMMARY audit handoffs, raw SHA `328c215e3662c17079cb363a2d10e5e6f8ee68f34b311d579d8ce6ae698efa28`. Source/input/output cold readback SHA `760f2f2891bf522e981a9881729227c747b0cd98e9edfdf28e883aa71329a25a`.
5. A **separate NumPy implementation** (`verify_p2_independent_numpy.py`) recomputed all 80 development/holdout class-wise counts against UCI original bytes, split indices, and features. All 80 match, independently frozen receipt SHA `b7d5dbf4cd627e53001671a6e5029a2c9a75165fec5a2d0506d79a379877f874`.
6. Full interpretation and negative-case matrix: [P2 source, audit and science return](https://docs.google.com/document/d/1okZ4Vwb2OGXC8URqz2U4Bu8IHwSLcGvpN9fWtoce8xQ/edit).

## Actual scientific result

- 8/8 numeric M evaluator weights changed compared with initial uniform scoring, and differed from ordinary scripted H. Nevertheless, **0/8 selected classifier choices changed** among S/M/H, and **24/24** held-out case × condition choices met the pre-specified class-recall threshold 0.80. This is a negative test of the proposed **decision-level** effect, not proof of a novel mechanism.
- The local Phi4 audit mistakenly inferred NO change for **16/16** M/H cases with all three weights visible; only **5/24** positively valid cases were correctly recognized despite complete holdout evidence. With SUMMARY evidence missing, it appropriately abstained on criterion-change **6/24**, validity **2/24**. This is a model-specific **evidence-use failure**; not a universal LLM claim.
- The H control is *scripted*, not a person; there are no live labs, human investigators, or controlled effects on scientific subjectivity. All eight tasks use **easy teaching datasets**; no held-out negative selections, so this pilot could not test false scientific acceptance.
- Carlile, P. R. (2002), *Organization Science* 13(4), DOI [10.1287/orsc.13.4.442.2953](https://doi.org/10.1287/orsc.13.4.442.2953), and Carlile (2004), *Organization Science* 15(5), DOI [10.1287/orsc.1040.0094](https://doi.org/10.1287/orsc.1040.0094) already theorized failed metric transfer and knowledge boundaries; **cite both in body** of C01/C09 and do not rebrand their discoveries as “new machine epistemology.”

## Replay instructions, owner-private runtime

```powershell
python C:\projects\trimurti\_ops\AI4SCI-C-20261026\run_evaldrift_p2_uci.py freeze
# The original 'generate' stage has already run, and should NOT be replayed as a new independent trial.
python C:\projects\trimurti\_ops\AI4SCI-C-20261026\run_evaldrift_p2_uci.py verify
python C:\projects\trimurti\_ops\AI4SCI-C-20261026\verify_p2_independent_numpy.py
```

Original journal research routes stay **W3=3, R0 W12_EQUIVALENT_HELD=2, DEEP=0, ARTICLESEED_AUTHOR_ADMITTED=0, SEND=0**; source A/B/C v0.3 and World O/OD/I unchanged. Next experiment must pre-register difficult independent samples where conflicting criteria actually change the chosen action and a negative held-out case exists; do **not** retroactively change P2 success thresholds.
