# FieldPositionModel — Unified Coordinate System for Articles and Venues

## Замысел

Kairoskopion позиционирует статью для публикации. Для этого нужно знать
**где** статья находится в пространстве академического знания и **где**
находится журнал. Fit = отношение координат статьи к региону журнала.

Текущая модель — плоские теги (`schools_and_traditions: list[str]`).
Это не позволяет вычислить дистанцию, containment, или степень адаптации.
FieldPositionModel заменяет теги координатами.

## Принцип единого пространства

Одна и та же координатная модель (FieldPositionModel) описывает:
- **статью** — как точку или компактный регион
- **журнал** — как расширенный регион (envelope)
- **редакционную коллегию** — как набор точек (→ centroid + hull)
- **раздел журнала** — как подрегион журнала
- **дисциплину** — как регион верхнего уровня
- **страну/традицию** — как "тяготение" в методологическом и цитатном пространстве

Fit = containment статьи в регионе журнала + distance по осям,
где статья выходит за границы.

---

## Оси (Axes)

### Группа 1: Дисциплинарное позиционирование

#### 1.1 discipline_vector (многомерный)
Позиция в пространстве дисциплин. Не "одна дисциплина", а вектор
принадлежности к нескольким. Каждая компонента — доля принадлежности (0.0–1.0).

```
{
  "philosophy_of_technology": 0.7,
  "STS": 0.4,
  "media_studies": 0.2,
  "cognitive_science": 0.1
}
```

Для журнала — envelope (min–max по каждой компоненте):
```
{
  "philosophy_of_technology": [0.3, 1.0],
  "STS": [0.0, 0.5],
  "media_studies": [0.0, 0.3]
}
```

#### 1.2 subdiscipline_address
Уточняющий адрес внутри основной дисциплины: ниша, подполе, рабочая область.
Строковый (не координата), но структурированный — для matching.

```
{
  "primary": "philosophy of technology",
  "niche": "technical individuation",
  "working_area": "Simondon-inspired ontology of technical objects"
}
```

### Группа 2: Лагерное/трайбовое позиционирование

#### 2.1 school_affiliation_vector
Позиция в пространстве школ и традиций. Аналогична discipline_vector,
но описывает интеллектуальные лагеря.

```
{
  "Simondon": 0.9,
  "Stiegler": 0.3,
  "Heidegger": 0.2,
  "analytic_philosophy": 0.0,
  "posthumanism": 0.1
}
```

Для журнала — envelope:
```
{
  "continental_phenomenology": [0.3, 0.9],
  "analytic_philosophy": [0.0, 0.2],
  "STS_pragmatism": [0.1, 0.5]
}
```

#### 2.2 citation_network_signature
Кого цитируют, кого НЕ цитируют. Отсутствие — сигнал.

```
{
  "must_cite": ["Simondon", "Stiegler", "Leroi-Gourhan"],
  "typically_cite": ["Deleuze", "Latour", "Haraway"],
  "never_cite": ["Popper", "Dennett"],
  "conspicuous_absence": ["Heidegger"]  // цитируют все в лагере, кроме тебя
}
```

Для журнала:
```
{
  "canonical_must_cite": ["founding authors of the journal's tradition"],
  "bridge_traditions": ["X → Y"],
  "absent_traditions_risk": ["if you cite Z, this signals wrong camp"],
  "self_citation_norm": "5-10%"
}
```

#### 2.3 opponents_and_foils
Против кого работает текст. Явные и неявные оппоненты.
Для журнала — какие полемики он публикует, какие нет.

```
// article
{
  "explicit_opponents": ["technological determinism", "Heidegger's Gestell"],
  "implicit_foils": ["transhumanism", "naive instrumentalism"]
}

// venue
{
  "published_polemics": ["anti-reductionism", "critique of neoliberal tech"],
  "avoided_polemics": ["political philosophy direct engagement"]
}
```

### Группа 3: Аргументативный профиль

#### 3.1 argument_move_type
Тип интеллектуального хода (enum из 12 значений — уже определён
в semantic_profiling.py). Координатное значение = вектор, т.к.
одна статья может сочетать несколько ходов.

```
{
  "concept_reconstruction": 0.6,
  "disciplinary_translation": 0.3,
  "genealogy": 0.1
}
```

Для журнала — какие ходы публикуются (envelope):
```
{
  "concept_reconstruction": [0.0, 0.8],
  "empirical_conceptual_hybrid": [0.3, 1.0],
  "systematic_review": [0.0, 0.4]
}
```

