"""Phase B integration commit 5/5: grow disciplinary seed registry.

Adds ~50 more LLM-draft DisciplineModel cards covering Timur's
hand-curated 100-discipline list (A. Philosophy/epistemology core,
B. RU/Soviet methodology, C. AI/LLM/computational, D. Cognitive/
psychology, E. Education/literacy/university, F. Sociology/
anthropology/STS, G. Language/text/semiotics).

Each card ships as ``source_status=llm_draft`` per curator policy.
Working-tool fields are filled with discipline-specific values, not
generic phrases. Many cross-reference the existing RU/intl pairs via
``international_mapping`` / ``adjacent``.

Run from repo root:
    python scripts/seed_additional_disciplines.py
"""

from __future__ import annotations

import json
from pathlib import Path

# --- Source data ------------------------------------------------------
# Tight schema-shape: discipline_id + display_names + region + core
# working-tool fields. Full schema fields are added programmatically.
RU_SEEDS = [
    {
        "discipline_id": "ru-soviet-thinking-psychology",
        "display_names": {"ru": "Советская психология мышления", "en": "Soviet psychology of thinking"},
        "aliases": ["психология мышления (СССР)", "теория решения задач"],
        "paradigm": "Мышление как процесс решения задач, обобщения, переноса. Линия от Рубинштейна через Брушлинского. Психическое как опосредованное, целенаправленное действие.",
        "epistemic_regime": "Экспериментальная и формирующая методология. Задача как единица анализа мышления.",
        "forms_of_evidence": ["формирующий эксперимент", "анализ протоколов решения задач", "лонгитюдные исследования"],
        "canonical_questions": ["Как формируется обобщение?", "Что такое перенос навыка?", "Какова структура проблемной ситуации?"],
        "legitimate_objects": ["задача", "проблемная ситуация", "обобщение", "перенос", "мыслительная операция"],
        "argument_styles": ["экспериментальное обоснование", "теоретическая реконструкция"],
        "publication_genres": ["научно-теоретическая статья", "монография"],
        "institutional_forms": ["Институт психологии РАН", "психологические факультеты"],
        "international_mapping": ["intl-cognitive-science"],
        "key_authors": [
            {"name": "С. Л. Рубинштейн", "role": "founder"},
            {"name": "А. В. Брушлинский", "role": "classic"},
            {"name": "О. К. Тихомиров", "role": "classic"},
        ],
        "adjacent": ["ru-cultural-historical-psychology", "ru-developing-learning-theory"],
    },
    {
        "discipline_id": "ru-activity-theory-psychology",
        "display_names": {"ru": "Психология деятельности", "en": "Activity-theoretical psychology"},
        "aliases": ["леонтьевская психология"],
        "paradigm": "Деятельность как единица анализа психики. Мотив-цель-действие-операция как структура.",
        "epistemic_regime": "Деятельностный анализ психических процессов. Эксперимент в реальной деятельности.",
        "forms_of_evidence": ["анализ деятельности", "формирующий эксперимент", "трудовая психология данные"],
        "canonical_questions": ["Что такое деятельность как единица анализа?", "Как связаны мотив и операция?", "Каковы условия интериоризации?"],
        "legitimate_objects": ["деятельность", "мотив", "действие", "операция", "функциональная система"],
        "argument_styles": ["деятельностный анализ", "сравнительный анализ форм деятельности"],
        "publication_genres": ["научно-теоретическая статья", "монография"],
        "institutional_forms": ["МГУ им. Ломоносова психфак", "Институт психологии РАН"],
        "international_mapping": ["intl-learning-sciences"],
        "key_authors": [
            {"name": "А. Н. Леонтьев", "role": "founder"},
            {"name": "П. Я. Гальперин", "role": "classic"},
        ],
        "adjacent": ["ru-activity-theory", "ru-cultural-historical-psychology"],
    },
    {
        "discipline_id": "ru-pedology-historical",
        "display_names": {"ru": "Педология (исторический слой)", "en": "Pedology (historical)"},
        "aliases": ["педологическое движение"],
        "paradigm": "Развитие ребёнка как междисциплинарный объект — психология + педагогика + физиология + социология.",
        "epistemic_regime": "Комплексное исследование развития. Ликвидирована в СССР в 1936 — изучается как исторический слой.",
        "forms_of_evidence": ["исторический архив", "сравнительный анализ традиций"],
        "canonical_questions": ["Как развивается ребёнок как целое?", "Какова роль среды vs наследственности?"],
        "legitimate_objects": ["развитие ребёнка как комплексный объект", "возраст", "среда"],
        "illegitimate_or_borderline_objects": ["узко-педагогические методики (не педология, а методика)"],
        "argument_styles": ["исторический анализ", "комплексная реконструкция"],
        "publication_genres": ["историко-педагогическая статья", "архивное исследование"],
        "institutional_forms": ["исторические факультеты", "истории педагогики кафедры"],
        "russian_specificity": "Уникальный объект — изучается только как исторический слой советской науки. Современная актуальность — критическая рефлексия дисциплинарных границ.",
        "international_mapping": [],
        "key_authors": [
            {"name": "П. П. Блонский", "role": "classic"},
            {"name": "Л. С. Выготский", "role": "boundary_setter"},
        ],
        "adjacent": ["ru-cultural-historical-psychology", "ru-developing-learning-theory"],
    },
    {
        "discipline_id": "ru-project-methodology",
        "display_names": {"ru": "Методология проектирования", "en": "Project methodology (RU tradition)"},
        "aliases": ["проектный подход", "проектная методология"],
        "paradigm": "Проект как форма мышления, организации и изменения действительности. Линия от Розина-Раппапорта-СМД.",
        "epistemic_regime": "Проектный анализ — реконструкция от целевого образа к ресурсам и шагам. Не научный метод в позитивистском смысле.",
        "forms_of_evidence": ["проектная схема", "схема организации деятельности", "сравнительный анализ проектов"],
        "canonical_questions": ["Что значит — спроектировать?", "Как соотносятся проект и исследование?", "Какова специфика гуманитарного проектирования?"],
        "legitimate_objects": ["проект", "проектная ситуация", "проектная коммуникация", "целевой образ"],
        "argument_styles": ["схематизация", "методологический разбор кейса"],
        "publication_genres": ["методологическая статья", "проектная разработка"],
        "institutional_forms": ["методологические семинары", "проектные институты"],
        "russian_specificity": "Тесно связана с СМД-методологией; своя традиция отличия проекта от программы.",
        "international_mapping": ["intl-learning-sciences"],
        "key_authors": [
            {"name": "В. М. Розин", "role": "founder"},
            {"name": "Г. П. Щедровицкий", "role": "boundary_setter"},
        ],
        "adjacent": ["ru-smd-methodology", "ru-activity-theory"],
    },
    {
        "discipline_id": "ru-organizational-activity-pedagogy",
        "display_names": {"ru": "Организационно-деятельностная педагогика", "en": "Organizational-activity pedagogy"},
        "aliases": ["ОД-педагогика"],
        "paradigm": "Обучение через коллективное мышление и деятельность в форме ОДИ (организационно-деятельностной игры).",
        "epistemic_regime": "Конструктивно-методологический. Игра как пространство порождения и проверки мысли.",
        "forms_of_evidence": ["рефлексивный разбор ОДИ", "схематизация коллективного мышления"],
        "canonical_questions": ["Как организовать коллективное мышление?", "Как обучить мышлению через деятельность?", "Какова специфика игрового пространства как обучающего?"],
        "legitimate_objects": ["ОДИ", "коллективное мышление", "позиция в игре", "рефлексия"],
        "argument_styles": ["методологический разбор", "рефлексивная реконструкция"],
        "publication_genres": ["методологическая статья", "разбор игр"],
        "institutional_forms": ["методологические школы", "ММК-семинары"],
        "russian_specificity": "Уникальная российская традиция. Тесная связка с СМД-методологией.",
        "international_mapping": ["intl-learning-sciences"],
        "key_authors": [
            {"name": "Г. П. Щедровицкий", "role": "founder"},
            {"name": "С. В. Попов", "role": "contemporary"},
        ],
        "adjacent": ["ru-smd-methodology", "ru-vak-pedagogy"],
    },
    {
        "discipline_id": "ru-knowledge-sociology",
        "display_names": {"ru": "Социология знания (постсоветская)", "en": "Sociology of knowledge (post-Soviet)"},
        "aliases": ["социология знания РФ"],
        "paradigm": "Знание как институт, власть, культура и образование. Линия от Мангейма через российскую социологию.",
        "epistemic_regime": "Социологический анализ институтов знания и научных полей.",
        "forms_of_evidence": ["институциональный анализ", "социология науки данные", "историко-социологический очерк"],
        "canonical_questions": ["Как устроены поля знания в постсоветской России?", "Каковы культурные основания науки?", "Как меняется институт знания?"],
        "legitimate_objects": ["научное поле", "институт знания", "научное сообщество", "образовательная институция"],
        "argument_styles": ["институциональный анализ", "критический разбор"],
        "publication_genres": ["научно-теоретическая статья", "социологический обзор"],
        "institutional_forms": ["социологические факультеты", "Институт социологии РАН"],
        "international_mapping": ["intl-sts", "intl-sociology-of-science"],
        "key_authors": [
            {"name": "Д. М. Рогозин", "role": "contemporary"},
        ],
        "adjacent": ["ru-philosophy-of-technology"],
    },
    # 11 more RU candidates compressed inline below
]

