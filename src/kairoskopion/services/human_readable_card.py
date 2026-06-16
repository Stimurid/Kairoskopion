"""Human-readable model review cards.

Author-facing markdown projections of ArticleModel and VenueModel /
VenueProfilePackage that a humanities author (NOT a developer) can
read and verify before trusting downstream fit/mismatch/venue output.

Triggered by the Mavrinsky review failure: golden ArticleModel + venue
selection were unreadable because their structured representation was
the only surface. This service produces prose with explicit:

  - what the system thinks the article/venue is;
  - what is extracted from source vs inferred vs unknown;
  - protected core (or honest "missing" warning);
  - questions back to the author for verification;
  - correction affordances.

The structured registries remain the source of truth — this is a
projection only. NO LLM, NO network, NO new extraction. The author can
read it, correct it (via `Case.confirm_article_model`), and re-render.

Per task spec §E every human-facing section carries an unobtrusive
HTML comment with the machine field path
(`<!-- field: article_model.<key> -->`) so a future UI can map a
"это неверно" click back to a structured field.
"""

from __future__ import annotations

from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Plain-language dictionaries for enums
# ---------------------------------------------------------------------------

GENRE_PROSE: dict[str, str] = {
    "theoretical_essay": (
        "теоретическое эссе — строит понятие, различение или модель, "
        "не сообщает новое эмпирическое исследование"
    ),
    "theoretical_argument": (
        "теоретический аргумент — выстраивает конструкцию рассуждения и "
        "выводит общий тезис, а не описывает данные"
    ),
    "empirical_paper": (
        "эмпирическая статья — представляет данные, метод и результат "
        "конкретного исследования"
    ),
    "case_study": (
        "кейс-стади — анализ одного случая, события, объекта"
    ),
    "review_article": (
        "обзорная статья — синтез существующей литературы по теме"
    ),
    "systematic_review": (
        "систематический обзор — структурированный сбор и оценка "
        "опубликованных работ по протоколу"
    ),
    "commentary": (
        "комментарий — реплика на чужую работу или событие в поле"
    ),
    "position_paper": (
        "позиционная статья — заявление позиции автора по дискуссии"
    ),
    "methods_paper": (
        "методологическая статья — представляет метод или инструмент"
    ),
    "book_review": "рецензия на книгу",
    "short_communication": "короткое сообщение",
    "conceptual_article": (
        "концептуальная статья — вводит или переосмысляет понятие"
    ),
    "essay": "эссе свободной формы",
}

METHOD_PROSE: dict[str, str] = {
    "no_method_continental_argument": (
        "методом в эмпирическом смысле не пользуется — это континентальный "
        "философский аргумент, который не опирается на данные или процедуру"
    ),
    "conceptual_method": (
        "использует концептуальный метод — строит понятийную работу: "
        "различения, реконструкцию, переопределение"
    ),
    "textual_analysis": "опирается на работу с текстами / источниками",
    "interpretive_method": "интерпретативный метод",
    "comparative_method": "сравнительный метод",
    "ethnographic": "этнографическое исследование",
    "qualitative_empirical": "качественное эмпирическое исследование",
    "quantitative_empirical": "количественное эмпирическое исследование",
    "experimental": "экспериментальный метод",
    "computational": "вычислительный / алгоритмический метод",
    "mixed_methods": "смешанные методы",
    "unknown": "метод пока не определён системой",
}

NOVELTY_PROSE: dict[str, str] = {
    "concept_introduction": (
        "вводит новое понятие или различение"
    ),
    "concept_reconstruction": (
        "переосмысляет существующее понятие"
    ),
    "concept_introduction_with_reconstruction": (
        "одновременно вводит новое различение и переосмысляет смежное "
        "существующее понятие"
    ),
    "new_theory": (
        "формулирует новую теорию или модель"
    ),
    "new_evidence": (
        "представляет новое эмпирическое свидетельство"
    ),
    "translation_between_fields": (
        "переводит понятие или приём из одной области в другую"
    ),
    "refutation": "опровергает существующее положение",
    "synthesis": "синтезирует существующие позиции",
    "unknown": "характер новизны пока не определён системой",
}