#### 3.2 novelty_mode
Как статья позиционирует свою новизну.

```
{
  "mode": "reconceptualization",  // or: original_framework, critique, synthesis, application, meta_analysis
  "novelty_claim_strength": 0.7,  // 0 = none, 1 = paradigm shift
  "builds_on_or_opposes": "builds_on"
}
```

#### 3.3 evidence_type_profile
Какими данными оперирует текст.

```
{
  "theoretical_argument": 0.7,
  "textual_analysis": 0.2,
  "case_study": 0.1,
  "quantitative_data": 0.0,
  "experimental": 0.0,
  "archival": 0.0,
  "interview_ethnographic": 0.0
}
```

### Группа 4: Методологический регистр

#### 4.1 method_stance
Явный или неявный метод.

```
{
  "explicit_method": false,
  "method_family": "philosophical_analysis",
  "method_specificity": "low",  // low/medium/high
  "empirical_component": false
}
```

Для журнала:
```
{
  "requires_explicit_method": true,
  "accepted_method_families": ["mixed_methods", "case_study", "grounded_theory"],
  "rejected_method_families": ["pure_speculation"]
}
```

#### 4.2 formalization_level
Степень формализации: от свободного эссе до формальной модели.
Непрерывная шкала 0.0–1.0.

```
{ "value": 0.3 }  // philosophy paper = low; formal model = 0.9
```

### Группа 5: Аудитория и регистр

#### 5.1 audience_level
```
{
  "expertise_required": "specialist",  // general / educated / specialist / deep_specialist
  "presupposed_knowledge": ["Simondon's philosophy", "concept of individuation"],
  "accessibility_index": 0.3  // 0 = inaccessible, 1 = popular science
}
```

#### 5.2 language_register
```
{
  "language": "en",
  "register": "academic_formal",   // academic_formal / academic_accessible / semi_popular / popular
  "jargon_density": 0.7,           // 0 = plain, 1 = dense jargon
  "expected_word_count_range": [6000, 12000]
}
```

#### 5.3 genre_position
```
{
  "genre": "research_article",   // research_article, review, essay, commentary, note, book_review
  "genre_formality": 0.8,        // 0 = free-form essay, 1 = structured paper with IMRaD
  "sections_expected": ["introduction", "literature_review", "analysis", "conclusion"]
}
```

### Группа 6: Геополитика и институциональный контекст

#### 6.1 geographic_affinity
```
{
  "author_region": "Russia",
  "intellectual_tradition_region": "France",  // Simondon → French tradition
  "target_audience_region": "international",
  "language_of_publication": "en"
}
```

Для журнала:
```
{
  "editorial_board_regions": {"USA": 0.4, "UK": 0.2, "France": 0.15, "Germany": 0.1, ...},
  "author_regions_published": {"Europe": 0.6, "North_America": 0.3, ...},
  "anglophone_hegemony_index": 0.8  // 0 = multilingual, 1 = English-only
}
```

#### 6.2 institutional_signals
```
{
  "prestige_tier": "mid",  // top / mid / emerging / predatory / unknown
  "indexing": ["Scopus", "WoS"],
  "open_access": "hybrid",
  "apc_range_usd": [0, 3000],
  "review_model": "double_blind",
  "typical_decision_weeks": 12
}
```

### Группа 7: Темпоральность и стадия

#### 7.1 temporal_position
```
{
  "recency_of_core_references": "mixed",  // classic / mixed / recent / cutting_edge
  "median_reference_year": 2008,
  "reference_time_depth_years": 50,
  "field_maturity": "established_but_reviving"  // nascent / growing / established / declining / reviving
}
```

#### 7.2 article_readiness
```
{
  "manuscript_stage": "draft",    // idea / draft / presubmission / submitted / revision / accepted
  "completeness": 0.6,           // 0 = notes, 1 = camera-ready
  "word_count": 8500,
  "has_abstract": true,
  "has_bibliography": true,
  "has_methods_section": false,
  "formal_compliance_score": 0.4
}
```

---

## Вычисление Fit

### Containment
Для каждого вектора (discipline, school, argument_move, evidence_type):
- Статья внутри envelope → `contained`
- Статья вне envelope, но на малой дистанции → `adjacent` (адаптация возможна)
- Статья далеко за пределами → `outside` (глубокий reframe или другой журнал)

### Distance
Для скалярных осей (formalization_level, jargon_density, accessibility_index):
- |article_value - venue_center| / venue_half_width → нормализованная дистанция

