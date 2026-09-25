# Academic World Routing v1

Status: qualification branch; provider-side routing substrate for canonical ARTIKL.KAIRON.

## Graph

`WORLD / REGION_ECOLOGY → DISCIPLINE_FAMILY → DISCIPLINE / SUBDISCIPLINE → SCHOOL_TRADITION_TRIBE / DEBATE → VENUE_FAMILY → VENUE → SECTION / ISSUE / CFP → corpus/editorial/formal regime`.

The graph is multi-parent. Region, language, institutional network, indexing regime, intellectual lineage and citation ecology are separate coordinates. Regional labels route search; they never encode quality or author identity.

## Classifier stack

1. `discipline_intent_parsing_v2` — user intent × article evidence × protected core.
2. `discipline_matching_v3` — registry-backed discipline candidates and missing-discipline debt.
3. `disciplinary_mapping_v2` — parallel disciplinary publication trajectories.
4. `academic_world_resolution_v1` — local publication-ecology paths; no model-memory nodes.
5. `venue_funnel_planning_v2` — local venue families/candidates plus discovery tasks for gaps.
6. `venue_family_context_v2` — evidence-backed family neighborhood around a concrete venue.
7. `field_positioning` article/venue families — discipline, framework/school, citation, argument, method, audience, geography and institutional axes.
8. TargetWorld corpus/editor/formal modeling.
9. Kairon pressure reconciliation and reversible transition decision.

## Local-first memory

Search order is AcademicWorld graph → discipline registry → venue registry → frozen TargetWorld → VenueMemory → external acquisition. External discovery is illegal until the local receipt proves these checks.

Reusable knowledge is stored independently from article-specific pressure. A TargetWorld can be reused across articles when fresh; pressure packs, transition decisions, target variants and return passes remain per article.

## Seed status

The top-level ecology seed is `routing_scaffold` / low confidence. It only ensures that RF/post-Soviet, Anglophone, Francophone, Germanophone, East/South/Southeast Asian, African, MENA, Latin American/Iberophone and transregional routes can exist as first-class paths. Concrete norms require evidence-backed child nodes and source refs.
## Discipline registry projection

Existing DisciplineModel cards are now projected into AcademicWorldNode
records before academic-world lookup. The projection is status-preserving:
llm_draft remains llm_draft; it does not become accepted merely because it
is present in the graph. Regional parents are explicit routing ecologies
(ru -> ecology:ru-post-soviet, international -> ecology:transregional,
en-us/en-uk -> ecology:anglophone, eu-fr -> ecology:francophone,
eu-de -> ecology:germanophone). adjacent and international_mapping become
graph adjacency links.

The projection deliberately does not manufacture DISCIPLINE_FAMILY or
SCHOOL_TRADITION_TRIBE nodes. Those levels enter only from evidence-backed
local records, corpus analysis, or explicit source acquisition.
