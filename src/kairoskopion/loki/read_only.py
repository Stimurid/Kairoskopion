"""LOKI R1: read-only bridges to EXISTING Artikl/Kairon/source-authority types.

No network and no writes. A verified digest proves which locally acquired
bytes were read, not who published them or why any manuscript was rejected.
The caller selects official publisher hostnames after independent checking.
The source authority admission is scoped to *quoted formal policy*, never
editorial outcome, scientific authorship or a real publication decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from html import unescape
from pathlib import Path
import re
from urllib.parse import urlsplit

from kairoskopion.kairon_provider.models import (
    ArtiklArticleProjection, TargetWorldSnapshot,
)
from kairoskopion.schema import (
    SourceSnapshot, VenueClaim, VenueSource,
)
from kairoskopion.source_authority import SourceAuthorityClaim
from kairoskopion.enums import (
    AuthorityStrength, SourceAccessMode, SourceAuthorityScope,
)

from .domain import (
    EvidenceKind, GameHypothesis, GameModel, OutcomeEvidence, ProbeKind,
    ProbeRecord, Verification,
)
from .engine import assess_observation


_ALLOWED_EXTRACTION = frozenset({
    "extracted", "html_parsed", "parsed", "validated",
    "full_text_extracted", "readable",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SourceNotAdmitted(ValueError):
    """Required source authentication/read-depth/authority is not proven."""


def _normalized(value: str) -> str:
    return " ".join(unescape(value).split()).casefold()


class _PolicyTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


@dataclass(frozen=True, slots=True)
class PolicyAdmissionReceipt:
    """Byte-anchored quote and scoped source authority, not peer review proof."""

    source_id: str
    source_url: str
    sha256_digest: str
    claim_id: str
    venue_record_id: str
    quote: str
    declared_outcome: str
    scope: str = "FORMAL_REQUIREMENTS_ONLY"
    origin_verification: str = "LOCAL_BYTES_ANCHORED_ORIGIN_NOT_AUTHENTICATED"
    limitations: tuple[str, ...] = (
        "Bytes and quote matched; remote publisher provenance is not independently signed",
        "The observer classified quoted wording into a pre-registered outcome",
        "Cannot infer a journal's hidden editorial preferences or acceptance probability",
    )


def _read_pinned_source(
    source: SourceSnapshot, source_root: Path, official_hosts: frozenset[str],
    *, max_bytes: int = 2_000_000,
) -> tuple[str, str]:
    if not source.snapshot_id or not source.source_id or not source.raw_ref:
        raise SourceNotAdmitted("snapshot, source identity and raw_ref required")
    if not source.url or not source.content_hash or not source.retrieved_at:
        raise SourceNotAdmitted("source URL, timestamp and content digest required")
    if source.extraction_status not in _ALLOWED_EXTRACTION:
        raise SourceNotAdmitted("source has no qualified readable extraction")
    if not isinstance(source.content_hash, str) or not _SHA256.fullmatch(source.content_hash):
        raise SourceNotAdmitted("source content hash must be pinned sha256")
    parsed = urlsplit(source.url)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.port is not None
            or parsed.hostname not in official_hosts):
        raise SourceNotAdmitted("source URL is not on an exact approved publisher host")
    try:
        root = Path(source_root).resolve(strict=True)
        requested = Path(source.raw_ref)
        path = (requested if requested.is_absolute() else root / requested).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SourceNotAdmitted("pinned source file is absent or unreadable") from exc
    if not path.is_relative_to(root) or not path.is_file():
        raise SourceNotAdmitted("source raw_ref escapes approved read-only root")
    if path.stat().st_size > max_bytes:
        raise SourceNotAdmitted("source exceeds authorized bounded text read")
    raw = path.read_bytes()
    digest = sha256(raw).hexdigest()
    if digest != source.content_hash:
        raise SourceNotAdmitted("source has been altered since snapshot hash")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceNotAdmitted("source is not a declared readable UTF-8 extraction") from exc
    if source.content_type and "html" in source.content_type.casefold():
        parser = _PolicyTextExtractor()
        parser.feed(content)
        content = " ".join(parser.parts)
    content = _normalized(content)
    if not content:
        raise SourceNotAdmitted("source contains no readable policy text")
    return content, digest


def admit_official_policy_quote(
    source: SourceSnapshot,
    provenance: SourceAuthorityClaim,
    venue_source: VenueSource,
    venue_claim: VenueClaim,
    *,
    expected_target_id: str,
    source_root: Path,
    official_hosts: frozenset[str],
) -> PolicyAdmissionReceipt:
    """Strict join of existing source, authority, venue-source and venue-claim types.

    Caller may submit a bogus authority claim; it is still only provenance
    stated by the producing subsystem. Code independently checks bytes,
    allowed host, exact quote, IDs, and prohibited source scopes.
    """
    if not isinstance(official_hosts, frozenset) or not official_hosts:
        raise SourceNotAdmitted("explicit approved host set required")
    if (provenance.access_mode != SourceAccessMode.OFFICIAL_WEBPAGE.value
            or provenance.authority_scope != SourceAuthorityScope.FORMAL_REQUIREMENTS.value
            or provenance.authority_strength != AuthorityStrength.AUTHORITATIVE.value):
        raise SourceNotAdmitted("only explicit authoritative official formal rules are admitted")
    if (provenance.source_ref != source.snapshot_id
            or provenance.evidence_ref != source.snapshot_id
            or provenance.supported_entity_id != expected_target_id):
        raise SourceNotAdmitted("source authority declaration does not match pinned snapshot/target")
    if (venue_source.venue_record_id != expected_target_id
            or venue_source.source_url != source.url
            or venue_claim.venue_record_id != expected_target_id
            or venue_claim.venue_source_id != venue_source.venue_source_id):
        raise SourceNotAdmitted("cross-venue source attribution rejected")
    if not provenance.claim_key or venue_claim.claim_path != provenance.claim_key:
        raise SourceNotAdmitted("authority claim path mismatch")
    if not isinstance(provenance.claim_value, str) or not provenance.claim_value.strip():
        raise SourceNotAdmitted("prediction category is absent")
    if venue_claim.claim_value != provenance.claim_value:
        raise SourceNotAdmitted("source and venue claim disagree")
    quote = venue_claim.quote_or_summary
    if not isinstance(quote, str) or len(quote.strip()) < 25:
        raise SourceNotAdmitted("short or absent exact publisher-policy passage")
    content, digest = _read_pinned_source(
        source, Path(source_root), official_hosts
    )
    if _normalized(quote) not in content:
        raise SourceNotAdmitted("quoted passage not present in pinned source bytes")
    return PolicyAdmissionReceipt(
        source_id=source.snapshot_id,
        source_url=source.url,
        sha256_digest=digest,
        claim_id=provenance.claim_id,
        venue_record_id=expected_target_id,
        quote=quote,
        declared_outcome=provenance.claim_value,
    )


def admitted_probe_outcome(
    game: GameModel,
    probe: ProbeRecord,
    hypotheses: tuple[GameHypothesis, ...],
    receipt: PolicyAdmissionReceipt,
) -> tuple[OutcomeEvidence, dict[str, str]]:
    """Create only a formal-policy observation, never simulated reviewer feedback."""
    if probe.game_id != game.game_id or probe.kind != ProbeKind.PASSIVE_ANALYSIS:
        raise SourceNotAdmitted("policy source cannot justify active or cross-game probe")
    if any(h.game_id != game.game_id for h in hypotheses):
        raise SourceNotAdmitted("cross-game hypothesis")
    predicted = {v for _, v in probe.predictions}
    if receipt.declared_outcome not in predicted:
        raise SourceNotAdmitted("publisher quote category was not preregistered")
    if not receipt.source_id or not _SHA256.fullmatch(receipt.sha256_digest):
        raise SourceNotAdmitted("broken digest receipt")
    if receipt.source_id not in probe.source_refs:
        raise SourceNotAdmitted("probe did not pre-register this exact source snapshot")
    if receipt.venue_record_id not in game.scope_ref:
        raise SourceNotAdmitted("venue source not in the declared game scope")
    event_id = sha256((
        probe.fingerprint + receipt.sha256_digest + receipt.claim_id
    ).encode("utf-8")).hexdigest()
    evidence = OutcomeEvidence(
        evidence_id=f"loki:policy:{event_id[:24]}",
        game_id=game.game_id,
        probe_id=probe.probe_id,
        probe_fingerprint=probe.fingerprint,
        outcome=receipt.declared_outcome,
        kind=EvidenceKind.PUBLIC_SOURCE,
        # A copied local page, even with a correct SHA and hostname string,
        # is NOT independent proof that a publisher served these bytes.
        # Only a separate authenticated source-ingestion owner can upgrade it.
        verification=Verification.PARTIAL,
        source_ref=f"{receipt.source_id}@sha256:{receipt.sha256_digest}",
        source_revision=receipt.sha256_digest,
    )
    return evidence, assess_observation(probe, hypotheses, evidence)


def game_from_artikl_target(
    article: ArtiklArticleProjection,
    target: TargetWorldSnapshot,
    *,
    owner_objective_ids: tuple[str, ...],
    protected_field_ref: str,
    source_snapshot_refs: tuple[str, ...],
) -> GameModel:
    """Read-only Artikl-authority + Kairon provider revision adapter.

    An ArtiklStatePointer is still a producer assertion. A trusted ingestion
    gate must independently verify its state/version before REAL_SCIENCE_PASS.
    """
    pointer = article.artikl_state
    if (article.semantic_authority != "ARTIKL"
            or pointer.authority != "ARTIKL" or not pointer.state_id
            or not pointer.version):
        raise SourceNotAdmitted("requires a versioned Artikl article projection")
    if not target.snapshot_id or not target.target_id:
        raise SourceNotAdmitted("requires a pinned target-world identity")
    if not protected_field_ref:
        raise SourceNotAdmitted("field owner must provide protected residue pointer")
    return GameModel(
        game_id=f"loki:{pointer.state_id}:{pointer.version}:{target.snapshot_id}",
        scope_ref=f"{pointer.state_id}@{pointer.version} x {target.target_id}@{target.snapshot_id}",
        objective_ids=owner_objective_ids,
        protected_field_ref=protected_field_ref,
        explicit_rule_refs=source_snapshot_refs,
        source_revisions=(pointer.version, target.snapshot_id),
        unknowns=(
            "Source/Artikl writer authenticity requires independent owner-side readback",
            "Venue corpus is provider observation, not an editorial acceptance record",
        ),
    )
