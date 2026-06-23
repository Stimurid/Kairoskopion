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
class HumanDossier:
    case_id: str
    title_ru: str
    venue_name_ru: str
    stage_ru: str
    generated_at: str | None
    sections: list[HumanSection]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title_ru": self.title_ru,
            "venue_name_ru": self.venue_name_ru,
            "stage_ru": self.stage_ru,
            "generated_at": self.generated_at,
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
        }


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
    return out


def _is_doi_like(text: str) -> bool:
    return bool(re.search(r"\b10\.\d{4,9}/[^\s\"']+", text or ""))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_passport(dossier: dict[str, Any]) -> HumanSection:
    am = _safe_get(dossier, "article_model") or {}
    sv = _safe_get(dossier, "selected_venue") or {}
    genre_code = _safe_get(am, "genre_current") or "unknown"
    genre_ru = _GENRE_RU.get(genre_code, genre_code)
    lang = _safe_get(am, "language") or "не указан"
    conf = _safe_get(am, "confidence") or "не указана"
    venue_name = _safe_get(sv, "canonical_name") or "площадка не выбрана"
    venue_conf = _safe_get(sv, "confidence") or "не указана"
    venue_aims = _safe_get(sv, "aims_scope_summary") or _safe_get(sv, "scope_summary")

    p1 = (
        f"Перед нами {genre_ru}. Язык статьи: {lang}. "
        f"Уверенность модели в реконструкции статьи: {conf}."
    )
    p2 = (
        f"Статья примеряется на площадку «{venue_name}». "
        f"Уверенность в профиле площадки: {venue_conf}."
    )
    notes = []
    if not venue_aims:
        notes.append(
            "Главная оговорка: подробного описания журнала в системе сейчас "
            "недостаточно — fit-проверка предварительная. Чтобы сделать "
            "вывод увереннее, нужно собрать про журнал больше материала "
            "(scope, типы статей, языковая политика, требования к объёму "
            "и оформлению)."
        )
    bullets = []
    fa = _safe_get(dossier, "fit_assessment") or {}
    overall = _safe_get(fa, "overall_label")
    if overall:
        bullets.append(
            f"Текущий общий вердикт fit-проверки: «{overall}» "
            f"(см. раздел 5)."
        )
    if _safe_get(am, "title_current"):
        bullets.append(f"Заголовок статьи: «{am['title_current']}».")
    else:
        bullets.append(
            "Заголовок статьи системой не извлечён — это значит, что "
            "распознанный article-модель пока без официального title; "
            "автору стоит проверить, есть ли в тексте явный заголовок."
        )
    return HumanSection(
        id="passport",
        title_ru="1. Паспорт",
        paragraphs=[p1, p2] + notes,
        bullets=bullets,
    )


