# Validation Matrix CLI Smoke Test
# Runs existing CLI commands on synthetic fixture pairs.
# Output goes to .kairoskopion_validation_matrix/ (gitignored).
# Usage: powershell -File scripts/run_validation_matrix.ps1
#   or:  cd repo_root && powershell scripts/run_validation_matrix.ps1

$ErrorActionPreference = "Continue"

# Resolve repo root (works when run from repo root or from scripts/)
if ($PSScriptRoot) {
    $root = Split-Path -Parent $PSScriptRoot
} else {
    $root = (Get-Location).Path
}

# PS 5.1 Join-Path only takes 2 args — chain calls
$fixtures = Join-Path (Join-Path (Join-Path $root "tests") "fixtures") "validation_matrix"
$scenario = Join-Path $fixtures "scenario_generic.json"
$manuscripts = Join-Path $fixtures "manuscripts"
$venues = Join-Path $fixtures "venues"

$cases = @(
    @{ Name = "good_fit";        Ms = "english_theoretical_article.md";       Vn = "english_philosophy_venue_complete.md" },
    @{ Name = "language_block";   Ms = "english_theoretical_article.md";       Vn = "russian_only_humanities_venue.md" },
    @{ Name = "method_block";     Ms = "english_theoretical_article.md";       Vn = "empirical_social_science_venue.md" },
    @{ Name = "missing_evidence"; Ms = "english_theoretical_article.md";       Vn = "incomplete_unknown_venue.md" },
    @{ Name = "formal_limits";    Ms = "english_theoretical_article.md";       Vn = "formal_limits_venue.md" },
    @{ Name = "thin_citation";    Ms = "thin_citation_theoretical_article.md"; Vn = "english_philosophy_venue_complete.md" }
)

Write-Host "=== Validation Matrix CLI Smoke Test ===" -ForegroundColor Cyan
Write-Host "Fixtures: $fixtures"
Write-Host "Cases: $($cases.Count)"
Write-Host ""

$passed = 0
$failed = 0

foreach ($c in $cases) {
    $storageRoot = Join-Path (Join-Path $root ".kairoskopion_validation_matrix") $c.Name
    $msFile = Join-Path $manuscripts $c.Ms
    $vnFile = Join-Path $venues $c.Vn

    Write-Host "--- Case: $($c.Name) ---" -ForegroundColor Yellow
    Write-Host "  MS: $($c.Ms)"
    Write-Host "  VN: $($c.Vn)"

    $result = & kairoskopion --storage-root $storageRoot run-local `
        --manuscript $msFile `
        --venue-guidelines $vnFile `
        --scenario $scenario 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  PASS" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  FAIL (exit $LASTEXITCODE)" -ForegroundColor Red
        $result | ForEach-Object { Write-Host "    $_" }
        $failed++
    }
    Write-Host ""
}

Write-Host "=== Summary: $passed passed, $failed failed out of $($cases.Count) ===" -ForegroundColor Cyan
if ($failed -gt 0) { exit 1 }