EVIDENCE_STATUS_PROSE: dict[str, str] = {
    "official_fact": "взято из официального источника",
    "external_claim": "взято из стороннего источника",
    "vendor_claim": "взято из заявления издателя/площадки",
    "metadata_api_openalex": "получено через OpenAlex",
    "metadata_api_crossref": "получено через Crossref",
    "corpus_observation": "наблюдение из публикационного корпуса",
    "registry_card": "взято из реестра-карточки",
    "operator_seed_canonical": "введено оператором как канонический seed",
    "inference": "это вывод системы (не прямое подтверждение)",
    "user_text_extracted": "извлечено из текста автора",
    "tacit_signal": "tacit-сигнал (низкая достоверность)",
    "unknown": "источник неизвестен",
}


def _evidence_status_in_prose(value: str | None) -> str:
    if not value:
        return ""
    return EVIDENCE_STATUS_PROSE.get(value, value)


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _is_present(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip()) and v.strip().lower() not in {"unknown", "none"}
    if isinstance(v, (list, dict)):
        return bool(v)
    return True


def _field_anchor(path: str) -> str:
    """Embed a machine field reference as an HTML comment."""
    return f"<!-- field: {path} -->"


def _h(level: int, title: str, field_path: str | None = None) -> str:
    hashes = "#" * level
    anchor = f" {_field_anchor(field_path)}" if field_path else ""
    return f"{hashes} {title}{anchor}\n"


# ---------------------------------------------------------------------------
# Article view
# ---------------------------------------------------------------------------

def _short_summary_article(article: dict[str, Any]) -> str:
    """Section 1: what the system thinks this article is, in 3–6 sentences."""
    lines: list[str] = []
    obj = _safe_str(article.get("object_of_inquiry"))
    problem = _safe_str(
        article.get("central_problem") or article.get("problem_statement")
    )
    genre = _safe_str(article.get("genre_current") or article.get("genre"))
    novelty = _safe_str(article.get("novelty_mode"))
    method = _safe_str(article.get("method_status"))
    lifecycle = _safe_str(article.get("lifecycle_status")) or "preliminary"
    confirmed = lifecycle.lower() not in {"preliminary", "draft", "unconfirmed"}

    if obj:
        lines.append(
            f"Система понимает, что статья работает вокруг следующего объекта: "
            f"**{obj}**."
        )
    else:
        lines.append(
            "Главный объект статьи система пока не зафиксировала — пометьте "
            "сами или попросите перечитать текст."
        )

    if problem:
        lines.append(
            f"Главное напряжение, которое система увидела в тексте: "
            f"**{problem}**."
        )

    genre_prose = GENRE_PROSE.get(genre, "")
    method_prose = METHOD_PROSE.get(method, "")
    if genre_prose:
        lines.append(f"По типу это {genre_prose}.")
    if method_prose and method_prose not in (genre_prose, ""):
        lines.append(f"По способу работы — {method_prose}.")
    if novelty:
        novelty_prose = NOVELTY_PROSE.get(novelty, "")
        if novelty_prose:
            lines.append(f"По характеру новизны система видит, что текст {novelty_prose}.")

    lines.append(
        "Эта модель **предварительная** — она построена системой и НЕ "
        "является финальным заявлением о статье. Прочитайте её, отметьте "
        "ошибки и подтвердите, что главное передано верно."
        if not confirmed
        else "Эта модель отмечена как **подтверждённая автором**."
    )
    return " ".join(lines)


def _section_object(article: dict[str, Any]) -> str:
    body = _h(2, "Главный объект статьи", "article_model.object_of_inquiry")
    obj = _safe_str(article.get("object_of_inquiry"))
    if obj:
        body += f"{obj}\n\n"
        ev = _evidence_status_in_prose(
            article.get("object_of_inquiry_evidence_status")
            or article.get("evidence_status")
        )
        if ev:
            body += f"_{ev}._\n"
    else:
        body += (
            "Главный объект статьи пока не выделен.\n"
            "Это вывод системы — её модель не содержит чёткого ответа на "
            "вопрос «о чём эта статья». Уточните сами или попросите "
            "перечитать с другим input_type.\n"
        )
    return body


def _section_problem(article: dict[str, Any]) -> str:
    body = _h(
        2, "Главная проблема и напряжение",
        "article_model.central_problem",
    )
    problem = _safe_str(
        article.get("central_problem")
        or article.get("problem_statement")
    )
    if problem:
        body += f"{problem}\n"
    else:
        body += (
            "Главная проблема пока не зафиксирована системой. Без этого "
            "невозможно содержательно оценить fit с конкретной площадкой.\n"
        )
    return body


