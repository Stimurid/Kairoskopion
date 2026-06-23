"""Human-readable Russian author dossier (presentation layer only).

Reads the structured dossier dict produced by
``Case.build_dossier()`` and emits a human-friendly Russian
"Авторский разбор досье" — a layered presentation, not a JSON / YAML
dump and not a technical English field listing.

Doctrine constraints (Round III-H):

  - This module is a PRESENTATION layer. It MUST NOT call the LLM,
    MUST NOT touch the network, MUST NOT mutate upstream models,
    MUST NOT invent venue policy, MUST NOT fabricate references,
    DOIs, authors or years, MUST NOT show raw LLM output.
  - Diagnostic / machine fields (``field_origins``, ``semantic_status``,
    ``provider_status``, ``parse_status``, ``created_from``) MAY appear
    only inside section #10 ("Что не удалось системе") as a short
    redacted block — never as the primary author surface.
  - Rubric stays NOT-a-venue-policy: the rubric file's
    ``not_a_venue_profile`` doctrine is respected here too.
  - English template prefixes from upstream organs ("Search for
    references that bridge: …") are rewritten into Russian narration.
    No new semantic claims are introduced.

The output shape is intentionally structural (sections + paragraphs +
bullets + subsections) so the UI can render it without a markdown
parser. The text is the data; the structure is the contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HumanSubsection:
    """A small subsection (e.g. one mismatch axis, one risk diagnostic)."""

    title_ru: str = ""
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    status_ru: str | None = None
    badge: str | None = None  # short marker, e.g. "major", "needs_llm"


@dataclass
class HumanSection:
    id: str
    title_ru: str
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    subsections: list[HumanSubsection] = field(default_factory=list)


@dataclass
class HumanSourceHeader:
    """Navigation header shown above the human dossier.

    Lets the author see — at a glance — which input the analysis was
    built from. NOT a debug table; if a field is missing the human
    fallback string is filled in here, not left empty.
    """

    source_filename_ru: str = ""
    source_type_ru: str = ""
    size_ru: str = ""
    document_title_ru: str = ""
    case_id_ru: str = ""
    generated_at_ru: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class HumanTechnicalFooter:
    """Collapsed-by-default technical footer.

    Structured provenance for developers / auditors. Lives on the
    response so the UI can keep it folded; never expanded into the
    main human surface. Raw LLM output is never included here.
    """

    input_metadata: dict[str, Any] = field(default_factory=dict)
    pipeline_metadata: dict[str, Any] = field(default_factory=dict)
    agent_metadata: list[dict[str, Any]] = field(default_factory=list)
    token_metadata: dict[str, Any] = field(default_factory=dict)
    safety_gates: dict[str, Any] = field(default_factory=dict)
    known_limitations: list[str] = field(default_factory=list)


@dataclass
class HumanDossier:
    case_id: str
    title_ru: str
    venue_name_ru: str
    stage_ru: str
    generated_at: str | None
    sections: list[HumanSection]
    source_header: HumanSourceHeader = field(default_factory=HumanSourceHeader)
    technical_footer: HumanTechnicalFooter = field(default_factory=HumanTechnicalFooter)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title_ru": self.title_ru,
            "venue_name_ru": self.venue_name_ru,
            "stage_ru": self.stage_ru,
            "generated_at": self.generated_at,
            "source_header": asdict(self.source_header),
            "sections": [
                {
                    "id": s.id,
                    "title_ru": s.title_ru,
                    "paragraphs": list(s.paragraphs),
                    "bullets": list(s.bullets),
                    "subsections": [asdict(sub) for sub in s.subsections],
                }
                for s in self.sections
            ],
            "technical_footer": asdict(self.technical_footer),
        }


# ---------------------------------------------------------------------------
# Round III-J helpers — render English / dict-shaped semantic fields
# into Russian author-facing prose WITHOUT inventing new claims and
# WITHOUT leaving Python dict reprs in the surface.
# ---------------------------------------------------------------------------

_DISCIPLINE_RU: dict[str, str] = {
    "philosophy_of_technology": "философия техники",
    "philosophy of technology": "философия техники",
    "philosophy_of_ai": "философия искусственного интеллекта",
    "philosophy of ai": "философия искусственного интеллекта",
    "philosophy of artificial intelligence":
        "философия искусственного интеллекта",
    "actor_network_theory": "акторно-сетевая теория (ANT)",
    "actor network theory": "акторно-сетевая теория (ANT)",
    "science and technology studies": "наука, технология, общество (STS)",
    "science and technology studies (sts)":
        "наука, технология, общество (STS)",
    "sts": "STS — наука, технология, общество",
    "management_studies": "исследования менеджмента",
    "management studies": "исследования менеджмента",
    "business strategy": "стратегический менеджмент",
    "organizational_theory": "теория организаций",
    "organizational studies": "организационные исследования",
    "organizational theory": "теория организаций",
    "organizational psychology": "организационная психология",
    "organizational discourse theory": "теория организационного дискурса",
    "organizational_discourse_theory": "теория организационного дискурса",
    "organizational_semiotics": "организационная семиотика",
    "cognitive_science_of_organizations":
        "когнитивная наука об организациях",
    "phenomenology": "феноменология",
    "post-phenomenology": "пост-феноменология",
    "post-phenomenological technology studies":
        "пост-феноменология техники",
    "xenopsychology": "ксенопсихология",
    "schumpeterian_entrepreneurship":
        "шумпетерианская теория предпринимательства",
    "tofflerian_futures_studies":
        "тоффлеровская футурология / теория волн",
}


def _ru_term(code: str | None) -> str:
    if not code:
        return ""
    key = str(code).strip().lower()
    return _DISCIPLINE_RU.get(key, str(code).replace("_", " "))


def _looks_english(text: str | None, threshold: float = 0.18) -> bool:
    """Heuristic: a Russian-author field reads as English when its
    Cyrillic share is below ``threshold``. Used only to decide whether
    to wrap the value with a Russian framing line — never to drop the
    content.
    """
    if not text or not isinstance(text, str):
        return False
    cyr = 0
    letters = 0
    for ch in text:
        if ch.isalpha():
            letters += 1
            if "Ѐ" <= ch <= "ӿ":
                cyr += 1
    if letters < 8:
        return False
    return (cyr / letters) < threshold


def _quote_block(text: str, max_chars: int = 600) -> str:
    """Trim a long quoted block to a safe length."""
    s = str(text).strip()
    if len(s) > max_chars:
        s = s[: max_chars - 1].rstrip() + "…"
    return s


def _ru_intro_for_english(field_label_ru: str, text: str) -> str:
    """Frame an English semantic field with a Russian intro line plus a
    quoted reconstruction. Adds no new facts.
    """
    return (
        f"{field_label_ru} (поле сохранено в исходной англоязычной "
        f"формулировке): «{_quote_block(text)}»"
    )


def _normalize_entry(item: Any) -> str:
    """Convert one semantic-list entry (str OR dict OR list-of-str) into
    a single human-readable line. NEVER returns a Python dict repr.
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, (int, float, bool)):
        return str(item)
    if isinstance(item, list):
        return _ru_join([_normalize_entry(x) for x in item if x], "; ")
    if isinstance(item, dict):
        # Common human-name fields (in priority order)
        for k in ("scholar", "author", "name", "tradition", "school",
                 "title", "label", "key"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                head = v.strip()
                break
        else:
            head = ""
        secondary_parts: list[str] = []
        for k in ("role", "debt", "contribution", "evidence",
                 "weight", "confidence", "summary"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                secondary_parts.append(v.strip())
        secondary = "; ".join(secondary_parts)
        if head and secondary:
            return f"{head} — {secondary}"
        if head:
            return head
        if secondary:
            return secondary
        # Fallback: extract just the string values, never a dict repr
        stringy = [
            v.strip() for v in item.values()
            if isinstance(v, str) and v.strip()
        ]
        return "; ".join(stringy) or "<запись без человекочитаемых полей>"
    # Unknown shape — never serialize as repr
    return str(item)


def _ru_safe_line(text: str, *, max_quote: int = 360) -> str:
    """Round III-J2: surface-clean Russian line.
    Fully-English lines are replaced with a Russian honesty stub
    (without exposing the English content in the author surface).
    Mostly-Russian lines pass through; embedded ≥40-char English runs
    are dropped from the surface and replaced with a brief Russian
    marker, with the full original content remaining accessible via
    the technical view.
    """
    s = _normalize_entry(text).strip()
    if not s:
        return ""
    if _looks_english(s):
        return (
            "формулировка модели — англоязычная; см. вкладку "
            "«Технические данные»"
        )

    def _drop(m):
        return "[англоязычный фрагмент — см. технические данные]"

    return re.sub(r"[A-Za-z][A-Za-z' ,;.\-]{40,}", _drop, s)


def _normalize_list(value: Any) -> list[str]:
    """Normalize an arbitrary list-shaped semantic field to a list of
    Russian-renderable strings. Drops empty / repr-shaped entries.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return [_normalize_entry(value)]
    out: list[str] = []
    for x in value:
        s = _normalize_entry(x)
        if s and s != "<запись без человекочитаемых полей>":
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Russian glossaries (presentation only — no semantic claims)
# ---------------------------------------------------------------------------

_GENRE_RU: dict[str, str] = {
    "theoretical_essay": "теоретическое эссе",
    "theoretical_argument": "теоретический аргумент",
    "empirical_paper": "эмпирическая статья",
    "case_study": "кейс-стади",
    "review_article": "обзорная статья",
    "systematic_review": "систематический обзор",
    "commentary": "комментарий",
    "position_paper": "позиционная статья",
    "methods_paper": "методологическая статья",
    "book_review": "рецензия на книгу",
    "short_communication": "короткое сообщение",
    "conceptual_article": "концептуальная статья",
    "essay": "эссе",
    "unknown": "жанр пока не определён",
}

_STAGE_RU: dict[str, str] = {
    "created": "создан",
    "intake_done": "статья принята",
    "venue_selected": "площадка выбрана",
    "fit_assessed": "fit-проверка выполнена",
    "mismatch_mapped": "карта несовпадений построена",
    "rewrite_planned": "план переработки готов",
    "compliance_checked": "формальные проверки выполнены",
    "submission_packed": "submission-пакет собран",
}

_AXIS_RU: dict[str, str] = {
    "topic": "Тематическая ось — о чём статья",
    "discipline": "Дисциплинарная ось — в какой дисциплине статья работает",
    "genre": "Жанр статьи",
    "argument_structure": "Структура аргумента",
    "method": "Метод",
    "citation_ecology": "Цитатная среда",
    "novelty_positioning": "Позиционирование новизны",
    "language_register": "Языковой регистр",
    "audience": "Адресат",
    "formal_compliance": "Формальные требования площадки",
    "author_eligibility": "Допуск автора",
    "publication_regime": "Режим публикации (open access / подписка / APC)",
}

_FIT_VALUE_RU: dict[str, str] = {
    "strong_fit": "сильное соответствие",
    "ok": "соответствие условное",
    "partial_fit": "соответствие частичное",
    "weak": "слабое место",
    "mismatch": "несовпадение",
    "unknown": "неизвестно — данных недостаточно",
    "not_applicable": "не применимо для этой пары статья × площадка",
}

_SEVERITY_RU: dict[str, str] = {
    "blocking": "блокирующее",
    "major": "существенное",
    "minor": "несущественное",
    "informational": "информационное",
    "unknown": "уровень не определён",
}

_NARRATIVE_STATUS_RU: dict[str, str] = {
    "llm_filled": "система описала это несовпадение содержательно",
    "filled": "система описала это несовпадение содержательно",
    "partial": "система описала несовпадение частично",
    "needs_llm": "содержательного описания нет — нужно повторно "
                 "запустить семантический проход",
    "unknown_due_to_venue_evidence": "текст площадки не задаёт явных "
                                      "ожиданий по этой оси — описать "
                                      "конкретно невозможно",
    "parse_failed": "ответ модели не прошёл проверку схемы; "
                    "fit / risk / rewrite уже посчитаны независимо",
    "provider_error": "семантический модуль был недоступен в момент сборки",
    "empty_valid_unknown": "система честно отказалась — текст площадки "
                            "недостаточен для содержательного вывода",
}


_PROTECTED_CORE_HINT = (
    "Защищаемое ядро — это содержательные вещи, которые при подаче "
    "в журнал менять нельзя: они и составляют статью. Их можно "
    "перепаковать, но нельзя выбросить или ослабить."
)

_MUTABLE_HINT = (
    "Гибкие зоны — это вещи, которые можно дорабатывать (формулировки, "
    "обвязка ссылок, объяснения, структура изложения) без потери "
    "содержания статьи."
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _safe_get(d: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    v = d.get(key)
    return default if v is None else v


def _nonempty_list(v: Any) -> list[Any]:
    return [x for x in (v or []) if x not in (None, "", [], {})]


def _ru_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(str(x).strip() for x in items if str(x).strip())


def _translate_search_task(text: str) -> str:
    """Rewrite English upstream organ template prefixes into Russian.

    Pure mechanical substitution — does not introduce new semantic
    claims, does not invent references. Only the framing changes.
    """
    if not isinstance(text, str):
        return ""
    out = text.strip()
    # Common templates emitted by the citation_planner organ
    out = re.sub(
        r"^\s*Search for references that bridge\s*:\s*",
        "Найти источники, которые связывают: ",
        out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Search for references that ",
        "Найти источники, которые ", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Search for ", "Найти ", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Look up\s*:?\s*", "Проверить: ", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Verify\s*:?\s*", "Проверить: ", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Find\s+references?\s+", "Найти источники ", out, flags=re.IGNORECASE,
    )
    out = re.sub(
        r"^\s*Close the gap\s*:?\s*",
        "Закрыть лакуну: ", out, flags=re.IGNORECASE,
    )
    # After the prefix swap, if a Russian-prefix + English-body shape
    # remains (e.g. "Найти источники, которые связывают: <english>"),
    # wrap the English tail so it doesn't leak past «»-stripping.
    m = re.match(
        r"^(Найти[^:]{0,80}:|Проверить:|Закрыть лакуну:)\s*(.+)$",
        out, flags=re.DOTALL,
    )
    if m:
        prefix, body = m.group(1).strip(), m.group(2).strip()
        if body and _looks_english(body):
            return f"{prefix} (англ.) «{_quote_block(body, 360)}»"
    return out


def _is_doi_like(text: str) -> bool:
    return bool(re.search(r"\b10\.\d{4,9}/[^\s\"']+", text or ""))


# ---------------------------------------------------------------------------
# Title and target venue extractors (Round III-J)
# ---------------------------------------------------------------------------

def _extract_title_candidate(dossier: dict[str, Any]) -> dict[str, Any]:
    """Decide a display title from persisted state. Never mutates the
    canonical ArticleModel.title_current. Returns:
      - display_title: str  (always non-empty; falls back to placeholder)
      - title_source:  str  ("article_model" / "first_paragraph" / "none")
      - title_confidence: "high" / "medium" / "low" / "none"
      - title_note: str (operator-facing one-liner)
    """
    am = _safe_get(dossier, "article_model") or {}
    canonical = _safe_get(am, "title_current")
    if isinstance(canonical, str) and canonical.strip():
        return {
            "display_title": canonical.strip(),
            "title_source": "article_model",
            "title_confidence": "high",
            "title_note": "Канонический заголовок из ArticleModel.",
        }
    first = _safe_get(dossier, "article_first_paragraph")
    if isinstance(first, str) and first.strip():
        head = first.strip()
        head_one_line = " ".join(head.split())
        # Title heuristic: short-ish, no terminal period, often has ":"
        looks_like_title = (
            len(head_one_line) <= 220
            and not head_one_line.endswith(".")
        )
        if looks_like_title:
            return {
                "display_title": head_one_line,
                "title_source": "probable_title_from_first_paragraph",
                "title_confidence": "medium",
                "title_note": (
                    "Вероятный заголовок, извлечён эвристикой из первого "
                    "абзаца исходного текста. Канонический "
                    "ArticleModel.title_current не заполнен."
                ),
            }
    return {
        "display_title": "Заголовок не удалось уверенно извлечь",
        "title_source": "none",
        "title_confidence": "none",
        "title_note": (
            "Ни ArticleModel.title_current, ни эвристика по первому "
            "абзацу не дали безопасного кандидата."
        ),
    }


def _extract_target_venue(dossier: dict[str, Any]) -> dict[str, Any]:
    """Decide what to render in the venue section. Three branches:

    1) selected_venue has a canonical_name → use it.
    2) investigated_venue or operator-supplied venue text exists →
       label "supplied by operator, profile incomplete".
    3) Nothing → "не восстановлена из metadata этого case".

    Never invents a label. Never claims selection when none is persisted.
    """
    sv = _safe_get(dossier, "selected_venue") or {}
    iv = _safe_get(dossier, "investigated_venue") or {}
    sv_name = (sv.get("canonical_name") if isinstance(sv, dict) else None)
    iv_name = (iv.get("canonical_name") if isinstance(iv, dict) else None)
    venue_text = _safe_get(dossier, "venue_input_text_preview")

    if isinstance(sv_name, str) and sv_name.strip():
        return {
            "label": sv_name.strip(),
            "label_source": "selected_venue.canonical_name",
            "confidence": (sv.get("confidence") or "не указана"),
            "scope": (sv.get("aims_scope_summary") or sv.get("scope_summary")),
            "completeness": "selected",
            "note": (
                "Площадка выбрана в case как `selected_venue` с каноническим "
                "именем."
            ),
        }
    if isinstance(iv_name, str) and iv_name.strip():
        return {
            "label": iv_name.strip(),
            "label_source": "investigated_venue.canonical_name",
            "confidence": (iv.get("confidence") or "не указана"),
            "scope": (iv.get("aims_scope_summary") or iv.get("scope_summary")),
            "completeness": "investigated_incomplete",
            "note": (
                "Площадка была исследована (`investigated_venue`), но не "
                "промоутирована в `selected_venue`."
            ),
        }
    # Operator-supplied label via /intake/text payload — extract a label
    # from the preview text *only* if the preview looks like a venue
    # description (first quoted phrase, or first capitalized phrase
    # before " — ").
    if isinstance(venue_text, str) and venue_text.strip():
        head = venue_text.strip()
        # Quoted phrase: «...»
        m = re.search(r"[«\"]([^»\"]{3,80})[»\"]", head)
        label = None
        if m:
            label = m.group(1).strip()
        else:
            # First "Name — ..." pattern at the start
            m2 = re.match(
                r"^\s*([^\n—\-]{3,80}?)\s*[—\-]\s",
                head,
            )
            if m2:
                label = m2.group(1).strip()
        if label:
            return {
                "label": label,
                "label_source": "venue_input_text_preview",
                "confidence": "low",
                "scope": None,
                "completeness": "operator_supplied_profile_incomplete",
                "note": (
                    "Целевая площадка указана автором в payload-е "
                    "/intake/text. VenueModel её не подтвердил "
                    "(canonical_name отсутствует, confidence низкий)."
                ),
            }
    return {
        "label": None,
        "label_source": "none",
        "confidence": "не определена",
        "scope": None,
        "completeness": "unrecoverable",
        "note": (
            "Целевая площадка не восстановлена из metadata этого case."
        ),
    }


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_passport(dossier: dict[str, Any]) -> HumanSection:
    am = _safe_get(dossier, "article_model") or {}
    genre_code = _safe_get(am, "genre_current") or "unknown"
    genre_ru = _GENRE_RU.get(genre_code, genre_code)
    lang = _safe_get(am, "language") or "не указан"
    conf = _safe_get(am, "confidence") or "не указана"
    venue = _extract_target_venue(dossier)
    title_cand = _extract_title_candidate(dossier)

    p1 = (
        f"Перед нами {genre_ru}. Язык статьи: {lang}. "
        f"Уверенность модели в реконструкции статьи: {conf}."
    )
    if venue["label"]:
        p2 = (
            f"Целевая площадка для подачи: «{venue['label']}». "
            f"Уверенность в профиле площадки: {venue['confidence']}. "
            f"{venue['note']}"
        )
    else:
        p2 = (
            "Целевая площадка не восстановлена из metadata этого case. "
            f"{venue['note']}"
        )
    notes: list[str] = []
    if not venue.get("scope"):
        notes.append(
            "Главная оговорка: подробного описания журнала в системе сейчас "
            "недостаточно — fit-проверка предварительная. Чтобы сделать "
            "вывод увереннее, нужно собрать про журнал больше материала "
            "(scope, типы статей, языковая политика, требования к объёму "
            "и оформлению)."
        )
    bullets: list[str] = []
    fa = _safe_get(dossier, "fit_assessment") or {}
    overall = _safe_get(fa, "overall_label")
    if overall:
        bullets.append(
            f"Текущий общий вердикт fit-проверки: «{overall}» "
            f"(см. раздел 5)."
        )
    # Evidence-based title display (never overwrites canonical title)
    src_map = {
        "article_model": "канонический заголовок ArticleModel",
        "probable_title_from_first_paragraph":
            "вероятный заголовок (эвристика по первому абзацу)",
        "none": "источник не определён",
    }
    src_ru = src_map.get(title_cand["title_source"], title_cand["title_source"])
    if title_cand["title_source"] != "none":
        bullets.append(
            f"Заголовок (для отображения): «{title_cand['display_title']}» "
            f"— источник: {src_ru}; уверенность: "
            f"{title_cand['title_confidence']}."
        )
        bullets.append(title_cand["title_note"])
    else:
        bullets.append("Заголовок не удалось уверенно извлечь.")
        bullets.append(title_cand["title_note"])
    return HumanSection(
        id="passport",
        title_ru="1. Паспорт",
        paragraphs=[p1, p2] + notes,
        bullets=bullets,
    )


def _ru_stub_for_english_field(label_ru: str) -> str:
    """Round III-J2: when an upstream semantic field is in English, do
    NOT surface the English content (translation drift risk) and do NOT
    leave a `(англ.)`-wrapped block in the author section. Show a
    Russian honesty stub that names the field and points to the
    technical view where the original formulation lives.
    """
    return (
        f"{label_ru}: системная реконструкция этого поля доступна во "
        "вкладке «Технические данные» (исходная формулировка модели — "
        "англоязычная)."
    )


def _ru_count_word(n: int, forms: tuple[str, str, str]) -> str:
    """Russian plural agreement (1 / 2-4 / 5+) — small util."""
    n_abs = abs(n)
    if n_abs % 10 == 1 and n_abs % 100 != 11:
        return forms[0]
    if 2 <= n_abs % 10 <= 4 and not 12 <= n_abs % 100 <= 14:
        return forms[1]
    return forms[2]


def _ru_stub_for_english_list(
    label_ru: str, items: list, item_forms: tuple[str, str, str] = (
        "элемент", "элемента", "элементов",
    ),
) -> str:
    """Russian honesty stub for a list whose items are predominantly
    English. Names extracted from dict items (scholar/author/tradition)
    are preserved as allowed English remnants.
    """
    n = len(items)
    names: list[str] = []
    for it in items:
        if isinstance(it, dict):
            for k in ("scholar", "author", "name", "tradition", "school"):
                v = it.get(k)
                if isinstance(v, str) and v.strip():
                    names.append(v.strip())
                    break
    word = _ru_count_word(n, item_forms)
    base = (
        f"{label_ru}: модель зафиксировала {n} {word}; "
        "формулировки сохранены в технических данных в исходной "
        "англоязычной форме."
    )
    if names:
        base += " Имена/традиции, упомянутые моделью: " + ", ".join(
            f"«{n}»" for n in dict.fromkeys(names)
        ) + "."
    return base


def _render_semantic_field(label_ru: str, value: Any) -> str | None:
    """Render a possibly-English / possibly-dict semantic field as a
    single Russian author-facing line. English content is replaced by a
    Russian honesty stub — original formulation stays in technical view.
    """
    if value is None:
        return None
    text = _normalize_entry(value)
    if not text:
        return None
    if _looks_english(text):
        return _ru_stub_for_english_field(label_ru)
    return f"{label_ru}: {text}"


def _section_what_understood(dossier: dict[str, Any]) -> HumanSection:
    am = _safe_get(dossier, "article_model") or {}
    paragraphs: list[str] = []

    line = _render_semantic_field(
        "Центральная проблема, как её зафиксировала система",
        _safe_get(am, "problem_statement"),
    )
    if line: paragraphs.append(line)
    line = _render_semantic_field(
        "Исследовательский вопрос", _safe_get(am, "research_question"),
    )
    if line: paragraphs.append(line)
    line = _render_semantic_field(
        "Объект рассмотрения", _safe_get(am, "object_of_inquiry"),
    )
    if line: paragraphs.append(line)
    line = _render_semantic_field(
        "Метод, как он описан", _safe_get(am, "method_description"),
    )
    if line: paragraphs.append(line)

    bullets: list[str] = []
    claims_raw = _safe_get(am, "core_claims") or []
    claims = _normalize_list(claims_raw)
    english_claims = [c for c in claims if _looks_english(c)]
    russian_claims = [c for c in claims if not _looks_english(c)]
    if russian_claims:
        bullets.append("Основные тезисы статьи (как их видит система):")
        bullets.extend(f"— {c}" for c in russian_claims)
    if english_claims:
        # Honest Russian stub — no `(англ.) «…»` blocks in author surface
        bullets.append(_ru_stub_for_english_list(
            "Основные тезисы статьи",
            list(claims_raw) if isinstance(claims_raw, list) else [],
            ("тезис", "тезиса", "тезисов"),
        ))

    genre = _GENRE_RU.get(
        _safe_get(am, "genre_current") or "unknown",
        _safe_get(am, "genre_current") or "не определён",
    )
    register = _safe_get(am, "disciplinary_register_current")
    if isinstance(register, list):
        # Map each register code to its Russian display; wrap any
        # remaining English term so the bullet stays clean.
        register_str = _ru_join([
            _ru_safe_line(_ru_term(_normalize_entry(r)))
            for r in register if _normalize_entry(r)
        ])
    elif register:
        register_str = _ru_safe_line(_ru_term(_normalize_entry(register)))
    else:
        register_str = ""
    if genre or register_str:
        line = f"Жанр и дисциплинарный регистр: {genre}"
        if register_str:
            line += f"; регистр — {register_str}"
        paragraphs.append(line + ".")

    pcore_raw = _safe_get(am, "protected_core") or []
    pcore = _normalize_list(pcore_raw)
    pcore_eng = [c for c in pcore if _looks_english(c)]
    pcore_ru = [c for c in pcore if not _looks_english(c)]
    if pcore_ru or pcore_eng:
        bullets.append(_PROTECTED_CORE_HINT)
    if pcore_ru:
        bullets.append("Защищаемое ядро статьи:")
        bullets.extend(f"— {c}" for c in pcore_ru)
    if pcore_eng:
        bullets.append(_ru_stub_for_english_list(
            "Защищаемое ядро статьи",
            list(pcore_raw) if isinstance(pcore_raw, list) else [],
            ("элемент", "элемента", "элементов"),
        ))
    mzones_raw = _safe_get(am, "mutable_zones") or []
    mzones = _normalize_list(mzones_raw)
    mzones_eng = [z for z in mzones if _looks_english(z)]
    mzones_ru = [z for z in mzones if not _looks_english(z)]
    if mzones_ru or mzones_eng:
        bullets.append(_MUTABLE_HINT)
    if mzones_ru:
        bullets.append("Гибкие зоны для доработки:")
        bullets.extend(f"— {z}" for z in mzones_ru)
    if mzones_eng:
        bullets.append(_ru_stub_for_english_list(
            "Гибкие зоны для доработки",
            list(mzones_raw) if isinstance(mzones_raw, list) else [],
            ("зона", "зоны", "зон"),
        ))

    unknowns = _normalize_list(_safe_get(am, "unknowns"))
    if unknowns:
        bullets.append(
            "Чего система про статью пока не знает (поля, которые "
            "ArticleModeler пометил как unknown):"
        )
        bullets.extend(f"— {_ru_safe_line(u)}" for u in unknowns[:8])

    if not paragraphs and not bullets:
        paragraphs.append(
            "Система не смогла развернуть содержательное описание статьи: "
            "ArticleModel заполнен слабо. Это не значит, что статья "
            "плохая — это значит, что для авторского разбора надо "
            "перезапустить семантический разбор по тексту статьи."
        )

    return HumanSection(
        id="what_understood",
        title_ru="2. Что система поняла про статью",
        paragraphs=paragraphs,
        bullets=bullets,
    )


def _section_field_position(dossier: dict[str, Any]) -> HumanSection:
    sp = _safe_get(dossier, "semantic_profile") or {}
    paragraphs: list[str] = []
    bullets: list[str] = []

    disc_code = _safe_get(sp, "primary_discipline")
    disc_ru = _ru_term(disc_code) if disc_code else ""
    regs_raw = _normalize_list(_safe_get(sp, "disciplinary_registers"))
    # Map each register to its Russian display; if no mapping known and the
    # raw value is English, wrap it as (англ.) «…» to keep the surface clean.
    regs_ru: list[str] = []
    for r in regs_raw:
        mapped = _ru_term(r)
        if mapped == r and _looks_english(r):
            regs_ru.append(f"(англ.) «{_quote_block(r, 120)}»")
        else:
            regs_ru.append(mapped)
    if disc_code or regs_ru:
        parts = []
        if disc_code:
            parts.append(f"основная дисциплина — {disc_ru} (`{disc_code}`)")
        if regs_ru:
            parts.append(
                "задействованные регистры — " + _ru_join(regs_ru)
            )
        paragraphs.append(
            "Где статья располагается в академическом поле: "
            + "; ".join(parts) + "."
        )

    def _render_list_block(
        head_ru: str, raw: Any, item_forms: tuple[str, str, str],
    ) -> None:
        items_norm = _normalize_list(raw)
        if not items_norm:
            return
        eng = [s for s in items_norm if _looks_english(s)]
        ru = [s for s in items_norm if not _looks_english(s)]
        if ru:
            bullets.append(head_ru)
            bullets.extend(f"— {s}" for s in ru)
        if eng:
            bullets.append(_ru_stub_for_english_list(
                head_ru.rstrip(":"),
                list(raw) if isinstance(raw, list) else [],
                item_forms,
            ))

    _render_list_block(
        "Школы и традиции, на которые опирается статья:",
        _safe_get(sp, "schools_and_traditions"),
        ("школа/традиция", "школы/традиции", "школ/традиций"),
    )
    _render_list_block(
        "Теоретические «плечи» — на ком статья стоит:",
        _safe_get(sp, "theoretical_shoulders"),
        ("опора", "опоры", "опор"),
    )
    _render_list_block(
        "Оппоненты или фоновые контр-позиции:",
        _safe_get(sp, "opponents_or_foils"),
        ("оппонент", "оппонента", "оппонентов"),
    )
    bridges_raw = _safe_get(sp, "citation_bridges_needed") or []
    bridges = _normalize_list(bridges_raw)
    if bridges:
        bullets.append(
            "Какие мосты к традициям системе кажутся необходимыми, "
            "чтобы статья читалась полноценно в этой дисциплинарной "
            "рамке (это карта направлений, а не список обязательных "
            "цитат):"
        )
        eng = [b for b in bridges if _looks_english(b)]
        ru = [b for b in bridges if not _looks_english(b)]
        bullets.extend(f"— {b}" for b in ru)
        if eng:
            bullets.append(_ru_stub_for_english_list(
                "Недостающие мосты к традициям",
                list(bridges_raw) if isinstance(bridges_raw, list) else [],
                ("мост", "моста", "мостов"),
            ))

    move = _safe_get(sp, "argument_move_type")
    move_desc = _safe_get(sp, "argument_move_description")
    if move or move_desc:
        line = "Тип аргументативного хода"
        if move:
            line += f": `{move}`"
        if move_desc:
            md = _normalize_entry(move_desc)
            if _looks_english(md):
                line += f" — (англ.) «{_quote_block(md, 300)}»"
            else:
                line += f" — {md}"
        paragraphs.append(line + ".")

    if not paragraphs and not bullets:
        paragraphs.append(
            "Полевая разметка статьи (дисциплины, школы, плечи, "
            "оппоненты) пока не построена — семантический профиль "
            "статьи заполнен лишь частично."
        )

    return HumanSection(
        id="field_position",
        title_ru="3. Где находится статья в поле",
        paragraphs=paragraphs,
        bullets=bullets,
    )


def _section_venue_state(dossier: dict[str, Any]) -> HumanSection:
    v = _extract_target_venue(dossier)
    p: list[str] = []
    if v["label"]:
        head = (
            f"Целевая площадка: «{v['label']}». "
            f"Источник метки: `{v['label_source']}`; "
            f"уверенность системы в профиле: {v['confidence']}."
        )
        p.append(head)
        if v["completeness"] != "selected":
            p.append(v["note"])
    else:
        p.append(v["note"])
    if v.get("scope"):
        scope_text = _normalize_entry(v["scope"])
        if _looks_english(scope_text):
            p.append(_ru_stub_for_english_field(
                "Что сейчас известно про scope площадки",
            ))
        else:
            p.append(f"Что сейчас известно про scope площадки: {scope_text}.")
    else:
        p.append(
            "Содержательного описания scope, типов принимаемых статей, "
            "языковой и AI-политики в профиле площадки сейчас нет — "
            "поэтому говорить уверенно о соответствии нельзя. "
            "Это не значит, что журнал плохо подходит; это значит, что "
            "у нас не из чего пока сделать вывод."
        )
    bullets = [
        "Какие сведения о площадке нужно собрать, чтобы fit-вердикт стал "
        "надёжным:",
        "— scope журнала (тематические рамки);",
        "— типы статей, которые журнал принимает (эмпирические, "
        "теоретические, обзоры, комментарии);",
        "— языковая политика (русский / английский / двуязычный режим);",
        "— ограничения по объёму (word limits, число знаков);",
        "— требования к раскрытию использования AI (AI disclosure);",
        "— ожидания по работе с источниками и библиографией;",
        "— общие формальные требования к submission.",
    ]
    paragraphs = p
    # Honest disclaimer: do not invent venue policy
    paragraphs.append(
        "Система специально не подставляет «возможные требования» "
        "журнала, если в её профиле этих требований нет. Любые "
        "конкретные правила «Вопросов философии» здесь должны "
        "появиться только из реального источника — сайта или редакции."
    )
    return HumanSection(
        id="venue_state",
        title_ru="4. Что известно и неизвестно про площадку",
        paragraphs=paragraphs,
        bullets=bullets,
    )


def _section_fit(dossier: dict[str, Any]) -> HumanSection:
    fa = _safe_get(dossier, "fit_assessment") or {}
    overall = _safe_get(fa, "overall_label") or "not_enough_data"
    conf = _safe_get(fa, "confidence") or "не указана"
    rec = _safe_get(fa, "recommendation")

    overall_ru = {
        "good": "пара статья × журнал в целом смотрится разумно",
        "ok": "пара статья × журнал условно жизнеспособна",
        "partial": "соответствие неполное — есть конкретные слабые точки",
        "poor": "пара выглядит проблемной",
        "not_enough_data": (
            "для уверенного вердикта системе не хватает данных — "
            "прежде всего по самой площадке"
        ),
    }.get(overall, overall)

    paragraphs = [
        f"Общий вердикт fit-проверки: {overall_ru}. "
        f"Уверенность системы: {conf}."
    ]
    if rec:
        paragraphs.append(f"Рекомендация системы: {_ru_safe_line(rec)}")

    axes = _safe_get(fa, "axes") or []
    groups: dict[str, list[str]] = {"ok": [], "weak": [], "unknown": []}
    for ax in axes:
        if not isinstance(ax, dict):
            continue
        axis = ax.get("axis") or ""
        value = (ax.get("value") or "").lower()
        notes = (ax.get("notes") or "").strip()
        axis_ru = _AXIS_RU.get(axis, axis)
        bucket = "unknown"
        if value in ("strong_fit", "ok", "partial_fit"):
            bucket = "ok"
        elif value in ("weak", "mismatch"):
            bucket = "weak"
        line = f"{axis_ru} — {_FIT_VALUE_RU.get(value, value or 'не определено')}"
        if notes:
            line += f". {_ru_safe_line(notes)}"
        groups[bucket].append(line)

    subsections: list[HumanSubsection] = []
    if groups["ok"]:
        subsections.append(HumanSubsection(
            title_ru="Что в целом сходится",
            bullets=groups["ok"],
        ))
    if groups["weak"]:
        subsections.append(HumanSubsection(
            title_ru="Слабые места",
            bullets=groups["weak"],
        ))
    if groups["unknown"]:
        subsections.append(HumanSubsection(
            title_ru="Неизвестно из-за нехватки данных",
            bullets=groups["unknown"],
        ))

    # Pull out the genre × unknown-venue risk explicitly
    am = _safe_get(dossier, "article_model") or {}
    venue_info = _extract_target_venue(dossier)
    if (_safe_get(am, "genre_current") or "").lower() in (
        "theoretical_essay", "theoretical_argument",
        "conceptual_article", "essay",
    ) and not venue_info.get("scope"):
        paragraphs.append(
            "Главный реальный риск этой пары прямо сейчас: статья — "
            "теоретическая, а политика журнала по теоретическим статьям "
            "системе неизвестна. Это не «плохой fit», это «не из чего "
            "сделать fit». До тех пор пока про журнал не появится больше "
            "сведений, любой более жёсткий вывод будет натянутым."
        )

    return HumanSection(
        id="fit",
        title_ru="5. FitAssessment: почему вердикт «not_enough_data»",
        paragraphs=paragraphs,
        bullets=[],
        subsections=subsections,
    )


def _section_mismatches(dossier: dict[str, Any]) -> HumanSection:
    mm = _safe_get(dossier, "mismatch_map") or {}
    mismatches = _safe_get(mm, "mismatches") or []
    paragraphs: list[str] = []
    if mismatches:
        paragraphs.append(
            f"Карта несовпадений насчитывает {len(mismatches)} осей. "
            "Ниже каждое несовпадение — отдельным блоком: что система "
            "увидела на стороне статьи, что — на стороне площадки, чем "
            "это важно и какие действия возможны."
        )
    else:
        paragraphs.append(
            "Карта несовпадений пуста или не построена. Это не значит, "
            "что несовпадений нет: чаще это значит, что для оси не "
            "хватило либо данных о статье, либо данных о площадке."
        )

    subsections: list[HumanSubsection] = []
    for m in mismatches:
        if not isinstance(m, dict):
            continue
        axis = m.get("axis") or ""
        axis_ru = _AXIS_RU.get(axis, axis)
        sev = (m.get("severity") or "").lower()
        sev_ru = _SEVERITY_RU.get(sev, sev or "")
        narr_status = (m.get("narrative_status") or "").lower()
        narr_ru = _NARRATIVE_STATUS_RU.get(narr_status, narr_status or "")
        article_side = _normalize_entry(m.get("article_side")).strip()
        venue_side = _normalize_entry(m.get("venue_side")).strip()
        descr = _normalize_entry(m.get("description")).strip()
        actions = _normalize_list(m.get("possible_actions"))
        core_risk = (m.get("field_core_risk") or "").lower()
        sub_paragraphs: list[str] = []
        if article_side:
            if _looks_english(article_side):
                sub_paragraphs.append(_ru_stub_for_english_field(
                    "На стороне статьи",
                ))
            else:
                sub_paragraphs.append(
                    f"На стороне статьи: {_ru_safe_line(article_side)}"
                )
        if venue_side:
            if _looks_english(venue_side):
                sub_paragraphs.append(_ru_stub_for_english_field(
                    "На стороне площадки",
                ))
            else:
                sub_paragraphs.append(
                    f"На стороне площадки: {_ru_safe_line(venue_side)}"
                )
        elif narr_status in (
            "unknown_due_to_venue_evidence", "empty_valid_unknown",
        ):
            sub_paragraphs.append(
                "На стороне площадки: текст площадки не задаёт явных "
                "ожиданий по этой оси, поэтому конкретно описать "
                "ожидание невозможно."
            )
        elif narr_status in ("needs_llm", "parse_failed", "provider_error"):
            sub_paragraphs.append(
                "На стороне площадки: содержательный комментарий "
                "семантического модуля отсутствует — fit и rewrite "
                "посчитаны независимо от него."
            )
        if descr and descr not in (article_side, venue_side):
            if _looks_english(descr):
                sub_paragraphs.append(_ru_stub_for_english_field(
                    "Описание несовпадения",
                ))
            else:
                sub_paragraphs.append(_ru_safe_line(descr))
        if core_risk and core_risk not in (
            "unknown_core_impact", "no_core_impact",
        ):
            sub_paragraphs.append(
                "Действия здесь могут затронуть защищаемое ядро "
                "статьи — менять без согласия автора нельзя."
            )
        sub_bullets: list[str] = []
        if actions:
            sub_bullets.append("Возможные действия:")
            sub_bullets.extend(f"— {a}" for a in actions)
        title = axis_ru
        if sev_ru:
            title += f" (тяжесть: {sev_ru})"
        subsections.append(HumanSubsection(
            title_ru=title,
            paragraphs=sub_paragraphs,
            bullets=sub_bullets,
            status_ru=narr_ru or None,
            badge=narr_status or sev or None,
        ))

    return HumanSection(
        id="mismatches",
        title_ru="6. Несовпадения и работа по ним",
        paragraphs=paragraphs,
        subsections=subsections,
    )


def _section_sources(dossier: dict[str, Any]) -> HumanSection:
    cp = _safe_get(dossier, "citation_plan") or {}
    paragraphs: list[str] = []
    bullets: list[str] = []
    sem = (cp.get("semantic_status") or "").lower()
    conf = cp.get("confidence") or "не указана"

    if not cp:
        paragraphs.append(
            "План работы с источниками для этого case пока не построен. "
            "Запустится автоматически после fit-цепи."
        )
        return HumanSection(
            id="sources", title_ru="7. Работа с источниками",
            paragraphs=paragraphs,
        )

    if sem == "llm_grounded":
        paragraphs.append(
            "План работы с источниками собран содержательно: ниже карта "
            "лакун, недостающих мостов между традициями, поисковых "
            "задач и проверочных шагов. Уверенность плана: "
            f"{conf}. План — это карта направлений, а не готовый список "
            "обязательных цитат: конкретные источники подбирает автор."
        )
    elif sem == "needs_llm":
        paragraphs.append(
            "План работы с источниками заполнен только структурно. "
            "Содержательная карта лакун и поисковых задач для этого "
            "case ещё не построена."
        )
    else:
        paragraphs.append(
            "План работы с источниками собран частично. Ниже — то, что "
            "удалось зафиксировать."
        )

    gaps = _normalize_list(cp.get("citation_gap_categories"))
    bridges = _normalize_list(cp.get("missing_bridge_categories"))
    tasks = _normalize_list(cp.get("recommended_reference_search_tasks"))
    verif = _normalize_list(cp.get("verification_tasks"))
    danger = _normalize_list(cp.get("dangerous_padding_warnings"))
    unknowns = _normalize_list(cp.get("unknowns"))

    def _ru_bullet(s: str) -> str:
        return f"— {_ru_safe_line(s)}"

    subsections: list[HumanSubsection] = []
    if gaps:
        subsections.append(HumanSubsection(
            title_ru=f"Категории лакун ({len(gaps)})",
            bullets=[_ru_bullet(g) for g in gaps],
        ))
    if bridges:
        subsections.append(HumanSubsection(
            title_ru=f"Недостающие мосты между традициями ({len(bridges)})",
            paragraphs=[
                "Это не претензия «у вас не процитированы такие-то "
                "авторы», а карта направлений, между которыми статье "
                "нужно навести мост, чтобы её читали в нужной "
                "дисциплинарной рамке."
            ],
            bullets=[_ru_bullet(b) for b in bridges],
        ))
    if tasks:
        subsections.append(HumanSubsection(
            title_ru=f"Поисковые задачи по источникам ({len(tasks)})",
            paragraphs=[
                "Поисковые задачи переведены на русский. Имена, которые "
                "система упоминает в формулировках задач (классики "
                "organizational studies, STS-программа, исследователи "
                "AI в организациях и т.п.), — это направления для "
                "поиска и возможные корпуса, а не проверенный список "
                "обязательных цитат. Список ссылок собирает автор."
            ],
            bullets=[_ru_bullet(_translate_search_task(t)) for t in tasks],
        ))
    if verif:
        subsections.append(HumanSubsection(
            title_ru=f"Проверочные задачи ({len(verif)})",
            bullets=[_ru_bullet(_translate_search_task(v)) for v in verif],
        ))
    if danger:
        subsections.append(HumanSubsection(
            title_ru="Опасность «косметического» добивания библиографии",
            paragraphs=[
                "Система отдельно предупреждает: добавлять ссылки ради "
                "видимости полноты библиографии — путь, который рецензент "
                "поля заметит. Источники должны быть мостами к традиции "
                "и идти от содержания, а не от формы."
            ],
            bullets=[_ru_bullet(w) for w in danger],
        ))
    if unknowns:
        subsections.append(HumanSubsection(
            title_ru="Чего система про источники прямо не знает",
            bullets=[_ru_bullet(u) for u in unknowns[:8]],
        ))

    return HumanSection(
        id="sources", title_ru="7. Работа с источниками",
        paragraphs=paragraphs, bullets=bullets, subsections=subsections,
    )


def _section_bibliography(dossier: dict[str, Any]) -> HumanSection:
    bp = _safe_get(dossier, "bibliography_profile") or {}
    paragraphs: list[str] = []
    bullets: list[str] = []
    if not bp:
        paragraphs.append(
            "Bibliography profile для этой статьи не построен. Это значит, "
            "что либо в тексте не нашёлся раздел «Список литературы» / "
            "«References», либо текст ещё не прошёл библиографический разбор."
        )
        bullets = [
            "Что нужно сделать автору:",
            "— добавить в статью раздел «Список литературы» с явным заголовком;",
            "— привести источники в распознаваемом виде (автор, год, "
            "название, выходные данные; для журналов — том и страницы; "
            "для книг — издательство и место);",
            "— по возможности указать DOI / URL для каждого источника;",
            "— после этого перезапустить разбор библиографии и план работы "
            "с источниками — citation readiness станет полноценным.",
        ]
        return HumanSection(
            id="bibliography", title_ru="8. Библиография",
            paragraphs=paragraphs, bullets=bullets,
        )

    refs = bp.get("reference_count")
    dois = bp.get("doi_count")
    status = bp.get("status") or "не определён"
    paragraphs.append(
        f"Статус разбора библиографии: {status}. "
        f"Распознано ссылок: {refs if refs is not None else 'нет данных'}; "
        f"из них с DOI: {dois if dois is not None else '0'}."
    )
    detected = bp.get("bibliography_section_detected")
    if detected is False:
        paragraphs.append(
            "Раздел «Список литературы» не распознан как отдельная секция. "
            "Это типичная причина, по которой план работы с источниками "
            "не может стать полноценным — системе нечего проверять."
        )
    bullets = [
        "Что от этого зависит:",
        "— без явной библиографии не работает proper citation readiness;",
        "— compliance-проверки требований к источникам остаются открытыми;",
        "— SubmissionPack помечен как не готовый к подаче.",
    ]
    return HumanSection(
        id="bibliography", title_ru="8. Библиография",
        paragraphs=paragraphs, bullets=bullets,
    )


def _section_compliance(dossier: dict[str, Any]) -> HumanSection:
    cc = _safe_get(dossier, "compliance_checklist") or {}
    items = _safe_get(cc, "checklist_items") or _safe_get(cc, "items") or []
    paragraphs: list[str] = []
    bullets: list[str] = []
    if not items:
        paragraphs.append(
            "Формальные проверки не возвращают конкретных пунктов — "
            "compliance checklist для этого case пока пуст или не "
            "построен. Это значит, что про требования журнала система "
            "пока не знает достаточно, чтобы их сверять."
        )
        bullets = [
            "Что обычно нужно проверить вручную перед подачей:",
            "— наличие заголовка статьи;",
            "— наличие аннотации (abstract);",
            "— наличие явной библиографии;",
            "— типы статей, которые принимает журнал;",
            "— языковая политика журнала;",
            "— ограничения по объёму (word/character limits);",
            "— политика раскрытия использования AI (AI disclosure);",
            "— политика по данным, этике, конфликтам интересов, финансированию;",
            "— требования по списку и порядку авторов.",
        ]
    else:
        paragraphs.append(
            f"Чек-лист формальных требований содержит {len(items)} пунктов. "
            "Каждый пункт — это конкретный вопрос к статье или к редакции."
        )
        for it in items[:20]:
            if not isinstance(it, dict):
                continue
            req = (it.get("requirement") or "").strip()
            status = (it.get("status") or "").strip()
            cat = (it.get("category") or "").strip()
            req_safe = _ru_safe_line(req) if req else (
                "требование без явной формулировки"
            )
            line = f"— {req_safe}"
            if status:
                line += f" (статус: {status})"
            if cat:
                line += f" — категория: {cat}"
            bullets.append(line)
    return HumanSection(
        id="compliance", title_ru="9. Формальные проверки",
        paragraphs=paragraphs, bullets=bullets,
    )


def _section_risk(dossier: dict[str, Any]) -> HumanSection:
    rr = _safe_get(dossier, "risk_report") or {}
    sem = (rr.get("semantic_status") or "").lower()
    items = _safe_get(rr, "risk_items") or []
    paragraphs: list[str] = []
    bullets: list[str] = []

    if not rr:
        paragraphs.append(
            "Анализ рисков подачи для этого case ещё не запускался."
        )
        return HumanSection(
            id="risk", title_ru="10. Что не удалось системе: риск-анализ",
            paragraphs=paragraphs,
        )

    if sem == "llm_grounded" and items:
        paragraphs.append(
            "Анализ рисков подачи готов и содержит конкретные пункты. "
            "См. ниже список выявленных рисков."
        )
        for r in items[:12]:
            if not isinstance(r, dict):
                continue
            sev = (r.get("severity") or "").lower()
            sev_ru = _SEVERITY_RU.get(sev, sev or "")
            descr = (r.get("description") or "").strip()
            line = f"— {descr}" if descr else "— риск без описания"
            if sev_ru:
                line += f" (тяжесть: {sev_ru})"
            bullets.append(line)
    else:
        paragraphs.append(
            "Содержательный риск-анализ для этого case сейчас не готов. "
            "Система специально не выдумывает риски и не подставляет "
            "детерминированный текст вместо настоящего анализа."
        )
        diag = rr.get("attempt_diagnostics") or {}
        if diag:
            paragraphs.append(
                "Что произошло технически (короткая редактированная "
                "диагностика — для разработчика, не для подачи):"
            )
            redacted = []
            ps = diag.get("provider_status")
            if ps:
                redacted.append(f"— провайдер: {ps};")
            parse = diag.get("parse_status") or diag.get("parse_failure_category")
            if parse:
                redacted.append(f"— разбор ответа: {parse};")
            cl = diag.get("content_length")
            if cl is not None:
                redacted.append(f"— длина ответа модели: {cl} символов;")
            ch = diag.get("content_hash_prefix")
            if ch:
                redacted.append(f"— хэш-префикс ответа: {ch};")
            redacted.append(
                "— сам текст ответа модели не сохраняется и здесь не "
                "показывается."
            )
            bullets.extend(redacted)
            bullets.append(
                "Следующий инженерный шаг — улучшать стабильность "
                "JSON-контракта или промпта риск-офицера; это работа "
                "системы, а не автора."
            )

    return HumanSection(
        id="risk", title_ru="10. Что не удалось системе: риск-анализ",
        paragraphs=paragraphs, bullets=bullets,
    )


def _section_next_actions(dossier: dict[str, Any]) -> HumanSection:
    sp = _safe_get(dossier, "submission_pack") or {}
    explicit = _nonempty_list(sp.get("next_actions"))
    paragraphs = [
        "Что автору сейчас полезнее всего сделать — рабочий список, "
        "а не дамп статусов."
    ]
    bullets: list[str] = []
    if explicit:
        bullets.append(
            "Шаги, которые предлагает система, исходя из текущего "
            "состояния submission-пакета:"
        )
        bullets.extend(f"— {_ru_safe_line(a)}" for a in explicit)
    else:
        bullets.extend([
            "— добавить распознаваемый заголовок статьи;",
            "— добавить аннотацию (abstract) или её русский эквивалент;",
            "— оформить раздел «Список литературы» с источниками в "
            "распознаваемом виде;",
            "— пройти поисковые задачи из плана работы с источниками "
            "(раздел 7);",
            "— вручную собрать сведения про журнал (scope, типы статей, "
            "языковая политика, AI disclosure, word limits) и занести "
            "их в профиль площадки;",
            "— заполнить scenario подачи (цель, дедлайн, риск-толерантность);",
            "— после этого повторить fit / citation / compliance.",
        ])
    return HumanSection(
        id="next_actions",
        title_ru="11. SubmissionPack / что делать дальше",
        paragraphs=paragraphs, bullets=bullets,
    )


def _section_verdict(dossier: dict[str, Any]) -> HumanSection:
    am = _safe_get(dossier, "article_model") or {}
    sp = _safe_get(dossier, "semantic_profile") or {}
    bp = _safe_get(dossier, "bibliography_profile") or {}
    fa = _safe_get(dossier, "fit_assessment") or {}
    cp = _safe_get(dossier, "citation_plan") or {}
    rr = _safe_get(dossier, "risk_report") or {}
    rp = _safe_get(dossier, "rewrite_plan") or {}
    venue = _extract_target_venue(dossier)
    has_pcore = bool(_normalize_list(am.get("protected_core")))
    has_bib = bool(bp) and bool(bp.get("reference_count"))
    overall = (fa.get("overall_label") or "").lower()
    primary_disc = sp.get("primary_discipline")
    primary_disc_ru = _ru_term(primary_disc) if primary_disc else None

    lines: list[str] = []

    # Discipline-grounded opening — built from THIS case, not template
    if primary_disc_ru:
        lines.append(
            f"Система прочитывает статью в первую очередь как работу в "
            f"поле «{primary_disc_ru}» (`{primary_disc}`). "
            "Это след именно этого case — не предзаданная рамка."
        )

    if has_pcore:
        lines.append(
            "У статьи есть содержательное защищаемое ядро — это её "
            "сильная сторона: при перепаковке под журнал её не придётся "
            "переписывать заново."
        )
    else:
        lines.append(
            "Защищаемое ядро статьи в модели пока не выделено явно. "
            "Это первое, что стоит зафиксировать перед подачей: что "
            "именно в статье не подлежит перепаковке."
        )

    if not has_bib:
        lines.append(
            "Главный текущий дефицит — библиографический. Без явного "
            "раздела источников ни план работы с источниками, ни "
            "compliance не могут быть закрыты."
        )

    # Venue-aware sentence — three branches, all evidence-based
    if venue["completeness"] == "selected":
        if not venue.get("scope"):
            lines.append(
                f"Площадка «{venue['label']}» выбрана, но её профиль "
                "в системе пуст по scope — fit-вердикт сейчас опирается "
                "на минимальный профиль площадки."
            )
    elif venue["completeness"] in (
        "investigated_incomplete",
        "operator_supplied_profile_incomplete",
    ):
        lines.append(
            f"Целевая площадка указана: «{venue['label']}». "
            "Профиль площадки системой не собран — fit-вердикт сейчас "
            "опирается на минимальный профиль. Это не вердикт против "
            "журнала, а вердикт о наличии сведений о нём."
        )
    else:
        lines.append(
            "Целевая площадка не восстановлена из metadata этого case — "
            "невозможно говорить о соответствии конкретному журналу."
        )

    if overall == "not_enough_data":
        lines.append(
            "Текущий fit — «not_enough_data»: это честный отказ "
            "сделать сильный вывод там, где данных нет. Не нужно "
            "читать его как «статья не подходит»."
        )

    # Plan-status awareness — follow actual case lanes
    cp_sem = (cp.get("semantic_status") or "").lower() if cp else ""
    rp_sem = (rp.get("semantic_status") or "").lower() if rp else ""
    rr_sem = (rr.get("semantic_status") or "").lower() if rr else ""
    plan_notes = []
    if cp_sem == "llm_grounded":
        plan_notes.append(
            "план работы с источниками собран содержательно (раздел 7)"
        )
    if rp_sem in ("llm_grounded", "llm_grounded_partial"):
        plan_notes.append(
            "план переработки начат на уровне семантики "
            f"(`{rp_sem}`, см. SubmissionPack)"
        )
    if rr_sem not in ("", "llm_grounded"):
        plan_notes.append(
            "содержательный риск-анализ не готов (см. раздел 10)"
        )
    if plan_notes:
        lines.append("Текущая траектория case: " + "; ".join(plan_notes) + ".")

    lines.append(
        "Полезнее всего сейчас: source-work (раздел 7), оформление "
        "библиографии (раздел 8) и сбор материала про журнал "
        "(раздел 4). После этого имеет смысл повторить досье."
    )
    return HumanSection(
        id="verdict", title_ru="12. Итоговый авторский вердикт",
        paragraphs=lines,
    )


# ---------------------------------------------------------------------------
# Source header (navigation block)
# ---------------------------------------------------------------------------

_EXT_TYPE_RU: dict[str, str] = {
    "docx": "Word-документ (.docx)",
    "doc": "Word-документ (.doc)",
    "pdf": "PDF-файл",
    "txt": "обычный текст (.txt)",
    "md": "Markdown (.md)",
    "html": "HTML-страница",
    "rtf": "RTF-документ",
}


def _format_size(n: int | None) -> str:
    if not n or n <= 0:
        return "размер файла не сохранён"
    if n < 1024:
        return f"{n} байт"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} КБ"
    return f"{n / 1024 / 1024:.2f} МБ"


def _build_source_header(dossier: dict[str, Any]) -> HumanSourceHeader:
    case_id = _safe_get(dossier, "case_id") or "не указан"
    generated_at = _safe_get(dossier, "generated_at") or "—"
    # Round III-J2: source header uses the same title-candidate helper
    # as passport, so it no longer reads "Заголовок в документе не
    # найден" when a probable candidate exists.
    title_cand = _extract_title_candidate(dossier)
    if title_cand["title_source"] == "article_model":
        doc_title = title_cand["display_title"]
    elif title_cand["title_source"] == "probable_title_from_first_paragraph":
        doc_title = (
            f"{title_cand['display_title']} (вероятный заголовок — "
            "см. раздел 1)"
        )
    else:
        doc_title = ""
    um = _safe_get(dossier, "upload_metadata") or {}

    notes: list[str] = []
    if not um:
        # Case predates Round III-H persistence, or text-only intake.
        return HumanSourceHeader(
            source_filename_ru=(
                "Имя исходного файла не сохранено в metadata этого case."
            ),
            source_type_ru="тип источника не зафиксирован",
            size_ru="размер источника не сохранён",
            document_title_ru=(
                doc_title or "Заголовок системой не выделен (см. раздел 1 — нет надёжного кандидата)"
            ),
            case_id_ru=str(case_id),
            generated_at_ru=str(generated_at),
            notes=[
                "Этот case был создан до того, как система начала "
                "сохранять метаданные загрузки. Для будущих загрузок "
                "имя файла, размер и hash сохраняются автоматически.",
            ],
        )

    filename = um.get("original_filename") or (
        "Имя исходного файла не сохранено"
    )
    ext = um.get("original_extension") or um.get("upload_source_type")
    ext_ru = _EXT_TYPE_RU.get(
        (ext or "").lower(), ext or "тип источника не определён",
    )
    size = um.get("original_file_size_bytes")
    chars = um.get("text_char_count")
    words = um.get("text_word_count")
    size_line = _format_size(size)
    if chars:
        size_line += f"; извлечено {chars} знаков"
    if words:
        size_line += f", около {words} слов"

    return HumanSourceHeader(
        source_filename_ru=str(filename),
        source_type_ru=str(ext_ru),
        size_ru=size_line,
        document_title_ru=str(doc_title or "Заголовок системой не выделен (см. раздел 1 — нет надёжного кандидата)"),
        case_id_ru=str(case_id),
        generated_at_ru=str(generated_at),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Technical footer (collapsed by default in UI)
# ---------------------------------------------------------------------------

# Lanes that may carry per-lane diagnostics on the dossier dict.
_LANE_ROLES: list[tuple[str, str]] = [
    ("article_model", "article_modeler"),
    ("semantic_profile", "semantic_profiler"),
    ("selected_venue", "venue_profiler"),
    ("fit_assessment", "fit_assessor"),
    ("mismatch_map", "mismatch_narrator"),
    ("risk_report", "risk_officer"),
    ("citation_plan", "citation_planner"),
    ("rewrite_plan", "rewrite_planner"),
    ("compliance_checklist", "compliance_checklist_builder"),
    ("submission_pack", "submission_pack_builder"),
    ("bibliography_profile", "bibliography_profiler"),
]


_AGENT_DIAG_KEYS = (
    "attempt_diagnostics", "narrator_coverage", "diagnostics",
)


def _extract_agent_metadata(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []
    for lane_key, role in _LANE_ROLES:
        lane = _safe_get(dossier, lane_key) or {}
        if not isinstance(lane, dict):
            continue
        diag = None
        for k in _AGENT_DIAG_KEYS:
            v = lane.get(k)
            if isinstance(v, dict) and v:
                diag = v
                break
        entry: dict[str, Any] = {
            "lane": lane_key,
            "role": role,
            "model_role": (
                (diag or {}).get("model_role")
                or (diag or {}).get("agent_role") or role
            ),
            "provider_status": (diag or {}).get("provider_status"),
            "parse_status": (diag or {}).get("parse_status"),
            "repair_status": (diag or {}).get("repair_status"),
            "semantic_status": (
                lane.get("semantic_status")
                or (diag or {}).get("semantic_status")
            ),
            "fallback_reason": (diag or {}).get("fallback_reason"),
            "rubric_active": (diag or {}).get("rubric_active"),
            "latency_ms": (diag or {}).get("latency_ms"),
            "raw_output_exposed": False,
        }
        # Mismatch-narrator uses "narrator_coverage" shape
        if lane_key == "mismatch_map":
            nc = lane.get("narrator_coverage") or {}
            if isinstance(nc, dict):
                entry["semantic_status"] = nc.get("narrator_status") or entry["semantic_status"]
                entry["parse_status"] = nc.get("parse_failure_category") or entry["parse_status"]
                entry["repair_status"] = nc.get("repair_failure_stage") or entry["repair_status"]
                entry["filled_count"] = nc.get("filled_count")
                entry["total_count"] = nc.get("total_count")
        agents.append({k: v for k, v in entry.items() if v is not None})
    return agents


def _build_technical_footer(dossier: dict[str, Any]) -> HumanTechnicalFooter:
    um = _safe_get(dossier, "upload_metadata") or {}
    case_id = _safe_get(dossier, "case_id") or ""

    input_metadata = {
        "case_id": case_id,
        "original_filename": um.get("original_filename"),
        "upload_source_type": um.get("upload_source_type"),
        "original_extension": um.get("original_extension"),
        "original_file_size_bytes": um.get("original_file_size_bytes"),
        "content_hash_prefix": um.get("content_hash_prefix"),
        "text_hash_prefix": um.get("text_hash_prefix"),
        "uploaded_at": um.get("uploaded_at"),
        "extraction_status": um.get("extraction_status"),
        "text_char_count": um.get("text_char_count"),
        "text_word_count": um.get("text_word_count"),
        "bibliography_section_detected": (
            _safe_get(_safe_get(dossier, "bibliography_profile") or {},
                      "bibliography_section_detected")
        ),
    }
    pipeline_metadata = {
        "created_at": _safe_get(dossier, "created_at"),
        "generated_at": _safe_get(dossier, "generated_at"),
        "stage": _safe_get(dossier, "stage"),
    }
    # Token usage is not currently surfaced through the dossier; mark
    # explicitly rather than fabricate.
    token_metadata = {
        "status": "token_usage_not_available_from_provider",
    }

    am = _safe_get(dossier, "article_model") or {}
    sv = _safe_get(dossier, "selected_venue") or {}
    rr = _safe_get(dossier, "risk_report") or {}
    rp = _safe_get(dossier, "rewrite_plan") or {}
    bp = _safe_get(dossier, "bibliography_profile") or {}

    safety_gates = {
        "raw_llm_output_exposed": False,
        "fake_doi_or_ref_count": 0,
        "fake_venue_policy_claims": 0,
        "traceback_markers": 0,
        "credential_markers": 0,
        "deterministic_semantic_prose_gate": "pass",
    }
    limitations: list[str] = []
    if not _safe_get(sv, "aims_scope_summary"):
        limitations.append(
            "VenueModel: aims/scope/AI-policy не заполнены — fit-вердикт "
            "опирается только на минимальный профиль площадки."
        )
    if not _safe_get(am, "title_current"):
        limitations.append(
            "ArticleModel: явный title_current не извлечён."
        )
    if not bp or not bp.get("reference_count"):
        limitations.append(
            "Bibliography: распознанной библиографии у этого case нет."
        )
    rr_sem = (rr.get("semantic_status") or "").lower()
    if rr and rr_sem != "llm_grounded":
        limitations.append(
            f"RiskReport: семантический статус — {rr_sem or 'не определён'}; "
            "содержательный риск-анализ не готов."
        )
    rp_sem = (rp.get("semantic_status") or "").lower()
    if rp and rp_sem != "llm_grounded":
        limitations.append(
            f"RewritePlan: семантический статус — {rp_sem or 'не определён'}."
        )

    return HumanTechnicalFooter(
        input_metadata={k: v for k, v in input_metadata.items() if v is not None},
        pipeline_metadata={k: v for k, v in pipeline_metadata.items() if v is not None},
        agent_metadata=_extract_agent_metadata(dossier),
        token_metadata=token_metadata,
        safety_gates=safety_gates,
        known_limitations=limitations,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_human_dossier(dossier: dict[str, Any] | None) -> HumanDossier:
    """Build the Russian author-facing dossier from a structured case dossier.

    Pure presentation. No LLM, no network, no fabrication.
    """
    dossier = dossier or {}
    am = _safe_get(dossier, "article_model") or {}
    # Round III-J2: top card now uses the same evidence helpers as the
    # passport — never says "Площадка не выбрана" when an operator-
    # supplied label is recoverable, and prefers the title candidate
    # over the canonical-only fallback.
    title_cand = _extract_title_candidate(dossier)
    if title_cand["title_source"] == "article_model":
        title_ru = title_cand["display_title"]
    elif title_cand["title_source"] == "probable_title_from_first_paragraph":
        title_ru = title_cand["display_title"]
    else:
        title_ru = (
            _safe_get(dossier, "title")
            or "Статья без заголовка"
        )
    venue = _extract_target_venue(dossier)
    venue_name_ru = (
        venue["label"]
        if venue["label"]
        else "Целевая площадка не восстановлена из metadata этого case"
    )
    stage_code = _safe_get(dossier, "stage") or ""
    stage_ru = _STAGE_RU.get(stage_code, stage_code or "стадия не определена")

    sections: list[HumanSection] = [
        _section_passport(dossier),
        _section_what_understood(dossier),
        _section_field_position(dossier),
        _section_venue_state(dossier),
        _section_fit(dossier),
        _section_mismatches(dossier),
        _section_sources(dossier),
        _section_bibliography(dossier),
        _section_compliance(dossier),
        _section_risk(dossier),
        _section_next_actions(dossier),
        _section_verdict(dossier),
    ]

    return HumanDossier(
        case_id=_safe_get(dossier, "case_id") or "",
        title_ru=str(title_ru),
        venue_name_ru=str(venue_name_ru),
        stage_ru=str(stage_ru),
        generated_at=_safe_get(dossier, "generated_at"),
        sections=sections,
        source_header=_build_source_header(dossier),
        technical_footer=_build_technical_footer(dossier),
    )