### Weighted Fit Score (multi-axis)
НЕ один скаляр. Профиль из N дистанций, каждая с меткой:
```
{
  "discipline_fit": {"status": "contained", "distance": 0.1},
  "school_fit": {"status": "adjacent", "distance": 0.3, "closest_edge": "STS_pragmatism"},
  "argument_move_fit": {"status": "contained", "distance": 0.0},
  "method_fit": {"status": "outside", "distance": 0.8, "note": "venue requires explicit method"},
  "audience_fit": {"status": "contained", "distance": 0.15},
  ...
}
```

### Protected Core Risk
Для каждой оси, где статья `outside` или на большой дистанции:
- Можно ли адаптироваться без потери protected core?
- Если адаптация по оси X требует изменения protected core → `high_core_risk`

---

## Структура dataclass

```python
@dataclass
class FieldPositionModel:
    # Identity
    entity_type: str  # "article" | "venue" | "section" | "editor" | "discipline"
    entity_id: str

    # Group 1: Disciplinary
    discipline_vector: dict[str, float]       # article: point; venue: center
    discipline_envelope: dict[str, list[float]] | None  # venue only: [min, max] per dim
    subdiscipline_address: dict[str, str]

    # Group 2: Camp/Tribe
    school_affiliation_vector: dict[str, float]
    school_envelope: dict[str, list[float]] | None
    citation_network_signature: dict[str, list[str]]
    opponents_and_foils: dict[str, list[str]]

    # Group 3: Argument
    argument_move_vector: dict[str, float]
    argument_move_envelope: dict[str, list[float]] | None
    novelty_mode: dict[str, Any]
    evidence_type_profile: dict[str, float]

    # Group 4: Method
    method_stance: dict[str, Any]
    formalization_level: float

    # Group 5: Audience
    audience_level: dict[str, Any]
    language_register: dict[str, Any]
    genre_position: dict[str, Any]

    # Group 6: Geo/Institutional
    geographic_affinity: dict[str, Any]
    institutional_signals: dict[str, Any]

    # Group 7: Temporal
    temporal_position: dict[str, Any]
    article_readiness: dict[str, Any] | None  # articles only

    # Meta
    unknowns: list[str]
    confidence: str
    evidence_refs: list[str]
```

---

## Как используется

1. **Intake → ArticleModel → FieldPositionModel(article)**
   LLM-агент строит координаты из текста. Заменяет (или дополняет) плоские
   теги в ArticleSemanticProfile.

2. **Venue investigation → VenueModel → FieldPositionModel(venue)**
   Из aims/scope, editorial board, published corpus, guidelines.
   Envelope строится из корпусного анализа (или LLM-инференса при недостатке данных).

3. **Fit = compare(article_FPM, venue_FPM)**
   Не 16 отдельных текстовых осей, а вычислимые дистанции в одном пространстве.

4. **Mismatch = оси, где distance > threshold**
   Каждый mismatch приходит с указанием: "можно адаптировать" vs "core risk".

5. **Venue discovery = поиск журналов, чей envelope содержит или граничит
   с координатами статьи.**

6. **Variant planning = "куда можно сдвинуть координаты без core loss?"**

---

## Отличия от текущей модели

| Аспект | Сейчас | FieldPositionModel |
|--------|--------|--------------------|
| Дисциплина | `list[str]` теги | `dict[str, float]` вектор |
| Школа | `list[str]` теги | `dict[str, float]` вектор + citation signature |
| Аргумент | `str` enum | `dict[str, float]` вектор |
| Метод | `str` (status) | structured stance + formalization level |
| Аудитория | `str` | expertise + jargon + accessibility |
| Журнал | другая модель, другие поля | **та же модель**, но с envelopes |
| Fit | 16 текстовых осей | вычислимые дистанции в едином пространстве |
| Гео | нет | regions + anglophone hegemony index |
| Цитатная сигнатура | `list[str]` | must/typically/never/conspicuous absence |
| Оппоненты | `list[str]` | структура: explicit vs implicit |

---

## Миграционный путь

1. Написать `FieldPositionModel` dataclass в schema.py
2. Написать LLM prompt family: `field_positioning.py`
   - Один промпт для статьи (→ article FPM)
   - Один промпт для журнала (→ venue FPM)
3. Написать `field_position_fit.py` — вычисление fit из двух FPM
4. Связать с существующей FitAssessment (FPM → axes[])
5. Обновить GPT-5.5 бенчмарк-промпт: извлечение по всем осям FPM
6. ArticleSemanticProfile и VenuePublicationProfile остаются — FPM
   строится поверх них (или вместо, в следующей фазе)