def _section_claims(article: dict[str, Any]) -> str:
    body = _h(2, "Основные утверждения статьи", "article_model.core_claims")
    claims = article.get("core_claims") or []
    if not claims:
        body += (
            "Система не смогла выделить основные утверждения. Возможные "
            "причины: текст слишком короткий; формулировка не строится "
            "как «тезис → аргумент»; LLM-обработка не прошла валидацию и "
            "сработал детерминированный фоллбэк.\n"
        )
        return body
    ev_default = _evidence_status_in_prose(article.get("evidence_status")) or \
        "это вывод системы по тексту"
    body += f"_Происхождение этих утверждений: {ev_default}._\n\n"
    for i, c in enumerate(claims, 1):
        c = _safe_str(c)
        if c:
            body += f"{i}. {c}\n"
    return body


def _section_kind(article: dict[str, Any]) -> str:
    body = _h(2, "Тип статьи", "article_model.genre_current")
    genre = _safe_str(article.get("genre_current") or article.get("genre"))
    method = _safe_str(article.get("method_status"))
    novelty = _safe_str(article.get("novelty_mode"))

    genre_prose = GENRE_PROSE.get(genre, "")
    method_prose = METHOD_PROSE.get(method, "")
    novelty_prose = NOVELTY_PROSE.get(novelty, "")

    if genre_prose:
        body += f"**Жанр.** Система считает, что это {genre_prose}.\n\n"
    elif genre:
        body += f"**Жанр.** Система ставит метку `{genre}` — описание этого ярлыка в каноне пока не закреплено.\n\n"
    else:
        body += "**Жанр.** Не определён.\n\n"

    if method_prose:
        body += f"**Способ работы.** {method_prose}.\n\n"
    elif method:
        body += f"**Способ работы.** Системная метка: `{method}`.\n\n"
    else:
        body += "**Способ работы.** Не определён.\n\n"

    if novelty_prose:
        body += f"**Что нового.** Система видит, что текст {novelty_prose}.\n"
    elif novelty:
        body += f"**Что нового.** Системная метка: `{novelty}`.\n"
    else:
        body += "**Что нового.** Не определено.\n"
    return body


def _section_disciplines(
    article: dict[str, Any],
    pathways: list[dict[str, Any]] | None,
) -> str:
    body = _h(2, "Дисциплинарные регистры", "article_model.disciplinary_registers")
    registers = article.get("disciplinary_registers") or []

    # If any pathway carries a fallback attempt metadata, surface a
    # single visible warning at the start of the section. Same shape as
    # the ArticleModel fallback warning.
    if pathways:
        for p in pathways:
            ea = (p or {}).get("extraction_attempt") or {}
            if ea.get("fallback_used"):
                warn = ea.get("warning_for_user") or (
                    "Часть дисциплинарной карты построена в "
                    "предварительном режиме."
                )
                body += (
                    f"\n> ⚠ **Дисциплинарная карта: {warn}**\n\n"
                    f"> _(parse_status: `{ea.get('parse_status', 'unknown')}` · "
                    f"fallback_reason: `{ea.get('fallback_reason', 'unknown')}`)_\n\n"
                )
                break  # one banner is enough

    if not pathways and not registers:
        body += (
            "Дисциплинарные регистры пока не зафиксированы. Это значит "
            "система пока не предлагает дисциплинарный мир, в котором "
            "текст можно прочесть как уместный — определите его сами.\n"
        )
        return body

    if registers:
        body += "Система считает, что текст работает в следующих регистрах:\n\n"
        for r in registers:
            r = _safe_str(r)
            if r:
                body += f"- {r}\n"
        body += "\n"

    if pathways:
        body += (
            "Возможные публикационные траектории (что система предлагает "
            "как направление поиска журналов):\n\n"
        )
        for p in pathways[:10]:
            name = _safe_str(p.get("discipline_name")) or "без названия"
            fit = _safe_str(p.get("fit_strength")) or "неизвестно"
            reasoning = _safe_str(p.get("reasoning"))
            body += f"- **{name}** — сила сигнала: {fit}.\n"
            if reasoning:
                body += f"  _Почему_: {reasoning}\n"
        body += (
            "\n_Эти траектории — гипотезы, а не рекомендации. "
            "«Сильный» сигнал означает, что текст хорошо ложится в этот мир по "
            "доступным признакам; не означает, что нужно туда подавать._\n"
        )
    return body


