# UC-1 Demo Pack — Expected Behavior Notes

## What the demo should demonstrate

1. **Article modeling**: The draft article (Simondon/STS on AI publication positioning) is parsed into an ArticleModel with extracted title, abstract, keywords, methodology indicators, citation references, and word count.

2. **Semantic profiling**: The article's semantic profile identifies philosophy_of_technology, STS, and information_science as primary disciplines, with Simondon/individuation, evidence-bound design, and infrastructure studies as key conceptual clusters.

3. **Disciplinary pathway mapping**: Pathways should include philosophy_of_technology → STS → information_science, with potential crossover into AI_ethics and design_philosophy.

4. **Venue discovery**: From the 5 venue seeds, the system should identify all as potential matches, with Techné and Philosophy & Technology as strongest candidates (Simondon + philosophy of technology), Social Studies of Science as moderate (STS framing but lacks empirical grounding), AI & Society as moderate (AI theme but less philosophical depth expected), and Synthese as weaker (broad scope, less specialized).

5. **Fit assessment**: For the best-fit venue (expected: Philosophy & Technology), the system should report high fit on scope/methodology/citation overlap, with specific evidence from corpus and guidelines.

6. **Mismatch mapping**: Key mismatches to surface:
   - Social Studies of Science: article lacks empirical grounding (SSS expects ethnographic/historical methods)
   - AI & Society: article may be too philosophically dense for audience
   - Synthese: article's STS framing may not fit the formal epistemology tradition

7. **Evidence gaps**: The demo should explicitly flag what evidence is missing (e.g., no L5/L6/L7 depth data for any venue — reviewer behavior, outcome statistics, user experience memories).

## What the demo should NOT do

- Connect to any external API or network resource
- Use LLM inference (all analysis is deterministic/heuristic)
- Produce fabricated reviewer comments or editorial decisions
- Claim certainty where evidence is absent