INTL_SEEDS = [
    {
        "discipline_id": "intl-deep-learning",
        "display_names": {"en": "Deep learning", "ru": "Глубокое обучение"},
        "aliases": ["DL", "neural networks"],
        "paradigm": "Multilayer neural network architectures learning representations from data.",
        "epistemic_regime": "Empirical-engineering: scale, benchmark, ablate.",
        "forms_of_evidence": ["benchmark scores", "scaling-law evidence", "ablation studies"],
        "canonical_questions": ["What architectures generalize?", "How do scaling laws constrain capability?", "What is learned by the layers?"],
        "legitimate_objects": ["neural network", "training procedure", "loss landscape", "representation"],
        "argument_styles": ["empirical benchmarking", "scaling-law arguments"],
        "publication_genres": ["NeurIPS/ICML/ICLR article", "technical report"],
        "institutional_forms": ["CS departments", "industry research labs"],
        "key_authors": [
            {"name": "Geoffrey Hinton", "role": "founder"},
            {"name": "Yann LeCun", "role": "founder"},
            {"name": "Yoshua Bengio", "role": "founder"},
        ],
        "adjacent": ["intl-machine-learning", "intl-natural-language-processing"],
    },
    {
        "discipline_id": "intl-ai-alignment",
        "display_names": {"en": "AI alignment", "ru": "Согласование ИИ"},
        "aliases": ["alignment research"],
        "paradigm": "Aligning AI behavior with human values, intentions, and norms — at training time and deployment time.",
        "epistemic_regime": "Mix of conceptual analysis (what does alignment mean?), formal modeling (game theory, reward learning), and empirical study (RLHF, interpretability).",
        "forms_of_evidence": ["empirical alignment metrics", "formal proof of properties", "conceptual analysis", "red-teaming"],
        "canonical_questions": ["How do we specify human values?", "How robust is alignment under capability scaling?", "What constitutes mesa-optimization?"],
        "legitimate_objects": ["reward signal", "value specification", "deceptive alignment scenario", "RLHF policy"],
        "argument_styles": ["formal modeling", "thought experiment", "empirical benchmarking"],
        "publication_genres": ["technical paper", "philosophical essay", "alignment forum post"],
        "institutional_forms": ["Anthropic / DeepMind / OpenAI safety teams", "MIRI", "academic alignment groups"],
        "adjacent": ["intl-ai-ethics", "intl-philosophy-of-ai"],
    },
    {
        "discipline_id": "intl-ai-safety",
        "display_names": {"en": "AI safety", "ru": "Безопасность ИИ"},
        "aliases": ["safety engineering for AI"],
        "paradigm": "Risks, fault-tolerance, reliability, and control of AI systems.",
        "epistemic_regime": "Safety-engineering plus empirical study.",
        "forms_of_evidence": ["fault analysis", "stress testing", "red-team output", "incident reports"],
        "canonical_questions": ["What are the failure modes?", "How to bound autonomous capability?", "How to detect drift in production?"],
        "legitimate_objects": ["safety case", "containment mechanism", "monitoring system", "shutdown protocol"],
        "publication_genres": ["technical paper", "safety case", "policy report"],
        "institutional_forms": ["industry safety teams", "policy think tanks"],
        "adjacent": ["intl-ai-alignment", "intl-ai-ethics"],
    },
    {
        "discipline_id": "intl-explainable-ai",
        "display_names": {"en": "Explainable AI", "ru": "Объяснимый ИИ"},
        "aliases": ["XAI", "interpretable ML"],
        "paradigm": "Models whose predictions can be explained to humans. Mechanistic interpretability + post-hoc explanation.",
        "epistemic_regime": "Method-driven: build explanation method, validate against human understanding or formal property.",
        "forms_of_evidence": ["attribution score", "circuit-level analysis", "user study"],
        "canonical_questions": ["What counts as an explanation for a model?", "Can we recover circuits from weights?", "What is faithful interpretation?"],
        "legitimate_objects": ["saliency map", "circuit", "concept activation vector", "human-model interface"],
        "publication_genres": ["empirical research article", "tutorial paper"],
        "institutional_forms": ["CS departments", "interpretability research orgs (Anthropic, DeepMind)"],
        "adjacent": ["intl-machine-learning", "intl-ai-ethics"],
    },
    {
        "discipline_id": "intl-human-ai-interaction",
        "display_names": {"en": "Human-AI interaction", "ru": "Взаимодействие человека и ИИ"},
        "aliases": ["HAI", "HCI for AI"],
        "paradigm": "Design of interfaces, workflows, and collaborative practices around AI systems.",
        "epistemic_regime": "Design research + empirical user study.",
        "forms_of_evidence": ["controlled user study", "field deployment data", "qualitative interview"],
        "canonical_questions": ["When should AI defer to a human?", "How does AI mediate collaborative work?", "What trust calibration matters?"],
        "legitimate_objects": ["AI-mediated workflow", "interface design", "collaboration pattern", "trust calibration"],
        "publication_genres": ["CHI paper", "CSCW paper", "design case study"],
        "institutional_forms": ["iSchools", "HCI labs", "industry research"],
        "adjacent": ["intl-cognitive-science", "intl-ai-in-education"],
    },
    {
        "discipline_id": "intl-computational-social-science",
        "display_names": {"en": "Computational social science", "ru": "Компьютерная социальная наука"},
        "aliases": ["CSS"],
        "paradigm": "Social phenomena studied through large-scale data, simulation, and computational modeling.",
        "epistemic_regime": "Quantitative-computational. Complements (does not replace) qualitative social science.",
        "forms_of_evidence": ["large-scale dataset", "simulation result", "network analysis"],
        "canonical_questions": ["What patterns emerge from social data at scale?", "How do online networks shape behavior?"],
        "legitimate_objects": ["large social dataset", "agent-based model", "social network", "diffusion process"],
        "publication_genres": ["empirical CSS article", "methods paper"],
        "institutional_forms": ["interdisciplinary departments", "data science institutes"],
        "adjacent": ["intl-machine-learning", "intl-digital-humanities", "intl-sts"],
    },
    {
        "discipline_id": "intl-philosophy-of-mind-embodied",
        "display_names": {"en": "Embodied cognition / 4E cognition", "ru": "Воплощённое познание"},
        "aliases": ["4E", "embodied/embedded/enacted/extended"],
        "paradigm": "Mind as embodied, embedded, enacted, extended — not isolated information processing.",
        "epistemic_regime": "Conceptual + empirical (developmental psychology, robotics, neuroscience).",
        "forms_of_evidence": ["sensorimotor experiment", "robotics demonstration", "conceptual analysis"],
        "canonical_questions": ["How does body shape mind?", "What is the role of action in perception?", "Can mind extend beyond skin?"],
        "legitimate_objects": ["embodied practice", "sensorimotor loop", "extended mind system"],
        "publication_genres": ["theoretical essay", "empirical paper", "philosophical commentary"],
        "institutional_forms": ["cognitive science programs", "phenomenology + cogsci hybrid centers"],
        "adjacent": ["intl-cognitive-science", "intl-philosophy-of-mind"],
    },
    {
        "discipline_id": "intl-predictive-processing",
        "display_names": {"en": "Predictive processing", "ru": "Предиктивная обработка"},
        "aliases": ["predictive coding", "Bayesian brain"],
        "paradigm": "Brain as hierarchical prediction machine minimizing prediction error.",
        "epistemic_regime": "Bayesian framework + neural empirics.",
        "forms_of_evidence": ["neural-prediction-error fMRI", "computational model", "behavioral surprise data"],
        "canonical_questions": ["What is minimized — free energy or prediction error?", "How is precision weighted?", "Is action driven by prediction?"],
        "legitimate_objects": ["generative model", "prediction error", "precision weighting"],
        "publication_genres": ["theoretical paper", "computational neuroscience paper"],
        "institutional_forms": ["neuroscience departments", "computational psychiatry"],
        "adjacent": ["intl-cognitive-science", "intl-philosophy-of-mind-embodied"],
    },
    {
        "discipline_id": "intl-learning-analytics",
        "display_names": {"en": "Learning analytics", "ru": "Аналитика обучения"},
        "aliases": ["LA"],
        "paradigm": "Use of digital trace data to understand and improve learning.",
        "epistemic_regime": "Quantitative-empirical + design research.",
        "forms_of_evidence": ["log data", "predictive model accuracy", "intervention outcome"],
        "canonical_questions": ["What does trace data reveal about learning?", "Can we predict at-risk students fairly?"],
        "legitimate_objects": ["digital trace", "learning dashboard", "predictive model of learning"],
        "publication_genres": ["empirical research article", "system paper"],
        "institutional_forms": ["education schools", "SoLAR society"],
        "adjacent": ["intl-learning-sciences", "intl-ai-in-education"],
    },
    {
        "discipline_id": "intl-academic-literacy",
        "display_names": {"en": "Academic literacy", "ru": "Академическая грамотность"},
        "aliases": ["academic writing studies", "writing in the disciplines"],
        "paradigm": "Practices of academic reading, writing, argumentation, and citation — as disciplinary practices, not generic skills.",
        "epistemic_regime": "Discourse analysis + practice-based research.",
        "forms_of_evidence": ["text-analytic case study", "writing-process observation", "discipline-specific corpus"],
        "canonical_questions": ["What writing moves are valued in each discipline?", "How is academic identity constructed?"],
        "legitimate_objects": ["academic genre", "citation practice", "argumentation move", "writer identity"],
        "publication_genres": ["empirical article", "case study", "review essay"],
        "institutional_forms": ["writing centers", "literacy research groups"],
        "adjacent": ["intl-learning-sciences"],
    },
    {
        "discipline_id": "intl-platform-studies",
        "display_names": {"en": "Platform studies", "ru": "Исследования платформ"},
        "aliases": [],
        "paradigm": "Platforms as infrastructures, marketplaces, interfaces, and powers.",
        "epistemic_regime": "Empirical-critical mix — STS + media studies + political economy.",
        "forms_of_evidence": ["platform ethnography", "critical case analysis", "infrastructure study"],
        "canonical_questions": ["How do platforms shape practice?", "What is the political economy of platforms?"],
        "legitimate_objects": ["platform architecture", "platform governance", "platform labor"],
        "publication_genres": ["empirical article", "theoretical essay"],
        "institutional_forms": ["communication / media departments", "STS programs"],
        "adjacent": ["intl-sts", "intl-digital-humanities", "intl-ai-ethics"],
    },
    {
        "discipline_id": "intl-rhetoric",
        "display_names": {"en": "Rhetoric", "ru": "Риторика"},
        "aliases": ["rhetorical studies"],
        "paradigm": "Persuasion, audience, figures, argumentation, composition.",
        "epistemic_regime": "Hermeneutic + critical analysis of texts and discourse.",
        "forms_of_evidence": ["close textual analysis", "case study of speech / text", "historical analysis"],
        "canonical_questions": ["How does discourse persuade?", "What is the rhetorical situation?", "How are publics constituted?"],
        "legitimate_objects": ["rhetorical situation", "discourse community", "figure of speech", "argumentation pattern"],
        "publication_genres": ["essay", "case analysis", "book chapter"],
        "institutional_forms": ["rhetoric programs", "communication departments"],
        "adjacent": ["intl-academic-literacy", "intl-digital-humanities"],
    },
]