def _section_theory(article: dict[str, Any]) -> str:
    body = _h(2, "Теоретические плечи, оппоненты, словарь",
              "article_model.theoretical_shoulders")
    shoulders = article.get("theoretical_shoulders") or []
    opponents = article.get("opponents_or_contrasts") or []
    terms = article.get("key_terms") or []
    citation = _safe_str(article.get("citation_ecology_current"))
    tribes = article.get("tribes_present") or {}

    any_present = bool(shoulders or opponents or terms or citation or tribes)
    if not any_present:
        body += (
            "Эти поля пока не заполнены системой. Это значит **неизвестно**, "
            "а не «отсутствует» — пожалуйста, заполните сами.\n"
        )
        return body

    if shoulders:
        body += "**Теоретические плечи.**\n"
        for s in shoulders:
            body += f"- {_safe_str(s)}\n"
        body += "\n"
    if tribes:
        body += "**Линии, на которые система опирается:**\n"
        for k, v in tribes.items():
            body += f"- {k} → {v}\n"
        body += "\n"
    if opponents:
        body += "**Оппоненты или контрастные позиции.**\n"
        for o in opponents:
            body += f"- {_safe_str(o)}\n"
        body += "\n"
    if terms:
        body += "**Ключевые термины.** " + ", ".join(_safe_str(t) for t in terms) + ".\n\n"
    if citation:
        body += f"**Цитатная экология (наблюдение системы).** {citation}\n"
    return body


def _section_protected_core(article: dict[str, Any]) -> str:
    body = _h(2, "Неприкосновенное ядро", "article_model.protected_core")
    core = article.get("protected_core") or []
    if not core:
        body += (
            "Система пока не знает, что автор считает неприкосновенным "
            "ядром статьи. Без этого любые fit/rewrite выводы остаются "
            "предварительными, потому что система не понимает, что "
            "**нельзя** менять ради журнала.\n\n"
            "Заполните этот раздел — это самый важный шаг для "
            "осмысленного fit-анализа.\n"
        )
        return body
    body += "Эти элементы система не будет предлагать менять при адаптации:\n\n"
    for i, item in enumerate(core, 1):
        body += f"{i}. {_safe_str(item)}\n"
    return body


def _section_unknowns(article: dict[str, Any]) -> str:
    body = _h(2, "Что система не знает", "article_model.unknowns")
    unknowns = article.get("unknowns") or []
    technical_to_human = {
        "abstract missing": "у системы нет абстракта статьи",
        "shallow": "модель статьи получилась поверхностной — слишком мало текста",
        "genre not detected": "тип статьи не удалось определить",
        "method not detected": "способ работы не удалось определить",
        "novelty mode not detected": "характер новизны не зафиксирован",
        "protected core not confirmed by user": (
            "автор ещё не подтвердил неприкосновенное ядро"
        ),
    }
    if unknowns:
        body += "Сейчас система явно не знает следующего:\n\n"
        for u in unknowns:
            u_s = _safe_str(u)
            humanized = None
            for needle, repl in technical_to_human.items():
                if needle.lower() in u_s.lower():
                    humanized = repl
                    break
            body += f"- {humanized or u_s}\n"
        body += "\n"
    # Plain-language unknowns that always apply at preliminary stage
    body += "Также система пока **не знает** следующего:\n\n"
    body += "- какой у автора **целевой журнал** или класс площадок;\n"
    body += "- какие у автора **ограничения по сценарию подачи** (Scopus/ВАК/OA/APC/deadline);\n"
    body += "- **полный список источников**, на которые опирается статья;\n"
    body += "- **цель публикации** (статус, бюджет, переводимость, обходные форматы).\n"
    return body


def _section_questions_article() -> str:
    body = _h(2, "Вопросы автору для проверки модели")
    questions = [
        "Правильно ли система поняла **главный объект** статьи?",
        "Какие из перечисленных **утверждений** действительно ваши, а какие система додумала?",
        "Есть ли утверждение, которое система **пропустила или исказила**?",
        "К какому дисциплинарному миру вы хотите это отнести — и что туда **точно не подходит**?",
        "Что в статье **нельзя менять** ради журнала (неприкосновенное ядро)?",
        "Это **концептуальный текст** или у вас есть эмпирический материал, который я не вижу?",
        "Какая **цель публикации** — статус, обмен, дискуссия, экзотика, обходная площадка?",
    ]
    body += "Ответьте на эти вопросы (себе или прямо в этой панели), прежде чем доверять fit-анализу или venue-подбору.\n\n"
    for q in questions:
        body += f"- {q}\n"
    return body