def _section_what_understood(dossier: dict[str, Any]) -> HumanSection:
    am = _safe_get(dossier, "article_model") or {}
    paragraphs: list[str] = []
    if _safe_get(am, "problem_statement"):
        paragraphs.append(
            "Центральная проблема, как её зафиксировала система: "
            f"{am['problem_statement']}"
        )
    if _safe_get(am, "research_question"):
        paragraphs.append(
            f"Исследовательский вопрос: {am['research_question']}"
        )
    if _safe_get(am, "object_of_inquiry"):
        paragraphs.append(
            f"Объект рассмотрения: {am['object_of_inquiry']}"
        )
    if _safe_get(am, "method_description"):
        paragraphs.append(
            f"Метод, как он описан: {am['method_description']}"
        )

    bullets: list[str] = []
    claims = _nonempty_list(_safe_get(am, "core_claims"))
    if claims:
        bullets.append("Основные тезисы статьи (как их видит система):")
        bullets.extend(f"— {c}" for c in claims)

    genre = _GENRE_RU.get(
        _safe_get(am, "genre_current") or "unknown",
        _safe_get(am, "genre_current") or "не определён",
    )
    register = _safe_get(am, "disciplinary_register_current")
    if isinstance(register, list):
        register_str = _ru_join(register)
    else:
        register_str = register or ""
    if genre or register_str:
        line = f"Жанр и дисциплинарный регистр: {genre}"
        if register_str:
            line += f"; регистр — {register_str}"
        paragraphs.append(line + ".")

    pcore = _nonempty_list(_safe_get(am, "protected_core"))
    if pcore:
        bullets.append(_PROTECTED_CORE_HINT)
        bullets.append("Защищаемое ядро статьи:")
        bullets.extend(f"— {c}" for c in pcore)
    mzones = _nonempty_list(_safe_get(am, "mutable_zones"))
    if mzones:
        bullets.append(_MUTABLE_HINT)
        bullets.append("Гибкие зоны для доработки:")
        bullets.extend(f"— {z}" for z in mzones)

    unknowns = _nonempty_list(_safe_get(am, "unknowns"))
    if unknowns:
        bullets.append(
            "Чего система про статью пока не знает (поля, которые "
            "ArticleModeler пометил как unknown):"
        )
        bullets.extend(f"— {u}" for u in unknowns[:8])

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
    afp = _safe_get(dossier, "article_field_position") or {}
    paragraphs: list[str] = []
    bullets: list[str] = []

    disc = _safe_get(sp, "primary_discipline")
    regs = _nonempty_list(_safe_get(sp, "disciplinary_registers"))
    if disc or regs:
        line = "Где статья располагается в академическом поле: "
        parts = []
        if disc:
            parts.append(f"основная дисциплина — {disc}")
        if regs:
            parts.append("задействованные регистры — " + _ru_join(regs))
        paragraphs.append(line + "; ".join(parts) + ".")

    schools = _nonempty_list(_safe_get(sp, "schools_and_traditions"))
    if schools:
        bullets.append("Школы и традиции, на которые опирается статья:")
        bullets.extend(f"— {s}" for s in schools)
    shoulders = _nonempty_list(_safe_get(sp, "theoretical_shoulders"))
    if shoulders:
        bullets.append("Теоретические «плечи» — на ком статья стоит:")
        bullets.extend(f"— {s}" for s in shoulders)
    foils = _nonempty_list(_safe_get(sp, "opponents_or_foils"))
    if foils:
        bullets.append("Оппоненты или фоновые контр-позиции:")
        bullets.extend(f"— {s}" for s in foils)

    bridges = _nonempty_list(_safe_get(sp, "citation_bridges_needed"))
    if bridges:
        bullets.append(
            "Какие мосты к традициям системе кажутся необходимыми, "
            "чтобы статья читалась полноценно в этой дисциплинарной "
            "рамке (это карта направлений, а не список обязательных "
            "цитат):"
        )
        bullets.extend(f"— {b}" for b in bridges)

    move = _safe_get(sp, "argument_move_type")
    move_desc = _safe_get(sp, "argument_move_description")
    if move or move_desc:
        line = "Тип аргументативного хода"
        if move:
            line += f": {move}"
        if move_desc:
            line += f" — {move_desc}"
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
    sv = _safe_get(dossier, "selected_venue") or {}
    name = _safe_get(sv, "canonical_name") or "площадка не выбрана"
    conf = _safe_get(sv, "confidence") or "не указана"
    aims = _safe_get(sv, "aims_scope_summary") or _safe_get(sv, "scope_summary")
    p = [
        f"Площадка для подачи: «{name}». "
        f"Уверенность системы в профиле этой площадки: {conf}."
    ]
    if aims:
        p.append(f"Что сейчас известно про scope: {aims}")
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
        paragraphs.append(f"Рекомендация системы: {rec}")

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
            line += f". {notes}"
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
    sv = _safe_get(dossier, "selected_venue") or {}
    if (_safe_get(am, "genre_current") or "").lower() in (
        "theoretical_essay", "theoretical_argument",
        "conceptual_article", "essay",
    ) and not _safe_get(sv, "aims_scope_summary"):
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
        article_side = (m.get("article_side") or "").strip()
        venue_side = (m.get("venue_side") or "").strip()
        descr = (m.get("description") or "").strip()
        actions = _nonempty_list(m.get("possible_actions"))
        core_risk = (m.get("field_core_risk") or "").lower()
        sub_paragraphs: list[str] = []
        if article_side:
            sub_paragraphs.append(f"На стороне статьи: {article_side}")
        if venue_side:
            sub_paragraphs.append(f"На стороне площадки: {venue_side}")
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
            sub_paragraphs.append(descr)
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

    gaps = _nonempty_list(cp.get("citation_gap_categories"))
    bridges = _nonempty_list(cp.get("missing_bridge_categories"))
    tasks = _nonempty_list(cp.get("recommended_reference_search_tasks"))
    verif = _nonempty_list(cp.get("verification_tasks"))
    danger = _nonempty_list(cp.get("dangerous_padding_warnings"))
    unknowns = _nonempty_list(cp.get("unknowns"))

    subsections: list[HumanSubsection] = []
    if gaps:
        subsections.append(HumanSubsection(
            title_ru=f"Категории лакун ({len(gaps)})",
            bullets=[f"— {g}" for g in gaps],
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
            bullets=[f"— {b}" for b in bridges],
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
            bullets=[f"— {_translate_search_task(t)}" for t in tasks],
        ))
    if verif:
        subsections.append(HumanSubsection(
            title_ru=f"Проверочные задачи ({len(verif)})",
            bullets=[f"— {_translate_search_task(v)}" for v in verif],
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
            bullets=[f"— {w}" for w in danger],
        ))
    if unknowns:
        subsections.append(HumanSubsection(
            title_ru="Чего система про источники прямо не знает",
            bullets=[f"— {u}" for u in unknowns[:8]],
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
            line = f"— {req}" if req else "— требование без явной формулировки"
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
        bullets.extend(f"— {a}" for a in explicit)
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
    sv = _safe_get(dossier, "selected_venue") or {}
    bp = _safe_get(dossier, "bibliography_profile") or {}
    fa = _safe_get(dossier, "fit_assessment") or {}
    has_pcore = bool(_nonempty_list(am.get("protected_core")))
    has_bib = bool(bp) and bool(bp.get("reference_count"))
    overall = (fa.get("overall_label") or "").lower()

    lines: list[str] = []
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
    if not _safe_get(sv, "aims_scope_summary"):
        lines.append(
            "Журнал оценить трудно: его профиль слишком пустой, чтобы "
            "построить уверенный fit. Это не вердикт против журнала; "
            "это вердикт о наличии сведений о нём."
        )
    if overall == "not_enough_data":
        lines.append(
            "Текущий fit — «not_enough_data»: это честный отказ "
            "сделать сильный вывод там, где данных нет. Не нужно "
            "читать его как «статья не подходит»."
        )
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
# Public entry point
# ---------------------------------------------------------------------------

def build_human_dossier(dossier: dict[str, Any] | None) -> HumanDossier:
    """Build the Russian author-facing dossier from a structured case dossier.

    Pure presentation. No LLM, no network, no fabrication.
    """
    dossier = dossier or {}
    am = _safe_get(dossier, "article_model") or {}
    sv = _safe_get(dossier, "selected_venue") or {}
    title_ru = (
        _safe_get(dossier, "title")
        or _safe_get(am, "title_current")
        or "Статья без заголовка"
    )
    venue_name_ru = _safe_get(sv, "canonical_name") or "Площадка не выбрана"
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
    )
