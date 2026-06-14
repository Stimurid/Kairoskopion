"""Build a venue seed corpus from the Mavrinsky-RU research notes.

Converts the operator notes in
`benchmarks/_operator_notes/mavrinsky_venue_research/` into the
canonical 3-JSONL seed corpus format (venues.jsonl, sources.jsonl,
claims.jsonl) that `kairoskopion import-venue-seed` consumes.

This is NOT a generic markdown parser. The Mavrinsky-RU notes are
operator-written; this script hand-encodes the structured data they
contain. When notes are extended (more rounds of research), edit this
script — venue/source/claim dicts at the bottom.

Run:
    python scripts/build_mavrinsky_ru_seed_corpus.py
        --output private_inputs/venue_seeds/mavrinsky_ru_corpus

Output:
    {output}/venues.jsonl
    {output}/sources.jsonl
    {output}/claims.jsonl

Then ingest:
    kairoskopion import-venue-seed --corpus-dir <output> \\
        --storage-root <project-storage>

All IDs are deterministic (slug-based) so re-running this script is
idempotent — no duplicate venue / source records emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Deterministic ID generation (slug-based so re-runs are idempotent).
# ---------------------------------------------------------------------------

def _slug(text: str, n: int = 12) -> str:
    """8-12 char short hash of text, alpha-num lowercase."""
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()
    return h[:n]


def venue_id(canonical_name: str) -> str:
    return f"vrec_mavru_{_slug(canonical_name)}"


def source_id(venue_record_id: str, source_key: str) -> str:
    return f"vsrc_mavru_{_slug(venue_record_id + ':' + source_key)}"


def claim_id(venue_source_id: str, claim_path: str, sequence: int = 0) -> str:
    return f"vclm_mavru_{_slug(venue_source_id + ':' + claim_path + ':' + str(sequence))}"


# ---------------------------------------------------------------------------
# Output structures.
# ---------------------------------------------------------------------------

NOW = "2026-06-14T00:00:00Z"


@dataclass
class VenueDef:
    canonical_name: str
    aliases: list[str]
    issn: str | None = None
    eissn: str | None = None
    publisher: str | None = None
    official_urls: list[str] | None = None
    sources: list[dict[str, Any]] | None = None  # list of source dicts
    claims: list[dict[str, Any]] | None = None   # list of claim dicts

    def to_records(self) -> tuple[dict, list[dict], list[dict]]:
        """Emit (venue_record, source_records, claim_records).

        Source dicts in self.sources have shape:
            {"key": "...", "source_url": "...", "source_title": "...",
             "source_type": "...", "retrieved_at": "...",
             "freshness_window_days": int, "notes": "..."}

        Claim dicts in self.claims have shape:
            {"source_key": "...", "claim_path": "...",
             "claim_value": Any, "evidence_status": "...",
             "confidence": "high|medium|low",
             "quote_or_summary": "..."}
        """
        vrec_id = venue_id(self.canonical_name)
        venue = {
            "venue_record_id": vrec_id,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "issn": self.issn,
            "eissn": self.eissn,
            "publisher": self.publisher,
            "official_urls": self.official_urls or [],
            "created_at": NOW,
            "updated_at": NOW,
        }
        source_records: list[dict] = []
        source_id_by_key: dict[str, str] = {}
        for src in (self.sources or []):
            sid = source_id(vrec_id, src["key"])
            source_id_by_key[src["key"]] = sid
            source_records.append({
                "venue_source_id": sid,
                "venue_record_id": vrec_id,
                "source_url": src.get("source_url"),
                "source_title": src.get("source_title"),
                "source_type": src["source_type"],
                "retrieved_at": src.get("retrieved_at", NOW),
                "freshness_window_days": src.get("freshness_window_days"),
                "extracted_by": src.get("extracted_by", "operator+chrome-mcp+webfetch"),
                "extraction_method": src.get("extraction_method", "page_text"),
                "notes": src.get("notes"),
                "created_at": NOW,
            })

        claim_records: list[dict] = []
        seq_by_path: dict[str, int] = {}
        for clm in (self.claims or []):
            src_key = clm["source_key"]
            if src_key not in source_id_by_key:
                raise ValueError(
                    f"{self.canonical_name}: claim references unknown source_key={src_key!r}"
                )
            sid = source_id_by_key[src_key]
            path = clm["claim_path"]
            seq_by_path[path] = seq_by_path.get(path, 0) + 1
            cid = claim_id(sid, path, seq_by_path[path])
            claim_records.append({
                "venue_claim_id": cid,
                "venue_record_id": vrec_id,
                "venue_source_id": sid,
                "claim_path": path,
                "claim_value": clm["claim_value"],
                "evidence_status": clm["evidence_status"],
                "confidence": clm.get("confidence", "medium"),
                "quote_or_summary": clm.get("quote_or_summary"),
                "conflict_group": clm.get("conflict_group"),
                "created_at": NOW,
            })

        return venue, source_records, claim_records


# ---------------------------------------------------------------------------
# Helpers for compact claim authoring.
# ---------------------------------------------------------------------------

def fact(source_key: str, path: str, value: Any, *, quote: str | None = None) -> dict:
    return {
        "source_key": source_key,
        "claim_path": path,
        "claim_value": value,
        "evidence_status": "official_fact",
        "confidence": "high",
        "quote_or_summary": quote,
    }


def claim(source_key: str, path: str, value: Any, *,
          status: str = "external_claim",
          confidence: str = "medium",
          quote: str | None = None) -> dict:
    return {
        "source_key": source_key,
        "claim_path": path,
        "claim_value": value,
        "evidence_status": status,
        "confidence": confidence,
        "quote_or_summary": quote,
    }


def inference(source_key: str, path: str, value: Any, *,
              confidence: str = "low",
              quote: str | None = None) -> dict:
    return {
        "source_key": source_key,
        "claim_path": path,
        "claim_value": value,
        "evidence_status": "inference",
        "confidence": confidence,
        "quote_or_summary": quote,
    }


# ---------------------------------------------------------------------------
# Venue data — Mavrinsky-RU top set.
# Hand-encoded from the operator notes in
# benchmarks/_operator_notes/mavrinsky_venue_research/.
# ---------------------------------------------------------------------------

VENUES: list[VenueDef] = [
    # ---------------------- Tier A #1 — Stasis -----------------------------
    VenueDef(
        canonical_name="Stasis",
        aliases=["Stasis (EUSP)", "Стасис"],
        issn=None,
        publisher="European University at Saint Petersburg / Stasis Centre for Practical Philosophy",
        official_urls=[
            "https://stasisjournal.net/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://stasisjournal.net/",
             "source_title": "Stasis main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180,
             "notes": "Page returns 403 to bot agents; verified via aggregator + EUSP cross-refs"},
            {"key": "motto_distribution", "source_url": "http://www.mottodistribution.com/shop/stasis-academic-journal-social-and-political-theory.html",
             "source_title": "motto-distribution.com Stasis catalogue listing",
             "source_type": "third_party_summary",
             "freshness_window_days": 90,
             "notes": "Aggregator listing surfaced the editorial board composition"},
            {"key": "stasis_centre_page", "source_url": "https://eusp.org/stasis",
             "source_title": "EUSP Centre for Practical Philosophy «Stasis» faculty page",
             "source_type": "publisher_page",
             "freshness_window_days": 180,
             "notes": "Faculty listing — operational team behind Stasis journal"},
        ],
        claims=[
            fact("motto_distribution", "editorial_board_signal",
                 ["Artemy Magun (ed-in-chief, EUSP)",
                  "Oxana Timofeeva (deputy editor, EUSP)",
                  "Sami Khatib (Berlin/Lebanon)",
                  "Benjamin Noys (UK)",
                  "Ray Brassier (American Univ Beirut)",
                  "Gregor Moder (Univ Ljubljana, Žižek student)",
                  "Jamila Mascat (Italy/Netherlands)",
                  "Vitaly Kosykhin (Russia)"],
                 quote="Per motto-distribution aggregator listing"),
            fact("homepage", "accepted_languages", ["en", "ru"],
                 quote="Bilingual EN+RU OA journal"),
            fact("homepage", "apc_oa", {"open_access": True, "apc": None},
                 quote="Free OA"),
            claim("homepage", "aims_scope",
                  "International journal in social and political philosophy and theory; opens common space between English- and Russian-language philosophical traditions.",
                  status="official_claim", confidence="high"),
            claim("homepage", "recent_issue_signal",
                  ["2024 №1: New Perspectives in Contemporary Continental Philosophy",
                   "2024 №2: New Perspectives in Contemporary Continental Philosophy — 2",
                   "2025 №1: Dialectics",
                   "2025 №2: Modes of Futurity: Prophecies, Utopias, Dystopias"],
                  status="external_claim", confidence="high",
                  quote="2024 series is explicitly Mavrinsky-tribe thematic"),
            claim("stasis_centre_page", "editorial_board_signal",
                  ["Lada Shipovalova (Director, Stasis Centre, SPbU Phil of Sci+Tech Head)",
                   "Yoel Regev (Associate Professor, Stasis Centre — author of «Mole or Snake?» in Logos №1/2024)",
                   "Igor Zaytsev", "Gleb Karpov", "Andrey Patkul",
                   "Nina Savchenkova (Professor)", "Anton Syutkin (Senior Lecturer)"],
                  status="external_claim", confidence="high",
                  quote="EUSP Stasis Centre faculty — operational publication network"),
            claim("motto_distribution", "editorial_board_publications.Magun",
                  ["Andrei Bely Prize 2020: «Искус небытия. Энциклопедия диалектических наук. Том 1. Отрицательная эстетика»",
                   "Boris Grushin Sociological Book Prize 2023: «От триггера к трикстеру. Энциклопедия диалектических наук. Том 2. Негативность в этике» (Voprosy filosofii 2023 review by IF RAN)",
                   "2023 Diaphanes co-edited: «Thinking with Jean-Luc Nancy»",
                   "2020 Rowman: «Civitas Paradoxa or a Dialectical Theory of State» (3 cit)",
                   "2020 book: «The Future of the State: philosophy and politics» (8 cit)",
                   "2017 Stasis: «Boris Porshnev's Dialectic of History» (4 cit)",
                   "2024 Emancipations: Journal of Critical Social Theory: «Toward a Dialectical Theory of Politico-Economic Regimes» (1 cit)",
                   "2026 Studies in East European Thought (Springer): «Conservatism and the dialectic of ideology» (1 cit)",
                   "2018 Springer Studies in East European Thought: «Lenin on democratic theory» (3 cit)",
                   "2018 Stasis: «A Philosophical Theory of Energy» (cites Bibikhin)",
                   "2013 Stasis: «De Negatione: What Does It Mean to Say No?» (2 cit)",
                   "2013 Bloomsbury London: «Unity and Solitude» (6 cit)",
                   "2012 book: «Politics of the One: Concepts of the One and the Many in Contemporary Thought» (14 cit)",
                   "PhD Strasbourg + PhD Michigan; Director Stasis Centre EUSP",
                   "specialization: dialectics, continental political philosophy, negative aesthetics, energy ontology"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar + EUSP + Springer multiple book/journal listings"),
            claim("motto_distribution", "editorial_board_publications.Timofeeva",
                  ["2025 book: «Freud's Beasty Boys: sex, violence and masculinity» (2 cit)",
                   "2022 book: «Solar politics» (31 cit) — TOP-CITED",
                   "2018 book: «The History of Animals: A Philosophy» — Bloomsbury",
                   "2020 Stasis: «From the Philosophy of Nature to a New Materialist Politics» (1 cit)",
                   "2020 Stasis: «From the quarantine to the general strike: On Bataille's political economy» (4 cit)",
                   "2017 e-flux Journal: «Ultra-black: Towards a materialist theory of oil» (8 cit)",
                   "2016 On Culture: «The non-human as such: on men, animals, and barbers» (8 cit)",
                   "2016 Stasis: «Theatre for the Dead» (2 cit) — references Boris Groys politicization vs aestheticization",
                   "2015 Identities: «Unconscious Desire for Communism» (3 cit)",
                   "EUSP + Deputy Editor Stasis + author «What is to be done?»",
                   "specialization: continental + animal philosophy + materialism + Bataille + base materialism"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14"),
            claim("motto_distribution", "editorial_board_publications.Brassier",
                  ["2007 book: «Nihil Unbound: Enlightenment and Extinction» — Palgrave Macmillan, foundational speculative realism text (Johnston 2009 Taylor & Francis review)",
                   "«I am a nihilist because I believe in truth» — defining quote (Speculations III 2012, 53 cit)",
                   "American University Beirut Phil Dept",
                   "Speculative realism canonical member with Harman + Negarestani + Meillassoux",
                   "Critical realism position; concept-naturalism; Sellars-Brandom influence",
                   "specialization: speculative realism + nihilism + naturalism + radical Enlightenment"],
                  status="external_claim", confidence="high",
                  quote="Multiple secondary citations + Hegel and Speculative Realism 2023 Springer"),
        ],
    ),

    # ---------------------- Tier A #2 — Социологическое обозрение ----------
    VenueDef(
        canonical_name="Sociological Review (Russia)",
        aliases=["Социологическое обозрение", "Russian Sociological Review", "Соц.обозр"],
        issn="1728-192X",
        publisher="HSE Center for Fundamental Sociology",
        official_urls=[
            "https://sociologica.hse.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://sociologica.hse.ru/",
             "source_title": "Sociologica main page (HSE Center for Fundamental Sociology)",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "editorial_team", "source_url": "https://sociologica.hse.ru/about/editorialTeam",
             "source_title": "Editorial team page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
            {"key": "vol25_no1", "source_url": "https://sociologica.hse.ru/issue/view/2125",
             "source_title": "Vol 25 No 1 2026 issue page",
             "source_type": "official_archive",
             "freshness_window_days": 365},
        ],
        claims=[
            fact("editorial_team", "editorial_board_signal",
                 [{"name": "Alexander F. Filippov", "role": "Editor-in-Chief",
                   "affiliation": "HSE Center for Fundamental Sociology Director",
                   "tribe": "Schmitt-translator + political theology"},
                  {"name": "Marina Pugacheva", "role": "Deputy",
                   "affiliation": "HSE"},
                  {"name": "Svetlana Bankovskaya", "role": "Board",
                   "affiliation": "HSE Dept Social Institutions Analysis"},
                  {"name": "Ruslan Khestanov", "role": "Board since 2022",
                   "affiliation": "HSE Faculty of Humanities",
                   "tribe": "Foucault governmentality + McLuhan translator"},
                  {"name": "Dmitry Kurakin", "role": "Board",
                   "affiliation": "HSE + Yale Center for Cultural Sociology",
                   "metrics": "Google Scholar h-26, citations 3107"},
                  {"name": "Alexander Pavlov", "role": "Board",
                   "affiliation": "HSE Doctor of Phil; Logos chief editor; RAS Cor Member 2025"},
                  {"name": "Anna Turchik", "role": "Board",
                   "affiliation": "HSE"}],
                 quote="Per https://sociologica.hse.ru/about/editorialTeam"),
            fact("homepage", "indexing_claims", ["DOAJ", "Scopus"],
                 quote="DOAJ + Scopus indexed"),
            fact("vol25_no1", "recent_issue_signal",
                 ["Regular Schmittiana section (Yarkeev — Carl Schmitt's political concept deconstruction)",
                  "AI Application section (Ignatiev+Pakhidnya — Human-Machine Communication research direction)",
                  "Political Philosophy + Russian Atlantis (Berdyaev) + Reviews"],
                 quote="Vol 25 No 1 2026 ToC verified"),
            claim("editorial_team", "ai_policy", "UNKNOWN",
                  status="unknown", confidence="low"),
            claim("homepage", "accepted_languages", ["ru", "en"],
                  status="external_claim", confidence="high"),
        ],
    ),

    # ---------------------- Tier A #3 — Логос ------------------------------
    VenueDef(
        canonical_name="Logos (Russian philosophical-literary journal)",
        aliases=["Логос", "Logos journal"],
        issn="0869-5377",
        eissn="2499-9628",
        publisher="HSE / Anashvili publishing",
        official_urls=[
            "https://logosjournal.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://logosjournal.ru/",
             "source_title": "Logos main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "board", "source_url": "https://logosjournal.ru/board/",
             "source_title": "Logos editorial board page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
            {"key": "council", "source_url": "https://logosjournal.ru/council/",
             "source_title": "Logos editorial council page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
            {"key": "issue_2024_1", "source_url": "https://logosjournal.ru/archive/",
             "source_title": "Logos Vol 34 No 1 2024 «Художественные исследования» special issue (joint with V-A-C foundation + GES-2)",
             "source_type": "official_archive",
             "freshness_window_days": 365},
        ],
        claims=[
            fact("board", "editorial_board_signal",
                 [{"name": "Valery Anashvili", "role": "Editor-in-Chief"},
                  {"name": "Alexander Pavlov", "role": "Chief Editor",
                   "affiliation": "HSE; RAS Cor Member 2025"},
                  {"name": "Vitaly Kurennoy", "role": "Scientific Editor",
                   "affiliation": "HSE Head School of Cultural Studies"},
                  {"name": "Yakov Okhonko", "role": "Managing Secretary"},
                  {"name": "Vyacheslav Danilov", "role": "Editor", "affiliation": "MSU phil-anthr"},
                  {"name": "Dmitry Kralechkin", "role": "Editor/Translator",
                   "affiliation": "Censura.ru + Moscow Philosophical College; Derrida translator"},
                  {"name": "Inna Kushnareva", "role": "Editor/Translator"},
                  {"name": "Artem Morozov", "role": "Editor/Translator"},
                  {"name": "Alexander Pisarev", "role": "Editor/Translator",
                   "affiliation": "IF RAN + HSE Design School",
                   "tribe": "Cross-tribe: analytic epistemology h-7 + Foucault 2024 in Человек"},
                  {"name": "Artem Smirnov", "role": "Editor", "affiliation": "Gaidar Institute Publishing"},
                  {"name": "Polina Khanova", "role": "Editor", "affiliation": "MSU"},
                  {"name": "Igor Chubarov", "role": "Editor", "affiliation": "MSU"},
                  {"name": "Ruslan Khestanov", "role": "Board since 1997"}],
                 quote="Per https://logosjournal.ru/board/"),
            fact("council", "editorial_board_signal",
                 [{"name": "Yuk Hui", "affiliation": "Erasmus Univ Rotterdam",
                   "tribe": "Simondon-Stiegler-Hui line — Mavrinsky must cite or position against"},
                  {"name": "Graham Harman", "affiliation": "SCI-Arc", "tribe": "OOO"},
                  {"name": "Boris Groys", "affiliation": "NYU Slavic", "tribe": "continental media philosophy"},
                  {"name": "John Law", "affiliation": "Open Univ", "tribe": "ANT/STS"},
                  {"name": "Boris Kapustin", "affiliation": "IF RAN"},
                  {"name": "Petar Bojanić", "affiliation": "Belgrade IPST"},
                  {"name": "Klaus Held", "affiliation": "Wuppertal", "tribe": "phenomenology"},
                  {"name": "Christian Möckel", "affiliation": "Humboldt Berlin"},
                  {"name": "Vadim Volkov", "affiliation": "EUSP rector"}],
                 quote="Per https://logosjournal.ru/council/ — world-class continental"),
            fact("homepage", "indexing_claims", ["Scopus Q1", "Web of Science ESCI", "EBSCO", "ProQuest"],
                 quote="Logos main page indexing claims"),
            fact("issue_2024_1", "recent_issue_signal",
                 [{"section": "Художественные исследования (joint V-A-C + GES-2 issue)",
                   "articles": [
                       "Ольга Широкоступ — Блуждая среди высот гор и низин рек",
                       "Дмитрий Кралечкин (board member) — Полураспад светил: знание и его кризисы",
                       "Станислав Шурипа — От метода к предмету",
                       "Константин Бохоров — Сверхъестественное знание как побочный продукт художественного использования ИИ",
                       "Анастасия Алехина + Александр Писарев (board member) — Исполнять технонауку: Art & Science с точки зрения современной метафизики",
                       "Диана Ухина + Бермет Борубаева — Школа методологии художественных исследований",
                       "Йоэль Регев + Алек Петук — Кто я — крот или змея? Направление произведения знания (Deleuze reference)",
                       "Максим Селезнев — Кинематограф в одном кадре",
                   ]}],
                 quote="Two articles by Logos board members in their own dispositif-active issue — confirms Mavrinsky-tribe alive at Logos"),
            inference("homepage", "trust_compliance_profile",
                      {"editorial_political_filtering": "FLAGGED — Meduza 2024 verified censorship concern"},
                      confidence="medium",
                      quote="Svoboda article '«Работа в очистке». Соцсети о цензуре в философском журнале Логос'"),
            claim("board", "editorial_board_publications.Pavlov",
                  ["2024 Philosophy Journal HSE: «Дуология Пеннивайза»",
                   "2025 Philosophy Journal HSE: «Чужие и традиционные ценности» (3 cit)",
                   "2023 Philosophy Journal HSE: «Так ли новы новые подходы к хоррору?» (1 cit)",
                   "2026 Наука телевидения: «Re: Ответ на попытку осмысления монографии об исследованиях хоррора»",
                   "2021 Philosophy Journal HSE: «Что мы делаем в темноте: хоррор и геймплей» (4 cit)",
                   "2021 Philosophy Journal HSE: «Постхоррор?: рецензия на книгу Дэвида Черча» (9 cit)",
                   "2020 State Religion and Church: «Hyper-Real Religion, Lovecraft, and the Cult of the Evil Dead» (4 cit)",
                   "2019: «The Benefits of the Cultural Turn in Slavic Studies for the Studies of the Russian Revolution»",
                   "specialization: horror studies + film philosophy + post-secular religion"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14"),
            claim("board", "editorial_board_publications.Kurennoy",
                  ["2021 International Journal of Cultural Policy (Taylor & Francis): «Contemporary state cultural policy in Russia» (7 cit) — INTERNATIONAL T&F",
                   "2020 Voprosy obrazovaniya: «Philosophy of liberal education: The principles» (48 cit)",
                   "2020 Voprosy obrazovaniya: «Philosophy of Liberal Education: The Contexts»",
                   "2021 Sociologija vlasti (=Соц.власти): «Лабораторная и полевая наука: онтология и эпистемология» (4 cit) — CROSS-VENUE",
                   "2017 Russian Journal of Phil & Humanities: «New Urban Romanticism»",
                   "specialization: German liberal-conservative philosophy of culture (Lübbe); cultural policy; epistemology of laboratory vs field science"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14 — confirms Logos→Соц.власти cross-publishing"),
            claim("board", "editorial_board_publications.Kralechkin",
                  ["2025 Another One Journal: «Монстр: экономия частей и пределы эволюции»",
                   "2001 translation: Jacques Derrida, «Письмо и различие» (Letter and Difference)",
                   "Co-founder Censura.ru philosophical project",
                   "Co-founder Moscow Philosophical College (since 2009)",
                   "Heidegger interpretation cited in Laruelle+Wolin «From Heidegger to Dugin and back» 2022",
                   "specialization: Derrida + Heidegger + cinema philosophy + monster ontology"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar + Laruelle/Wolin 2022 citation"),
            claim("board", "editorial_board_publications.Pisarev",
                  ["2024 Logos Vol 34 №1: «Исполнять технонауку: Art & Science с точки зрения современной метафизики» (co-auth Alekhina)",
                   "2024 Человек: «Несостоявшаяся смерть человека Фуко» — FOUCAULT-DIRECT in another top venue",
                   "2023 Наука телевидения Vol 19 №3: «Art&Science и постгуманизм: технонаука, эстетика и телесность» (co-auth Alekhina)",
                   "2022 Epistemology & Phil of Sci 32(6): «Abductive-deductive method» (10 cit)",
                   "2020 Epistemology & Phil of Sci 30(1): «On the question of truth» (17 cit)",
                   "2018 Epistemology & Phil of Sci 28(5): «Truth and the limits of scientific knowledge» (12 cit)",
                   "Google Scholar: h-7, 193 citations, i10-5",
                   "specialization: CROSS-TRIBE bridge: analytic epistemology (h-index venue) + continental Foucault (recent)"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar profile IeJLTx8AAAAJ"),
        ],
    ),

    # ---------------------- Tier A #4 — Социология власти ------------------
    VenueDef(
        canonical_name="Sociology of Power",
        aliases=["Социология власти", "Sociologija vlasti"],
        issn=None,
        publisher="RANEPA Institute of Social Sciences (Philosophy + Sociology Faculty)",
        official_urls=[
            "https://socofpower.ranepa.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://socofpower.ranepa.ru/",
             "source_title": "Socofpower main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180,
             "notes": "Direct URL frequently ECONNREFUSED; aggregator paths used as backup"},
            {"key": "editorial_board", "source_url": "https://socofpower.ranepa.ru/jour/pages/view/EditorialC?locale=en_US",
             "source_title": "Editorial board page (EN locale path bypasses RU blocks)",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("editorial_board", "editorial_board_signal",
                 [{"name": "Anton Smolkin", "role": "Editor-in-Chief",
                   "affiliation": "RANEPA",
                   "tribe": "continental ethics-of-care (replaced Vakhshtain April 2022)"},
                  {"name": "Alexey Zygmont", "role": "Deputy Editor-in-Chief",
                   "affiliation": "RANEPA, Candidate Philosophical Sciences"},
                  {"name": "Ivan Napreenko", "role": "Scientific Editor",
                   "affiliation": "HSE"},
                  {"name": "Nils Klowaite", "role": "English Materials Editor",
                   "affiliation": "Univ Paderborn, Germany"},
                  {"name": "Slavoj Žižek", "role": "Editorial Board",
                   "affiliation": "Univ of Ljubljana, Slovenia",
                   "tribe": "MAVRINSKY DIRECT — same as Артикульт council"},
                  {"name": "Alexander Filippov", "role": "Editorial Board",
                   "affiliation": "HSE — Соц.обозр Editor-in-Chief",
                   "tribe": "CROSS-BOARD: Соц.обозр + Соц.власти"},
                  {"name": "Mikhail Sokolov", "role": "Editorial Board",
                   "affiliation": "EUSP", "tribe": "sociology of academia"},
                  {"name": "Ilya Utekhin", "role": "Editorial Board",
                   "affiliation": "EUSP", "tribe": "anthropology, АнтроФорум №60 co-author"},
                  {"name": "Olga Stolyarova", "role": "Editorial Board",
                   "affiliation": "Institute of Philosophy RAS"},
                  {"name": "Vladimir Mau", "role": "Editorial Board",
                   "affiliation": "E.T. Gaidar Institute, Moscow"},
                  {"name": "Dmitry Michel", "role": "Editorial Board",
                   "affiliation": "INION RAS, Moscow"},
                  {"name": "Jeremy Morris", "role": "Editorial Board",
                   "affiliation": "Aarhus University, Denmark"},
                  {"name": "Ellan Spero", "role": "Editorial Board",
                   "affiliation": "MIT, Cambridge USA"},
                  {"name": "Alexey Titkov", "role": "Editorial Board",
                   "affiliation": "Univ of Manchester, UK"},
                  {"name": "Isak Frumin", "role": "Editorial Board",
                   "affiliation": "Univ of Constance, Bremen, Germany"},
                  {"name": "Paul Higgs", "role": "Editorial Board",
                   "affiliation": "Univ College London, UK"},
                  {"name": "Lee Jaemin", "role": "Editorial Board",
                   "affiliation": "Chinese Univ of Hong Kong"},
                  {"name": "Ivan Chalakov", "role": "Editorial Board",
                   "affiliation": "Paisii Hilendarski Univ of Plovdiv"}],
                 quote="Per https://socofpower.ranepa.ru/jour/pages/view/EditorialC?locale=en_US"),
            fact("homepage", "review_model", "double-blind peer-reviewed",
                 quote="Quarterly double-blind peer-reviewed open-access"),
            fact("homepage", "apc_oa", {"open_access": True, "apc": None}),
            fact("homepage", "accepted_languages", ["ru", "en"]),
            claim("homepage", "aims_scope",
                  "Two main subfields: (1) concepts of social theory and philosophy focusing on relationships between power and society; (2) empirical research of the Russian and Post-Soviet social environment.",
                  status="official_claim", confidence="high"),
            claim("editorial_board", "editorial_board_publications.Smolkin",
                  ["2017 SSRN: «Practice of Care by Luigina Mortari as a Sociological Puzzle»",
                   "2017 Журнал исследований социальной политики: same Mortari paper",
                   "specialization: continental ethics-of-care + age sociology + social theory"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14"),
            claim("editorial_board", "editorial_board_publications.Filippov_extended",
                  ["1993 International Sociology: «A final look back at Soviet sociology» (16 cit)",
                   "2010 Russian Sociological Review: «Schmitt, Carl's Political Romanticism» (4 cit)",
                   "2010 Russian Sociological Review: «Politics in the Times of Nazi» (Schmitt 1933-36)",
                   "2013 Russian Sociological Review: GLOSSARIUM by Carl Schmitt (with Korinets, Filippov) — 583 CITATIONS — FILIPPOV'S MOST-CITED WORK",
                   "2013 Russian Sociological Review: «Legality and legitimacy» Schmitt translation (4 cit)",
                   "2013 Journal of Classical Sociology: «The other Hobbes people: An alternative reading of Hobbes» (9 cit)",
                   "2013: «Correspondence on Schmitt and the Political» (with Akhutin) (2 cit)",
                   "2017 Соц.обозр: «Sociology and the Problem of Order» (with Farkhatdinov) (2 cit)",
                   "2019 Государство Религия Церковь: «Waiting for a Miracle: Sociology of Replicants as Political Theology (Blade Runner 2049)» (3 cit)",
                   "2019 Соц.обозр: «Sociology of Max Weber in the 21st century» (with Farkhatdinov) (8 cit)",
                   "2020-2021 Russian Politics & Law / Russian Social Science Review (Taylor & Francis): «The Ineradicable Rationality of Modernity» — INTERNATIONAL T&F",
                   "2023 Russia in Global Affairs: «Values and Mobilization: Sterile Excitement» (6 cit) — Schmitt-direct",
                   "2023 Соц.обозр: «Political theology and international justice» (with Kildyushov) (2 cit) — IN HIS OWN JOURNAL",
                   "2025: translator Carl Schmitt «The Tyranny of Values»",
                   "specialization: Schmitt is core scholarly identity 15+ years; political theology; sociology of space; Weber reception"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14 — Filippov dominantly Schmitt 15+ years"),
            claim("editorial_board", "editorial_board_publications.Stolyarova",
                  ["IF RAN philosopher; full publication list UNKNOWN",
                   "Likely Phil of Sci specialization (per affiliation)"],
                  status="inference", confidence="medium"),
        ],
    ),

    # ---------------------- Tier A #5 — Артикульт --------------------------
    VenueDef(
        canonical_name="Artikult",
        aliases=["Артикульт"],
        issn="2227-6165",
        publisher="Russian State University for the Humanities (RGGU) Faculty of Art History",
        official_urls=[
            "https://articult.rsuh.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://articult.rsuh.ru/",
             "source_title": "Artikult main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "editorial_council_board", "source_url": "https://articult.rsuh.ru/the-editorial-council-and-the-editorial-board.php",
             "source_title": "Editorial council and editorial board page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("editorial_council_board", "editorial_board_signal",
                 {"editorial_board": [
                     {"name": "Vladimir Kolotaev", "role": "Editor-in-Chief",
                      "affiliation": "RGGU Faculty of Art History Dean"},
                     {"name": "Alexander Markov", "role": "Deputy Editor-in-Chief",
                      "affiliation": "RGGU — multi-venue bridge author (31 verified titles 2022-2026 across Соц.обозр + НЛО + Praxema + Артикульт)"},
                     {"name": "Sergey Shtein", "role": "Executive Editor",
                      "affiliation": "RGGU"},
                     {"name": "Elena Ulybina", "role": "Board member",
                      "affiliation": "RANEPA, Doctor of Psychology"},
                     {"name": "Tatiana Kozhokaru", "role": "Executive Secretary",
                      "affiliation": "RGGU"}
                  ],
                  "editorial_council": [
                     {"name": "Nikolai Khrenov", "role": "Council Chair",
                      "affiliation": "State Inst Art Studies"},
                     {"name": "Slavoj Žižek", "affiliation": "Inst Sociology + Phil Univ Ljubljana",
                      "tribe": "MAVRINSKY DIRECT"},
                     {"name": "Mikhail Yampolsky", "affiliation": "NYU Slavic Studies",
                      "tribe": "Foucault-Deleuze cinema theory"},
                     {"name": "Hans Ulrich Gumbrecht", "affiliation": "Stanford"},
                     {"name": "Vladimir Papernyi", "affiliation": "UC Oakland"},
                     {"name": "Galina Zvereva", "affiliation": "RGGU"},
                     {"name": "Igor Kondakov", "affiliation": "RGGU"},
                     {"name": "Oleg Krivtsun", "affiliation": "Russian Academy of Arts"},
                     {"name": "Viktor Miziano", "affiliation": "Художественный журнал ed-in-chief"},
                     {"name": "Anzhelika Artyukh", "affiliation": "SPbGU"},
                     {"name": "Vladimir Spiridonov", "affiliation": "RANEPA — CROSS-BOARD with Шаги/Steps"},
                     {"name": "Alexander Tkhostov", "affiliation": "MSU"}
                  ]},
                 quote="Per https://articult.rsuh.ru/the-editorial-council-and-the-editorial-board.php"),
            fact("homepage", "indexing_claims", ["РИНЦ", "Перечень ВАК (since 2022-11-01)"],
                 quote="ВАК-included from November 2022"),
        ],
    ),

    # ---------------------- Tier A #6 — Антропологический форум -----------
    VenueDef(
        canonical_name="Forum for Anthropology and Culture",
        aliases=["Антропологический форум"],
        issn=None,
        publisher="EUSP Anthropology Faculty + Peter the Great Museum of Anthropology and Ethnography (Kunstkamera) RAS",
        official_urls=[
            "https://anthropologie.kunstkamera.ru/",
            "https://anthropologie.eusp.org/journal",
        ],
        sources=[
            {"key": "kunstkamera_homepage", "source_url": "https://anthropologie.kunstkamera.ru/",
             "source_title": "AnthroForum main page (Kunstkamera)",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "eusp_journal_page", "source_url": "https://anthropologie.eusp.org/journal",
             "source_title": "AnthroForum journal page (EUSP)",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "issue_60_aggregator", "source_url": "https://shop.kunstkamera.ru/catalog/zhurnaly/antropologicheskiy_forum/antropologicheskiy_forum_60_2024/",
             "source_title": "AnthroForum №60 2024 «AI in Social and Humanitarian Sciences» — shop page",
             "source_type": "third_party_summary",
             "freshness_window_days": 90},
        ],
        claims=[
            fact("eusp_journal_page", "editorial_board_signal",
                 [{"name": "Albert Baiburin", "role": "General Editor",
                   "affiliation": "EUSP Anthropology Dept; Doctor of Sciences",
                   "tribe": "Soviet/post-Soviet cultural anthropology; Polity Press 2021"},
                  {"name": "Catriona Kelly", "role": "Co-editor",
                   "affiliation": "Trinity College Cambridge senior research fellow + Oxford honorary",
                   "tribe": "Russian cultural history; 5+ Oxford UP/Bloomsbury monographs"}],
                 quote="Per AnthroForum journal page editor pair"),
            fact("issue_60_aggregator", "recent_issue_signal",
                 [{"issue": "№60 2024", "theme": "Artificial Intelligence in Social and Humanitarian Sciences",
                   "forum_thread_co_authors": ["Albert Baiburin", "Yuri Berezkin",
                       "Andrei Gromov", "Natalia Kovaleva", "Kira Kovalenko",
                       "Evgenii Sokolov", "Anna Moskvitina (Siim)",
                       "Nadezhda Stanulevich", "Ilya Utekhin", "Ivan Shirobokov",
                       "ChatGPT 3.5 (sic)"]},
                  {"issue": "№62 2024", "theme": "People and Other Living Beings"},
                  {"issue": "Issue #21 2025", "forum": "Humans and Other Species — multi-author thread with Blanchette + 20+"}],
                 quote="Per shop.kunstkamera + EUSP news"),
            fact("kunstkamera_homepage", "accepted_languages", ["ru", "en"],
                 quote="Bilingual peer-reviewed"),
        ],
    ),

    # ---------------------- Tier A — Шаги/Steps ----------------------------
    VenueDef(
        canonical_name="Shagi/Steps",
        aliases=["Шаги/Steps"],
        issn=None,
        publisher="RANEPA School of Relevant Humanitarian Research (SHAGI IOS RANEPA)",
        official_urls=[
            "https://steps.ranepa.ru/jour/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://steps.ranepa.ru/jour/",
             "source_title": "Shagi/Steps main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "editorial_team", "source_url": "https://steps.ranepa.ru/jour/about/editorialTeam",
             "source_title": "Editorial team page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("editorial_team", "editorial_board_signal",
                 [{"name": "Sergey Neklyudov", "role": "Editor-in-Chief",
                   "affiliation": "RANEPA + RGGU; Doctor of Philology, Professor",
                   "tribe": "Folklore + intellectual history",
                   "orcid": "0000-0002-4165-4604"},
                  {"name": "Henryk Baran", "affiliation": "University at Albany, USA"},
                  {"name": "Elena Vasina", "affiliation": "Univ of São Paulo, Brazil"},
                  {"name": "Nikolay Vakhtin", "affiliation": "EUSP",
                   "tribe": "linguistic anthropology"},
                  {"name": "Lyudmila Ermakova", "affiliation": "Kobe Univ of Foreign Studies, Japan"},
                  {"name": "Andrey Zorin", "affiliation": "Oxford University + RANEPA",
                   "tribe": "intellectual history"},
                  {"name": "Sergey Ivanov", "affiliation": "Northwestern Univ, USA"},
                  {"name": "Catriona Kelly", "affiliation": "Oxford University",
                   "tribe": "CROSS-VENUE with АнтроФорум co-editor"},
                  {"name": "Andrey Kibrik", "affiliation": "Institute of Linguistics RAS"},
                  {"name": "Anna Korndorf", "affiliation": "State Institute for Art Studies"},
                  {"name": "Maxim Krongauz", "affiliation": "HSE"},
                  {"name": "Alexander Mayorov", "affiliation": "SPbU"},
                  {"name": "Vladimir Mau", "affiliation": "Gaidar Institute"},
                  {"name": "Andrey Moroz", "affiliation": "HSE"},
                  {"name": "Yuri Slezkine", "affiliation": "UC Berkeley"},
                  {"name": "Vladimir Spiridonov", "affiliation": "RANEPA",
                   "tribe": "CROSS-VENUE with Артикульт council"},
                  {"name": "Konstantin Uchitel", "affiliation": "EUSP"},
                  {"name": "Tatiana Chernigovskaya", "affiliation": "SPbU",
                   "tribe": "cognitive science classic"}],
                 quote="Per https://steps.ranepa.ru/jour/about/editorialTeam"),
            fact("homepage", "indexing_claims", ["Scopus (since 2019)", "РИНЦ", "ВАК"],
                 quote="Scopus-indexed since 2019"),
            claim("homepage", "aims_scope",
                  "Multidisciplinary peer-reviewed academic journal; discusses contemporary humanities knowledge; includes ancient culture, oriental studies, comparative linguistics, historical-cultural and cognitive research, sociolinguistics, theoretical folklore.",
                  status="official_claim", confidence="high"),
            fact("homepage", "issn", "2412-9410"),
            fact("homepage", "eissn", "2782-1765"),
            fact("homepage", "apc_oa",
                 {"open_access": True, "license": "Creative Commons Attribution 4.0"}),
            claim("editorial_team", "recent_issue_signal",
                  [{"issue": "Vol 12 №2 (2026)",
                    "sections": ["АРХАИЗАЦИЯ И МОДЕРНИЗАЦИЯ В МИРОВОЙ ЛИТЕРАТУРЕ (10 articles)",
                                 "ИНТЕРПРЕТАЦИЯ ТЕКСТА (6 articles)",
                                 "МАРШРУТЫ ФОЛЬКЛОРНЫХ МОТИВОВ (2)",
                                 "VARIA — INCL «NFT-арт: новые возможности для раскрытия созидательного потенциала агентности в сфере культуры» (Afanasyeva+Sorokin) — MAVRINSKY-ADJACENT",
                                 "РЕЦЕНЗИИ (3)"],
                    "total_articles": 21}],
                  status="external_claim", confidence="high",
                  quote="Vol 12 №2 (2026) ToC verified — NFT/agency/culture article in Varia"),
        ],
    ),

    # ---------------------- Tier A — Urban Studies and Practices -----------
    VenueDef(
        canonical_name="Urban Studies and Practices",
        aliases=["Городские исследования и практики"],
        issn=None,
        publisher="HSE Vysokovsky School of Urbanism",
        official_urls=[
            "https://usp.hse.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://usp.hse.ru/",
             "source_title": "Urban Studies and Practices main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "editorial_team", "source_url": "https://usp.hse.ru/about/editorialTeam",
             "source_title": "Editorial team page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("editorial_team", "editorial_board_signal",
                 [{"name": "Valery Anashvili", "role": "Editor-in-Chief",
                   "affiliation": "HSE Faculty of Humanities (also Logos ed-in-chief)",
                   "tribe": "CROSS-VENUE with Logos"},
                  {"name": "D.R. Kodzokova", "role": "Executive Secretary", "affiliation": "HSE"},
                  {"name": "A.A. Smirnov", "role": "Scientific Editor",
                   "affiliation": "Gaidar Institute Publishing chief — Anashvili publishing network"},
                  {"name": "V.N. Danilov", "role": "Scientific Editor",
                   "affiliation": "MSU phil-anthr; ALSO Logos editorial board",
                   "tribe": "CROSS-VENUE with Logos"},
                  {"name": "R.A. Dokhov", "role": "Scientific Editor",
                   "affiliation": "MSU geography"},
                  {"name": "A.A. Lavrik", "role": "Managing Editor", "affiliation": "HSE"}],
                 quote="Per https://usp.hse.ru/about/editorialTeam"),
            fact("editorial_team", "editorial_council_signal",
                 ["Aksenov K.E. (SPbU)", "Alterman R. (Technion Israel)", "Ass E.V. (MARSH)",
                  "Akhmedova E.A. (SamGTU)", "Belykh A.A. (RANEPA)", "Bishop P. (UCL)",
                  "Blinkin M.Y. (HSE)", "Brückner J. (UC USA)", "Vaitens A.G. (SPbGASU)",
                  "Vendina O.I. (Inst Geography RAS)", "Grigorichev K.V. (IrSU)",
                  "Zamyatin D.N. (HSE — cultural geography)", "Zaporozhets O.N. (Leibniz Inst Germany)",
                  "Zubarevich N.V. (HSE+MSU — economic geography)", "Ilyina I.N. (HSE)",
                  "Levin M.I. (HSE)", "Long Y. (Tsinghua China)", "Low S. (CUNY — urban anthropology)",
                  "Mityagin S.D.", "Mikhailenko E.K. (HSE)", "Moiseev Y.M. (MARKHI)",
                  "Nefedova T.G. (Inst Geography RAS)", "Pilyasov A.N. (HSE+MSU)",
                  "Puzanov A.S. (HSE)", "Revich B.A. (INP RAS)", "Savoskul M.S. (MSU)",
                  "Sivaev S.B. (HSE)", "Timms P. (Univ Leeds UK)"]),
        ],
    ),

    # ---------------------- Tier A — Studia Culturae ----------------------
    VenueDef(
        canonical_name="Studia Culturae",
        aliases=["Studia culturae"],
        issn="2225-3211",
        eissn="2310-1245",
        publisher="Институт Мира и исследования конфликтов (Autonomous NCO), SPb",
        official_urls=[
            "http://iculture.spb.ru",
            "https://iculture.spb.ru/",
        ],
        sources=[
            {"key": "spbu_pure_listing", "source_url": "https://pureportal.spbu.ru/ru/activities/studia-culturae-journal",
             "source_title": "SPbU Pure portal Studia Culturae listing",
             "source_type": "registry_card",
             "freshness_window_days": 365},
            {"key": "iculture_homepage", "source_url": "http://iculture.spb.ru",
             "source_title": "Studia Culturae main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180,
             "notes": "Full editor contact + founders + publisher + ISSNs"},
        ],
        claims=[
            fact("spbu_pure_listing", "editorial_board_signal",
                 [{"name": "Boris G. Sokolov", "role": "Editor-in-Chief",
                   "affiliation": "Head, Dept of Cultural Studies, Philosophy of Culture, and Aesthetics, Institute of Philosophy, SPbU; Doctor of Philosophical Sciences, Professor",
                   "tribe": "MAVRINSKY DIRECT — continental aesthetics + philosophy of culture"}]),
            fact("spbu_pure_listing", "indexing_claims", ["РИНЦ", "Ulrichsweb"]),
            fact("iculture_homepage", "issn", "2225-3211"),
            fact("iculture_homepage", "eissn", "2310-1245"),
            fact("iculture_homepage", "editor_contact",
                 {"editor": "Sokolov B.G.", "email": "b.g.sokolov@spbu.ru",
                  "phone": "(812) 328-94-21 ext 1849"}),
            fact("iculture_homepage", "founders",
                 ["Sokolov B.G.", "Maltseva Y.M.", "Morina L.P.", "Prokudin D.E."],
                 quote="All 4 founders SPb-based"),
            fact("iculture_homepage", "publisher",
                 {"name": "Институт Мира и исследования конфликтов (Autonomous NCO)",
                  "address": "197022, СПб, Каменноостровский пр., д. 67",
                  "email": "fond_conflict@mail.ru"}),
            claim("iculture_homepage", "registration",
                  "Сетевое издание зарегистрировано Роскомнадзором; ЭЛ № ФС 77-75585 от 19.04.2019",
                  status="official_fact", confidence="high"),
            claim("spbu_pure_listing", "aims_scope",
                  "Peer-reviewed scientific journal publishing theory and history of culture, philosophy of culture, aesthetics and philosophy of art; interdisciplinary humanities; cross-cultural studies; bridges Russian and international scholars.",
                  status="official_claim", confidence="high"),
            claim("spbu_pure_listing", "frequency", "4 issues/year",
                  status="external_claim", confidence="high"),
            claim("iculture_homepage", "published_corpus_signal",
                  ["2024: «Influence of Suprematism on XXI Century Fashion» (Melnik)",
                   "2024: «Transcendental Reflection as Constructor of Values and Possibility of AI-Axiologies» (Popov) — Mavrinsky-adjacent (AI + axiology)",
                   "2025: «Karabakh traditions on Eldar Hajiev's carpets» (Mir-Bagirzade)",
                   "2025: «Cinema of slowness» (Ivanova)",
                   "2025: «Inclusive practices in social and cultural museum space» (Nosenko-Stein)",
                   "2023: «Spronck V. Testing the Parameters of Music — John Cage» (Lipov)",
                   "2021: «CEREMONIAL PORTRAIT OF FRENCH KINGS: SEMIOTIZATION OF INSTITUTION OF POWER» (Vasileva) — Mavrinsky-direct (semiotics of power)"],
                  status="external_claim", confidence="high",
                  quote="Per Google Scholar search Studia Culturae 2020-2025"),
        ],
    ),

    # ---------------------- Tier A — NLO -----------------------------------
    VenueDef(
        canonical_name="Novoe Literaturnoe Obozrenie (NLO)",
        aliases=["НЛО", "Новое литературное обозрение", "New Literary Observer"],
        issn=None,
        publisher="Novoe Literaturnoe Obozrenie publishing house",
        official_urls=[
            "https://www.nlobooks.ru/magazines/novoe_literaturnoe_obozrenie/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://www.nlobooks.ru/magazines/novoe_literaturnoe_obozrenie/",
             "source_title": "NLO main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "issue_191", "source_url": "https://www.nlobooks.ru/magazines/novoe_literaturnoe_obozrenie/191_nlo_1_2025/",
             "source_title": "NLO 191 (1/2025) issue page",
             "source_type": "official_archive",
             "freshness_window_days": 365},
        ],
        claims=[
            fact("homepage", "editorial_board_signal",
                 [{"name": "Irina Prokhorova",
                   "role": "Editor-in-Chief",
                   "affiliation": "NLO publishing house founder (1992)",
                   "tribe": "philologist + cultural historian"}],
                 quote="Founder + ed-in-chief since 1992"),
            fact("issue_191", "recent_issue_signal",
                 [{"section": "КНИГА КАК СОБЫТИЕ (continental theory primary)",
                   "articles": ["Рясов «У врат рассказа»",
                                "Яценко «Чрезвычайное положение после Идиллии» — Agamben-direct (state of exception)",
                                "Погребняк «В ожидании цифры?» — digital culture theory",
                                "Горяинов «Гегель, смерть и закон» — continental ontology",
                                "Серебряков «Закон чтения, болезнь толкования, смерть литературы»"]},
                  {"section": "ИСКУССТВО И ВЕРНАКУЛЯРНАЯ КУЛЬТУРА (4 articles)"},
                  {"section": "МУЗЫКА И ТРАНСГРЕССИЯ В СОВЕТСКОМ КИНО (2)"},
                  {"section": "РОССИЙСКИЙ СЕВЕР (5 articles area studies)"},
                  {"section": "IN MEMORIAM С.Л. КОЗЛОВ (7 articles)"},
                  {"section": "С.Л. КОЗЛОВ: НАУКА И ПАМЯТЬ (2)"},
                  {"section": "ЗАПИСИ И ВЫПИСКИ (3 theoretical notes)"},
                  {"section": "ХРОНИКА СОВРЕМЕННОЙ ЛИТЕРАТУРЫ (4 reviews)"},
                  {"section": "БИБЛИОГРАФИЯ (3)"},
                  {"section": "НА ПОЛЯХ (1)"},
                  {"section": "ХРОНИКА НАУЧНОЙ ЖИЗНИ (2 conference reports)"}],
                 quote="Vol 191 (1/2025) verified — 38 articles across 11 sections; Yatsenko's Agamben-direct paper confirms continental tribe alive in 2025"),
            claim("homepage", "aims_scope",
                  "Theory and history of literature, criticism and bibliography. First independent humanities periodical in post-Soviet space.",
                  status="official_claim", confidence="high"),
            claim("issue_191", "mavrinsky_landing_section",
                  "КНИГА КАК СОБЫТИЕ — continental theory essays ~10-15 pages each, conceptual; primary Mavrinsky landing",
                  status="inference", confidence="high",
                  quote="Section composition analysis"),
        ],
    ),

    # ---------------------- Tier A — Khudozhestvenny Zhurnal ---------------
    VenueDef(
        canonical_name="Moscow Art Magazine (Khudozhestvenny Zhurnal)",
        aliases=["Художественный журнал", "ХЖ", "Moscow Art Magazine"],
        issn=None,
        publisher="Khudozhestvenny Zhurnal",
        official_urls=[
            "https://moscowartmagazine.com/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://moscowartmagazine.com/",
             "source_title": "Moscow Art Magazine main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "archive_2024", "source_url": "https://moscowartmagazine.com/archive/releases/2024",
             "source_title": "2024 releases archive page",
             "source_type": "official_archive",
             "freshness_window_days": 365},
        ],
        claims=[
            fact("homepage", "editorial_board_signal",
                 [{"name": "Viktor Miziano",
                   "role": "Editor-in-Chief (founder 1993)",
                   "affiliation": "Контемпорари art curator + theorist; HSE Design School",
                   "tribe": "curatorial theory + continental art theory; Venice Biennale Russian Pavilion curator 1995/2003/2005; Founder Manifesta Journal: Journal of Contemporary Curatorship; Kandinsky Prize laureate"}],
                 quote="Founder + ed-in-chief since 1993"),
            fact("archive_2024", "recent_issue_signal",
                 [{"issue": "№127 2024", "theme": "Искусство больших данных (Art of Big Data)",
                   "mavrinsky_match": "DIRECT — interface + big data"},
                  {"issue": "№126 2024", "theme": "Автофикшн (Autofiction)"},
                  {"issue": "№125 2024", "theme": "Непрямое высказывание (Indirect Statement)",
                   "mavrinsky_match": "DIRECT — Foucault-Deleuze indirect-discourse axis"},
                  {"issue": "№124 2024", "theme": "Производство пространства (Production of Space)",
                   "mavrinsky_match": "DIRECT — Lefebvre/continental"}],
                 quote="3 of 4 2024 themes are Mavrinsky-direct"),
            claim("homepage", "aims_scope",
                  "Contemporary art theory + curatorial theory; continental aesthetic-political register; 4 thematic issues per year",
                  status="external_claim", confidence="high"),
        ],
    ),

    # ---------------------- Tier A — JOURSSA -------------------------------
    VenueDef(
        canonical_name="Journal of Sociology and Social Anthropology",
        aliases=["ЖССА", "Журнал социологии и социальной антропологии"],
        issn=None,
        publisher="SI RAN — branch of FNISC RAS + SPbU",
        official_urls=[
            "https://www.jourssa.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://www.jourssa.ru/",
             "source_title": "ЖССА main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "editorial_team", "source_url": "https://www.jourssa.ru/index.php/jourssa/about/editorialTeam",
             "source_title": "ЖССА editorial team page (partial — full board not displayed)",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("editorial_team", "editorial_board_signal",
                 [{"name": "Vladimir Vyacheslavovich Kozlovskiy",
                   "role": "Editor-in-Chief",
                   "affiliation": "Doctor of Philosophy, Professor; SI RAN — branch of FNISC RAS + SPbU",
                   "tribe": "sociology, social philosophy"},
                  {"name": "Alexander Vladimirovich Tavrovskiy",
                   "role": "Executive Secretary",
                   "affiliation": "Assistant, SPbU"}],
                 quote="Per https://www.jourssa.ru/index.php/jourssa/about/editorialTeam; full board page not rendered"),
            fact("homepage", "indexing_claims",
                 ["RSCI", "RISC", "VAK list K1 White List"],
                 quote="Per FNISC listing"),
            claim("homepage", "frequency", "4 issues/year since 1998",
                  status="external_claim", confidence="high"),
            claim("homepage", "aims_scope",
                  "Communication field for Russian sociologists, social philosophers, political scientists, culturologists, anthropologists.",
                  status="official_claim", confidence="high"),
        ],
    ),

    # ---------------------- Tier B — Seance --------------------------------
    VenueDef(
        canonical_name="Seance (Film and Time)",
        aliases=["Сеанс"],
        issn=None,
        publisher="Seance independent magazine",
        official_urls=[
            "https://seance.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://seance.ru/",
             "source_title": "Seance main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
        ],
        claims=[
            fact("homepage", "editorial_board_signal",
                 [{"name": "Vasily Stepanov",
                   "role": "Editor-in-Chief (since 2020)",
                   "affiliation": "Seance journal, since 2004"}],
                 quote="Per AFISHA article: ed-in-chief since 2020"),
            claim("homepage", "aims_scope",
                  "Journal and website about time and cinema; scientific supplement on film theory and history; design-oriented; SPb-based.",
                  status="external_claim", confidence="high"),
            claim("homepage", "trust_compliance_profile",
                  {"peer_review_clarity": "low — magazine-not-journal format; scientific supplement uses editorial review"},
                  status="inference", confidence="medium"),
        ],
    ),

    # ---------------------- Tier A — Digital Scholar -----------------------
    VenueDef(
        canonical_name="The Digital Scholar: Philosopher's Lab",
        aliases=["Цифровой ученый: лаборатория философа", "Digital Scholar UNN"],
        issn=None,
        publisher="Lobachevsky State University of Nizhny Novgorod (UNN)",
        official_urls=[
            "https://digital-scholar.unn.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://digital-scholar.unn.ru/",
             "source_title": "Digital Scholar main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
        ],
        claims=[
            claim("homepage", "aims_scope",
                  "Open space of academic communications between philosophers, science studies scholars and researchers from neighboring fields. Publishes papers in philosophy and science studies in Russian and English.",
                  status="official_claim", confidence="high",
                  quote="Per digital-scholar.unn.ru about page"),
            claim("homepage", "frequency", "Quarterly",
                  status="external_claim", confidence="high"),
            claim("homepage", "accepted_languages", ["ru", "en"],
                  status="external_claim", confidence="high"),
            claim("homepage", "scope_topics",
                  ["ontology", "epistemology", "history of philosophy",
                   "philosophy of science", "logic",
                   "science and technology studies",
                   "cognitive studies", "ethics", "aesthetics"],
                  status="official_claim", confidence="high",
                  quote="Wide phil-tech/STS/epistemology scope — Mavrinsky-adjacent in phil-tech axis"),
        ],
    ),

    # ---------------------- Tier A — Praxema -------------------------------
    VenueDef(
        canonical_name="Praxema. Journal of Visual Semiotics",
        aliases=["Праксема", "ΠΡΑΞΗΜΑ", "Praxema"],
        issn="2312-7899",
        eissn="2408-9176",
        publisher="Tomsk State Pedagogical University",
        official_urls=[
            "https://praxema.tspu.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://praxema.tspu.ru/",
             "source_title": "Praxema main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "issue_2024_2", "source_url": "https://praxema.tspu.ru/archive?format=html&issue=2&year=2024",
             "source_title": "Praxema 2024 Issue 2 ToC",
             "source_type": "official_archive",
             "freshness_window_days": 365},
            {"key": "issue_2024_4", "source_url": "https://praxema.tspu.ru/archive.html?year=2024&issue=4",
             "source_title": "Praxema 2024 Issue 4 ToC",
             "source_type": "official_archive",
             "freshness_window_days": 365},
            {"key": "chelovek_board_inference", "source_url": "https://chelovek.iphras.ru/redkollegiya",
             "source_title": "Chelovek editorial board page (lists Aвanesov as Praxema chief editor)",
             "source_type": "third_party_summary",
             "freshness_window_days": 90,
             "notes": "Praxema /redkollegiya.html persistently 404; Aвanesov ed-in-chief confirmed via cross-listing on Человек editorial board"},
        ],
        claims=[
            fact("homepage", "indexing_claims",
                 ["Scopus", "РИНЦ", "Ulrich's Periodicals Directory", "SJR (Scimago Journal & Country Rank)"],
                 quote="Per Praxema main page: 'Журнал ΠΡΑΞΗΜΑ включён в международную базу данных Scopus / РИНЦ / Ulrich's / SJR'"),
            fact("homepage", "accepted_languages", ["ru", "en", "fr"],
                 quote="Языки журнала - русский, английский и французский"),
            fact("homepage", "frequency", "4 issues/year",
                 quote="Периодичность издания: 4 выпуска в год"),
            fact("homepage", "accepted_article_types",
                 ["научная статья", "перевод научной статьи", "эссе",
                  "интервью", "научный доклад", "рецензия",
                  "библиографический обзор", "отчет о научном мероприятии"],
                 quote="Жанры приема публикаций"),
            fact("homepage", "review_model", "rigorous peer review",
                 quote="Все присланные материалы проходят процедуру рецензирования"),
            claim("homepage", "aims_scope",
                  "Theoretical problems of contemporary visual semiotics; multidisciplinary field bringing together philosophy, cultural studies, sociology, political science, art history, religious studies, aesthetics, ethics, history, linguistics, ethnography.",
                  status="official_claim", confidence="high"),
            claim("homepage", "recent_issue_signal",
                  [{"issue": "2026 №4 CFP", "theme": "Тексты в современном образовании: гибридный генезис и гибридные формы",
                    "deadline_abstract": "1 May 2026", "deadline_full": "20 July 2026",
                    "limit_articles": "8-10 articles only"}],
                  status="official_claim", confidence="high",
                  quote="2026 №4 CFP announcement"),
            fact("chelovek_board_inference", "editorial_board_signal",
                 [{"name": "Сергей Сергеевич Аванесов / S.S. Avanesov",
                   "role": "Editor-in-Chief",
                   "affiliation": "Director Scientific-Educational Center 'Humanitarian Urbanism' at Yaroslav-the-Wise Novgorod State University; Doctor of Philosophy, Professor",
                   "tribe": "philosophical anthropology + philosophy of religion + axiology + religious studies",
                   "cross_venue": "ALSO Chelovek editorial board member"}],
                 quote="Aвanesov listed as Praxema chief editor on Chelovek editorial board page"),
            claim("issue_2024_2", "published_corpus_signal",
                  ["Битюцкая (cinema)", "Боброва (mental models + Peirce)",
                   "Volodenkov+Fedorchenko+Belov+Karlyavina (Russian political elite + video games — Metro Exodus)",
                   "Думнова (Japanese garden)", "Спешилова (city perception)",
                   "Горбулева+Мелик-Гайказян (student note semiotics)",
                   "Донских (language purification)",
                   "Лисанюк+Шеваренкова (argumentation visualisation)"],
                  status="external_claim", confidence="high",
                  quote="2024 Issue 2 ToC verified"),
            claim("issue_2024_4", "published_corpus_signal",
                  ["Абрамова (family visualisation)",
                   "Агатова+Ермолина (big data student communities)",
                   "Буденкова et al (Chinese blogosphere)",
                   "Вихман+Ромм (visual model of formalized education language)",
                   "Уалиханова+Чорух+Червонный (Phenomenon-Based Learning physics)",
                   "Шиповалова+Мартынова (boundary-object science museum — STS continental)",
                   "Суровцев (formal logic)",
                   "Кирякова+Семьян (Pavel Ulitin books visual features)"],
                  status="external_claim", confidence="high",
                  quote="2024 Issue 4 ToC verified — Shipovalova (Stasis Centre Director) STS paper confirms continental-STS path"),
        ],
    ),

    # ---------------------- Tier A — Chelovek ------------------------------
    VenueDef(
        canonical_name="Chelovek (Human)",
        aliases=["Человек", "Chelovek journal", "Human journal IF RAN"],
        issn=None,
        publisher="Institute of Philosophy RAS",
        official_urls=[
            "https://chelovek.iphras.ru/",
        ],
        sources=[
            {"key": "homepage", "source_url": "https://chelovek.iphras.ru/",
             "source_title": "Chelovek main page",
             "source_type": "official_homepage",
             "freshness_window_days": 180},
            {"key": "redkollegiya", "source_url": "https://chelovek.iphras.ru/redkollegiya",
             "source_title": "Chelovek editorial board page",
             "source_type": "official_contacts",
             "freshness_window_days": 60},
        ],
        claims=[
            fact("redkollegiya", "editorial_board_signal",
                 [{"name": "Афанасов Николай Борисович / N.B. Afanasov",
                   "role": "Editor-in-Chief",
                   "affiliation": "Институт философии РАН, кандидат философских наук, научный сотрудник"},
                  {"name": "Аванесов Сергей Сергеевич / S.S. Avanesov",
                   "role": "Editorial Board",
                   "affiliation": "Director NEC «Humanitarian Urbanism» Yaroslav-the-Wise Novgorod State Univ; Doctor of Philosophy",
                   "tribe": "philosophical anthropology + phil of religion + axiology",
                   "cross_venue": "ALSO Editor-in-Chief Praxema"},
                  {"name": "Артемьева Татьяна Владимировна",
                   "role": "Editorial Board",
                   "affiliation": "RGPU im. A.I. Herzen, Dept Theory and History of Culture",
                   "tribe": "history of ideas + intellectual communication + cross-cultural comparativism"},
                  {"name": "Гарбер Илья Евгеньевич",
                   "role": "Editorial Board",
                   "affiliation": "Independent researcher",
                   "tribe": "social psychology"},
                  {"name": "Дудчик Андрей Юрьевич",
                   "role": "Editorial Board",
                   "affiliation": "Deputy Director Research, Inst Philosophy NAS Belarus",
                   "tribe": "communication theory + national tradition"},
                  {"name": "Kenneth Robert Westphal",
                   "role": "Editorial Board",
                   "affiliation": "European Academy (Italy); PhD in Philosophy, Professor",
                   "tribe": "philosophical anthropology + history of philosophy"},
                  {"name": "Любжин Алексей Игоревич",
                   "role": "Editorial Board",
                   "affiliation": "MIPT MASKI lab; Doctor Philology",
                   "tribe": "classics + Russian school history"},
                  {"name": "Мартьянов Виктор Сергеевич",
                   "role": "Editorial Board",
                   "affiliation": "Director Institute of Philosophy and Law UrO RAS",
                   "tribe": "political philosophy + axiology"},
                  {"name": "Намли Елена",
                   "role": "Editorial Board",
                   "affiliation": "Uppsala University (Sweden), Theological Faculty",
                   "tribe": "theology"},
                  {"name": "Никольский Сергей Анатольевич",
                   "role": "Editorial Board",
                   "affiliation": "IF RAN, Chief Researcher",
                   "tribe": "phil of culture + phil anthropology + phil of literature"},
                  {"name": "Островская Злата Владимировна",
                   "role": "Executive Secretary"},
                  {"name": "Павлов Александр Владимирович / A.V. Pavlov",
                   "role": "Editorial Board",
                   "affiliation": "HSE Head School of Phil and Culturology; IF RAN Leading Researcher; Logos Chief Editor; Соц.обозр Board; RAS Cor Member 2025",
                   "tribe": "MAVRINSKY-DIRECT GATEKEEPER — Pavlov on Logos + Соц.обозр + Человек = TRIPLE-VENUE bridge"},
                  {"name": "Покровский Никита Евгеньевич",
                   "role": "Editorial Board",
                   "affiliation": "HSE Sociology Chair + IF Sociology RAS Chief Researcher",
                   "tribe": "sociology"},
                  {"name": "Ростова Наталья Николаевна",
                   "role": "Editorial Board",
                   "affiliation": "MSU Faculty of Philosophy Phil Anthropology",
                   "tribe": "philosophical anthropology + religion + culture + art"},
                  {"name": "Сердюкова Елена Владимировна",
                   "role": "Editorial Board",
                   "affiliation": "Director Institute of Phil and Socio-Political Sciences, South Federal Univ",
                   "tribe": "philosophy of personality"}],
                 quote="Per https://chelovek.iphras.ru/redkollegiya — full editorial board with 15+ members"),
            claim("homepage", "aims_scope",
                  "Humanities + technology + AI in social and humanitarian sciences; philosophical anthropology + sociology + culture. Vol 37 №3 2026 included 'AI as normative agent: Chinese philosophical-anthropological perspective' (Dryaeva+Kanaev).",
                  status="external_claim", confidence="high",
                  quote="Vol 37 №3 2026 ToC verified earlier"),
            fact("homepage", "indexing_claims", ["РИНЦ", "ВАК"],
                 quote="IF RAN venue"),
            claim("redkollegiya", "editorial_board_publications.Afanasov",
                  ["2025 Patria: «О государстве-цивилизации: между философией и политикой»",
                   "2025 Patria: «Время и место современного коллективизма» (2 cit)",
                   "Cand Phil + IF RAN scientific researcher",
                   "specialization: state, collectivism, philosophy+politics intersection (post-2022 Russian discourse)"],
                  status="external_claim", confidence="high",
                  quote="Google Scholar 2026-06-14"),
            claim("redkollegiya", "editorial_board_publications.Avanesov_cross_ref",
                  ["Editor-in-Chief Praxema (cross-venue bridge); Doctor of Philosophy",
                   "specialization: philosophical anthropology + philosophy of religion + axiology + religious studies",
                   "Director NEC «Humanitarian Urbanism» at Yaroslav-the-Wise Novgorod State Univ"],
                  status="external_claim", confidence="high",
                  quote="Avanesov is Praxema chief editor — confirmed via this Chelovek board listing"),
        ],
    ),

    # ---------------------- Tier A — Historiko-philosophical Yearbook ------
    VenueDef(
        canonical_name="Historiko-philosophical Yearbook",
        aliases=["Историко-философский ежегодник", "ИФЕ"],
        issn="0134-8655",
        eissn="2782-6538",
        publisher="Institute of Philosophy RAS",
        official_urls=[
            "https://ife.iphras.ru/",
            "https://iphras.ru/histph.htm",
        ],
        sources=[
            {"key": "iphras_listing", "source_url": "https://iphras.ru/histph.htm",
             "source_title": "IF RAN journal listing for ИФЕ",
             "source_type": "publisher_page",
             "freshness_window_days": 180,
             "notes": "Direct ife.iphras.ru ECONNREFUSED; iphras.ru/histph.htm alternative path works"},
        ],
        claims=[
            fact("iphras_listing", "editorial_board_signal",
                 [{"name": "A.A. Stolyarov", "role": "Editor-in-Chief",
                   "affiliation": "IF RAN Western Phil History Sector; Doctor of Philosophy, Senior Research Fellow"},
                  {"name": "O.I. Kusenko", "role": "Deputy Editor-in-Chief",
                   "affiliation": "Candidate of Philosophy, Senior Research Fellow"},
                  {"name": "A.T. Yunusov", "role": "Executive Secretary",
                   "affiliation": "Candidate of Philosophy, Research Fellow"},
                  {"name": "A.S. Pavlov", "role": "Scientific Editor",
                   "affiliation": "Candidate of Philosophy, Junior Research Fellow"},
                  {"name": "A.V. Simonyan", "role": "Editorial Director",
                   "affiliation": "Junior Research Fellow"},
                  {"name": "E.S. Marchukova", "role": "Editor",
                   "affiliation": "Candidate of Philosophy, Research Fellow"}],
                 quote="Per iphras.ru/histph.htm"),
            fact("iphras_listing", "indexing_claims",
                 ["Scopus", "ScimagoJR", "eLibrary.ru", "CyberLeninka", "Ulrichs"]),
            fact("iphras_listing", "apc_oa",
                 {"open_access": True, "license": "Creative Commons BY-NC 4.0", "apc": None}),
            claim("iphras_listing", "frequency", "Annual",
                  status="external_claim", confidence="high"),
            claim("iphras_listing", "aims_scope",
                  "Cutting-edge historical-philosophical research; covers ancient, medieval, Islamic, modern, contemporary philosophical traditions; theoretical-methodological articles; archival materials; annotated translations of philosophical classics.",
                  status="official_claim", confidence="high"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Output emission.
# ---------------------------------------------------------------------------

def emit(out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)

    venues_path = out_dir / "venues.jsonl"
    sources_path = out_dir / "sources.jsonl"
    claims_path = out_dir / "claims.jsonl"

    n_v = n_s = n_c = 0

    with venues_path.open("w", encoding="utf-8") as fv, \
         sources_path.open("w", encoding="utf-8") as fs, \
         claims_path.open("w", encoding="utf-8") as fc:
        for vdef in VENUES:
            venue, sources, claims = vdef.to_records()
            fv.write(json.dumps(venue, ensure_ascii=False) + "\n")
            n_v += 1
            for s in sources:
                fs.write(json.dumps(s, ensure_ascii=False) + "\n")
                n_s += 1
            for c in claims:
                fc.write(json.dumps(c, ensure_ascii=False) + "\n")
                n_c += 1

    readme = out_dir / "README.md"
    readme.write_text(
        f"# Mavrinsky-RU venue seed corpus\n\n"
        f"Auto-generated by `scripts/build_mavrinsky_ru_seed_corpus.py`.\n\n"
        f"- Venues: {n_v}\n"
        f"- Sources: {n_s}\n"
        f"- Claims: {n_c}\n\n"
        f"Provenance: derived from operator notes in\n"
        f"`benchmarks/_operator_notes/mavrinsky_venue_research/`.\n"
        f"Each source has a verifiable URL; each claim links to its source.\n\n"
        f"Ingest into a project storage root:\n\n"
        f"    kairoskopion import-venue-seed --corpus-dir {out_dir} --storage-root <path>\n",
        encoding="utf-8",
    )

    return {"venues": n_v, "sources": n_s, "claims": n_c}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=Path("private_inputs/venue_seeds/mavrinsky_ru_corpus"),
        help="Directory where venues.jsonl / sources.jsonl / claims.jsonl are written",
    )
    args = parser.parse_args()
    counts = emit(args.output)
    print(f"Wrote {counts['venues']} venues, {counts['sources']} sources, "
          f"{counts['claims']} claims to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