def _section_corrections_article() -> str:
    body = _h(2, "Что можно поправить")
    body += (
        "Прямо в этой модели можно скорректировать или подтвердить:\n\n"
        "- **Главный объект** статьи "
        "<!-- field: article_model.object_of_inquiry -->\n"
        "- **Главную проблему / напряжение** "
        "<!-- field: article_model.central_problem -->\n"
        "- **Основные утверждения** "
        "<!-- field: article_model.core_claims -->\n"
        "- **Дисциплинарные регистры** "
        "<!-- field: article_model.disciplinary_registers -->\n"
        "- **Жанр** "
        "<!-- field: article_model.genre_current -->\n"
        "- **Способ работы (метод)** "
        "<!-- field: article_model.method_status -->\n"
        "- **Новизну** "
        "<!-- field: article_model.novelty_mode -->\n"
        "- **Неприкосновенное ядро** — самое важное "
        "<!-- field: article_model.protected_core -->\n"
        "- **Список того, что я не знаю** "
        "<!-- field: article_model.unknowns -->\n"
        "- **Заголовок / рабочая аннотация** (если они генерировались "
        "системой) "
        "<!-- field: article_model.title_current -->\n"
        "- **Цитатная экология** (что вы цитируете и что подчёркнуто "
        "отсутствует) "
        "<!-- field: article_model.citation_ecology_current -->\n\n"
        "После правок нажмите **«Подтвердить модель»** — она перестанет "
        "быть `preliminary` и переключится в `confirmed_by_user`.\n"
    )
    return body


def _layer_fallback_banner(
    layer_phrase: str, attempt: dict[str, Any] | None,
) -> str:
    """Render a Russian fallback banner for any layer (semantic/fit/etc.).

    Returns an empty string when no fallback fired.
    Used by the article human view to surface semantic_profile and
    fit_assessment fallback states beside the article-level one.

    Args:
      layer_phrase: full Russian phrase with correct gender agreement,
        e.g. "Семантический профиль построен в предварительном режиме"
        (masculine) or "Оценка соответствия построена в предварительном
        режиме" (feminine).
      attempt: the LLMAttemptMetadata dict from the layer.
    """
    if not attempt or not attempt.get("fallback_used"):
        return ""
    warn = attempt.get("warning_for_user") or (
        "LLM-вызов не дал корректный результат, поэтому использован fallback."
    )
    parse_status = attempt.get("parse_status", "unknown")
    fallback_reason = attempt.get("fallback_reason", "unknown")
    return (
        f"> ⚠ **{layer_phrase}:** {warn}\n\n"
        f"> _(parse_status: `{parse_status}` · fallback_reason: "
        f"`{fallback_reason}`)_\n\n"
    )