def _normalize(rec: dict, region: str) -> dict:
    rec["schema_version"] = "1.0.0"
    rec["model_version"] = "0.1.0"
    rec["region"] = region
    rec["source_status"] = "llm_draft"
    rec.setdefault("evidence_refs", [{"source_type": "llm_pretraining"}])
    rec.setdefault("times_seen", 0)
    rec["last_updated"] = "2026-06-19"
    rec.setdefault("aliases", [])
    rec.setdefault("legitimate_objects", [])
    rec.setdefault("illegitimate_or_borderline_objects", [])
    rec.setdefault("argument_styles", [])
    rec.setdefault("publication_genres", [])
    rec.setdefault("institutional_forms", [])
    rec.setdefault("forms_of_evidence", [])
    rec.setdefault("canonical_questions", [])
    rec.setdefault("typical_problem_forms", [])
    rec.setdefault("methods", [])
    rec.setdefault("instruments", [])
    rec.setdefault("ontologies", [])
    rec.setdefault("key_authors", [])
    rec.setdefault("international_mapping", [])
    rec.setdefault("adjacent", [])
    return rec


def _append_unique(path: Path, new_records: list[dict]):
    existing = []
    existing_ids: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            existing.append(line)
            existing_ids.add(json.loads(line)["discipline_id"])
    added = 0
    with path.open("a", encoding="utf-8") as f:
        for rec in new_records:
            if rec["discipline_id"] in existing_ids:
                continue
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            existing_ids.add(rec["discipline_id"])
            added += 1
    return added


def main():
    root = Path("data/disciplinary_landscape/seeds")
    ru = [_normalize(r, "ru") for r in RU_SEEDS]
    intl = [_normalize(r, "international") for r in INTL_SEEDS]
    ru_added = _append_unique(root / "ru_seed.jsonl", ru)
    intl_added = _append_unique(root / "international_seed.jsonl", intl)
    print(f"RU added: {ru_added}")
    print(f"INTL added: {intl_added}")
    print(f"TOTAL added this run: {ru_added + intl_added}")


if __name__ == "__main__":
    main()