def article_model_human_view(
    article: dict[str, Any],
    pathways: list[dict[str, Any]] | None = None,
    semantic_profile: dict[str, Any] | None = None,
    fit_assessment: dict[str, Any] | None = None,
) -> str:
    """Render the 11-section author-facing markdown view of an ArticleModel.

    Args:
      article: dict shape of an ArticleModel (ArticleModel.to_dict()).
      pathways: optional list of DisciplinaryPathway dicts to enrich
                section 6 with reasoning per pathway.
      semantic_profile: optional ArticleSemanticProfile dict. If it
                carries fallback metadata, a Russian warning is surfaced
                at the top of the view.
      fit_assessment: optional FitAssessment dict. Same surfacing.

    Returns:
      Markdown string, ready for direct cockpit rendering or vault
      storage.
    """
    article = article or {}
    title = _safe_str(article.get("title_current")) or "Untitled article"
    lifecycle = _safe_str(article.get("lifecycle_status")) or "preliminary"
    extraction_attempt = article.get("extraction_attempt") or {}

    lines: list[str] = []
    # Frontmatter — kept for vault navigation; cockpit ignores it
    lines.append("---")
    lines.append(f"id: {article.get('article_model_id', '')}")
    lines.append("type: ArticleModel (human view)")
    lines.append(f"lifecycle: {lifecycle}")
    lines.append("not_a_submission_recommendation: true")
    if extraction_attempt:
        lines.append(
            f"parse_status: {extraction_attempt.get('parse_status', 'unknown')}"
        )
        if extraction_attempt.get("fallback_used"):
            lines.append(
                f"fallback_reason: {extraction_attempt.get('fallback_reason')}"
            )
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(
        "> **Это предварительная модель статьи, построенная системой.** "
        "Она НЕ является рекомендацией по подаче. До того как доверять "
        "результатам fit-анализа или подбору журналов, прочтите модель и "
        "подтвердите/исправьте её ниже."
    )
    lines.append("")

    # LLM-fallback warning, if attempted-and-failed
    if extraction_attempt.get("fallback_used"):
        warning = extraction_attempt.get("warning_for_user")
        if warning:
            lines.append(
                f"> ⚠ **{warning}**"
            )
            lines.append("")
            lines.append(
                f"> _(parse_status: `{extraction_attempt.get('parse_status', 'unknown')}` · "
                f"fallback_reason: `{extraction_attempt.get('fallback_reason', 'unknown')}`)_"
            )
            lines.append("")

    # Per-layer fallback warnings — semantic profile + fit assessment.
    # Each is shown only if it carries `fallback_used: True`.
    # Russian gender agreement: "профиль" is masculine, "оценка" is
    # feminine, so the verb form differs.
    sem_banner = _layer_fallback_banner(
        "Семантический профиль построен в предварительном режиме",
        semantic_profile.get("extraction_attempt") if semantic_profile else None,
    )
    if sem_banner:
        lines.append(sem_banner)
    fit_banner = _layer_fallback_banner(
        "Оценка соответствия построена в предварительном режиме",
        fit_assessment.get("extraction_attempt") if fit_assessment else None,
    )
    if fit_banner:
        lines.append(fit_banner)

    lines.append(_h(2, "Коротко", "article_model._summary"))
    lines.append(_short_summary_article(article))
    lines.append("")
    lines.append(_section_object(article))
    lines.append(_section_problem(article))
    lines.append(_section_claims(article))
    lines.append(_section_kind(article))
    lines.append(_section_disciplines(article, pathways))
    lines.append(_section_theory(article))
    lines.append(_section_protected_core(article))
    lines.append(_section_unknowns(article))
    lines.append(_section_questions_article())
    lines.append(_section_corrections_article())
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Venue view
# ---------------------------------------------------------------------------

def _venue_completeness_label(state: str | None) -> str:
    s = (state or "missing").lower()
    return {
        "present": "собран",
        "partial": "частично собран",
        "missing": "отсутствует",
        "inaccessible": "недоступен для системы",
        "js_only_or_thin": "страница рендерится в JavaScript — извлечение невозможно",
        "auth_required": "требуется авторизация в источнике",
    }.get(s, s)


def _section_venue_identity(v: dict[str, Any]) -> str:
    body = _h(2, "Что это за журнал / площадка", "venue_model.identity")
    name = _safe_str(v.get("canonical_name")) or "(имя не зафиксировано)"
    body += f"**Название.** {name}\n\n"
    pub = _safe_str(v.get("publisher"))
    if pub:
        body += f"**Издатель.** {pub}\n\n"
    vtype = _safe_str(v.get("venue_type"))
    if vtype:
        body += f"**Тип площадки.** {vtype}\n\n"
    langs = v.get("languages") or []
    if langs:
        body += f"**Языки.** {', '.join(_safe_str(l) for l in langs)}\n\n"
    issns = v.get("issns") or []
    if issns:
        body += f"**ISSN.** {', '.join(_safe_str(i) for i in issns)}\n\n"
    home = _safe_str(v.get("homepage_url"))
    if home:
        body += f"**Homepage.** {home}\n\n"
    # Origin
    origin = v.get("discovery_sources") or []
    if origin:
        body += f"**Источник попадания в реестр.** {', '.join(_safe_str(o) for o in origin)}\n\n"
    lifecycle = _safe_str(v.get("evidence_status") or v.get("lifecycle_status")) or "external_claim"
    body += f"**Статус профиля.** {EVIDENCE_STATUS_PROSE.get(lifecycle, lifecycle)}.\n"
    return body


def _section_venue_self_description(v: dict[str, Any]) -> str:
    body = _h(2, "Что журнал сам о себе говорит", "venue_model.aims_scope")
    scope = _safe_str(v.get("scope_summary") or v.get("declared_scope"))
    if scope:
        body += f"{scope}\n\n_Это **vendor_claim** — заявление издателя, а не подтверждённый факт._\n"
        return body
    body += (
        "Официальное описание журнала пока не извлечено системой. Это **неизвестно**, "
        "а не «нет описания» — возможно, страница aims & scope доступна и "
        "имеет смысл её посмотреть вручную.\n"
    )
    return body


def _section_venue_corpus(v: dict[str, Any]) -> str:
    body = _h(2, "Что видно по опубликованному корпусу", "venue_model.corpus_hull")
    completeness = (v.get("completeness") or {}).get("PublishedCorpusHull")
    if completeness not in ("present", "partial"):
        body += (
            "Корпус публикаций журнала пока не собирался системой. Это значит, "
            "что **по реальному корпусу системе нечего сказать** — все "
            "выводы о жанрах, темах, методах в этом профиле — спекулятивны.\n"
        )
        return body
    body += f"_Корпус-хулл собран: {_venue_completeness_label(completeness)} ._\n\n"
    body += (
        "Эти наблюдения помечены `corpus_observation` — это то, что система "
        "увидела в реально опубликованных статьях, а не то, что журнал о себе "
        "заявил.\n\n"
        "Для подробностей попросите оператора показать `published_corpus_hull` "
        "по этому venue_profile_package_id.\n"
    )
    return body


def _section_venue_formal(v: dict[str, Any]) -> str:
    body = _h(
        2, "Формальные требования",
        "venue_model.formal_submission_profile",
    )
    completeness = (v.get("completeness") or {}).get("FormalSubmissionProfile")
    if completeness not in ("present", "partial"):
        body += (
            "Формальные требования (типы статей, длина, абстракт, ссылки, "
            "OA/APC, AI-policy) системой **не извлечены**. Прежде чем "
            "оценивать `formal_compliance`, эти данные нужно собрать "
            "вручную или попросить запустить guidelines-extractor.\n"
        )
        return body
    body += (
        f"_Формальный профиль: {_venue_completeness_label(completeness)} ._\n\n"
        "Каждое извлечённое поле помечено `external_claim_html` и привязано "
        "к URL страницы guidelines. Что недоступно — помечено `UNKNOWN_NOT_FOUND` "
        "(не «нет требования», а «не нашли»).\n"
    )
    return body


def _section_venue_board(v: dict[str, Any]) -> str:
    body = _h(2, "Редколлегия", "venue_model.editorial_board_cloud")
    state = (v.get("completeness") or {}).get("EditorialBoardCloud")
    label = _venue_completeness_label(state)
    body += f"_Состояние: {label}._\n\n"
    if state not in ("present", "partial"):
        body += (
            "Редколлегия системой пока **не собрана** (или board-страница недоступна / "
            "рендерится в JavaScript / закрыта auth). Это означает, что "
            "система **не знает** имён, аффилиаций или академических кластеров "
            "редакции. Никаких выводов о «вкусах редколлегии» не делается.\n"
        )
        return body
    ebc_id = _safe_str(v.get("editorial_board_cloud_id"))
    if ebc_id:
        body += f"Идентификатор облака редколлегии: `{ebc_id}`.\n\n"
    body += (
        "Все имена редколлегии помечены `external_claim` (взяты с board-страницы); "
        "если есть совпадения с OpenAlex Author — помечены `metadata_api_openalex`.\n\n"
        "Производные сигналы (география, концептные кластеры) помечены "
        "`inference` с явным `confidence`. Это **не** заявление о редакторских "
        "предпочтениях — только наблюдение распределения по реестру.\n"
    )
    return body


def _section_venue_inferred(v: dict[str, Any]) -> str:
    body = _h(
        2, "Какой тип текстов журнал, вероятно, распознаёт",
        "venue_model.inferred_genre_expectations",
    )
    body += (
        "Это **вывод системы** (`inference`), полученный из доступных "
        "сигналов: scope, корпус, редколлегия. Не факт об этом журнале.\n\n"
        "Подробный профиль ожиданий (`MethodExpectationProfile`, "
        "`GenreMoveProfile`, `StyleRegisterProfile`, "
        "`CitationExpectationProfile`) появится после deep-pass enrich.\n"
    )
    return body


def _section_venue_unknowns(v: dict[str, Any]) -> str:
    body = _h(2, "Что система не знает", "venue_model.unknowns")
    unk = v.get("unknowns") or []
    body += "Прямо в этом профиле система явно отмечает:\n\n"
    if unk:
        for u in unk[:30]:
            body += f"- {_safe_str(u)}\n"
        body += "\n"
    else:
        body += "_Никаких явных пометок неизвестности на этом профиле нет — "
        body += "что вероятно само по себе подозрительно._\n\n"
    body += "Сверх этого, для **любого** venue по умолчанию неизвестно:\n\n"
    body += "- индексация (Scopus / WoS / ВАК / РИНЦ) — нужен платный источник или ручной чек;\n"
    body += "- impact-factor / Quartile — у системы нет JCR-доступа;\n"
    body += "- редакционная политика по AI-помощникам, кроме явно прописанной;\n"
    body += "- актуальные deadlines и спецвыпуски;\n"
    body += "- ваш персональный опыт публикации в этом журнале (это **tacit signal**, который вы можете добавить).\n"
    return body


def _section_venue_questions(v: dict[str, Any]) -> str:
    body = _h(2, "Вопросы пользователю")
    body += (
        "- Есть ли у вас **личный опыт** с этим журналом — подавали, отказывали, рецензировали?\n"
        "- Этот журнал важен **сам по себе** (целевой) или как **пример класса**?\n"
        "- Нужны ли вам Scopus / WoS / ВАК / РИНЦ — это меняет приоритет?\n"
        "- Допустим ли APC? Если да — какой потолок?\n"
        "- Есть ли deadline (спецвыпуск, конкурс, грантовое требование)?\n"
        "- Нужен ли **deep profile** (полный editorial-board + corpus pattern + formal profile) или хватает текущего среза?\n"
    )
    return body


def _section_venue_corrections() -> str:
    body = _h(2, "Что можно поправить")
    body += (
        "В этом профиле вы можете:\n\n"
        "- сообщить, что **identity неверна** (не тот журнал, дубликат, переименование) "
        "<!-- field: venue_model.canonical_name -->\n"
        "- добавить **официальный URL** (homepage / submission / guidelines / board) "
        "<!-- field: venue_model.official_urls -->\n"
        "- добавить **личный tacit-signal** (ваш опыт; будет сохранён с "
        "`evidence_status=tacit_signal`, `confidence=low`) "
        "<!-- field: venue_model.tacit_venue_signals -->\n"
        "- **отклонить кандидата** — пометить, что этот venue не релевантен текущей статье "
        "<!-- field: venue_candidate.status -->\n"
        "- **пометить источник устаревшим** (board-страница изменилась, scope обновился) "
        "<!-- field: venue_model.last_refreshed_at -->\n"
        "- **запросить deep profile** — система соберёт board + corpus + formal заново "
        "<!-- field: venue_model.profile_depth_request -->\n"
    )
    return body


def venue_human_view(
    venue: dict[str, Any],
) -> str:
    """Render the 9-section author-facing markdown view of a VenueModel
    or VenueProfilePackage dict.

    Args:
      venue: dict shape of either a VenueModel or VenueProfilePackage
             (both share the relevant fields).

    Returns:
      Markdown string.
    """
    venue = venue or {}
    name = _safe_str(venue.get("canonical_name")) or "(имя не зафиксировано)"
    lifecycle = _safe_str(venue.get("evidence_status")) or "external_claim"

    lines: list[str] = []
    lines.append("---")
    lines.append(f"id: {venue.get('venue_profile_package_id') or venue.get('venue_model_id', '')}")
    lines.append("type: VenueProfile (human view)")
    lines.append(f"evidence_status: {lifecycle}")
    lines.append("not_a_submission_recommendation: true")
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("")
    lines.append(
        "> **Это предварительный профиль площадки.** Он НЕ является "
        "рекомендацией по подаче. Прочтите и при необходимости попросите "
        "глубже собрать данные, прежде чем доверять выводам fit-анализа."
    )
    lines.append("")
    lines.append(_section_venue_identity(venue))
    lines.append(_section_venue_self_description(venue))
    lines.append(_section_venue_corpus(venue))
    lines.append(_section_venue_formal(venue))
    lines.append(_section_venue_board(venue))
    lines.append(_section_venue_inferred(venue))
    lines.append(_section_venue_unknowns(venue))
    lines.append(_section_venue_questions(venue))
    lines.append(_section_venue_corrections())
    return "\n".join(lines)
