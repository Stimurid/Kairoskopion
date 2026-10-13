# HEAD-TRIMURTI source recovery from Codex ZIP; no SSH, deploy or external sending.
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$OutputEncoding=[Text.Encoding]::UTF8
$repoName='Stimurid/Kairoskopion'
$root='C:\projects\trimurti\_ops\cli-recovery-20261013'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$lock=New-Object Threading.Mutex($false,'Global\HEAD_TRIMURTI_RECOVERY_20261013')
if(-not $lock.WaitOne(0)){exit 0}
function Log([string]$s) {
 Add-Content -Path (Join-Path $root 'MASTER_LOG.md') -Value ("["+(Get-Date).ToUniversalTime().ToString('o')+"] "+$s) -Encoding UTF8
}
function Note([int]$n,[string]$s) {
 $file=Join-Path $root ("issue_"+$n+".md")
 $s | Set-Content -Encoding UTF8 $file
 & gh issue comment $n --repo $repoName --body-file $file *> (Join-Path $root ("issue_"+$n+".log"))
}
function AssertLast([string]$where) {
 if($LASTEXITCODE -ne 0){throw "$where exit $LASTEXITCODE"}
}
function SafeZip([string]$zip) {
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 $z=[IO.Compression.ZipFile]::OpenRead($zip)
 try {
  $sum=0
  foreach($entry in $z.Entries){
   $name=$entry.FullName.Replace('\','/')
   $sum+=$entry.Length
   if($name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:' -or $entry.Length -gt 10000000 -or $sum -gt 40000000) {
    throw "unsafe ZIP entry $name"
   }
  }
 } finally {$z.Dispose()}
}
function LocalTests([string]$wt,[string]$kind,[string]$dir) {
 $python=Get-Command python -ErrorAction SilentlyContinue
 if(!$python){return 'NOT_RUN_PYTHON_MISSING'}
 $tests=if($kind -eq 'HS016'){@('tests/test_deep_target_models.py','tests/test_kairon_provider_contract.py')}else{@('tests/test_publication_runner.py','tests/test_submission_gate.py')}
 $tests=@($tests | Where-Object {Test-Path (Join-Path $wt $_)})
 if(!$tests.Count){return 'NOT_RUN_TESTS_MISSING'}
 Push-Location $wt
 try{
  $env:PYTHONPATH=Join-Path $wt 'src'
  & $python.Source -m pytest @tests -q --basetemp (Join-Path $dir 'pytest_tmp') *> (Join-Path $dir 'TESTS.log')
  if($LASTEXITCODE -eq 0){return 'PASS'}else{return 'FAIL'}
 }finally{Pop-Location}
}
function Recover([string]$kind,[int]$issue,[string]$job,[string]$source,[string]$baseSha,[string]$bundle,[string]$branch) {
 $dir=Join-Path $root $kind
 New-Item -ItemType Directory -Force -Path $dir | Out-Null
 $receipt=Join-Path $dir 'FINAL_RESULT.md'
 if(Test-Path $receipt){
  $existing=Get-Content -Raw $receipt
  if($existing -match 'STATUS=(DRAFT_PR_PUBLISHED|PUSHED_NEEDS_PR)'){
   Log "$kind already published; skipping"
   return
  }
 }
 $status='STARTED';$commit='';$pr='';$test='NOT_RUN';$errorText='';$hash=''
 try{
  $zip="C:\AI\llm\aiye-executor\worktrees\$job\$bundle"
  if(!(Test-Path $zip)){throw 'source ZIP missing'}
  if(!(Test-Path (Join-Path $source '.git'))){throw 'source Git clone missing'}
  SafeZip $zip
  $hash=(Get-FileHash $zip -Algorithm SHA256).Hash
  $lines=@('SOURCE_JOB='+$job,'ZIP='+$zip,'SHA256='+$hash)
  $lines|Set-Content -Encoding UTF8 (Join-Path $dir 'SOURCE_RECEIPT.md')
  $stage=Join-Path $dir 'unzipped'
  New-Item -ItemType Directory -Force -Path $stage | Out-Null
  Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force
  & git -C $source cat-file -e ($baseSha+'^{commit}') 2>$null
  if($LASTEXITCODE -ne 0){
   & git -C $source fetch --no-tags origin $baseSha *> (Join-Path $dir 'FETCH.log')
   AssertLast 'fetch base'
  }
  $wt=Join-Path $dir 'worktree'
  if(!(Test-Path $wt)){
   & git -C $source worktree add -b $branch $wt $baseSha *> (Join-Path $dir 'WORKTREE.log')
   AssertLast 'worktree add'
  }
  if(@(& git -C $wt status --porcelain).Count -gt 0){throw 'worktree not clean before recovery'}
  if($kind -eq 'HS016'){
   $patch=Join-Path $stage 'HS016_INTEGRATION.patch'
   if(!(Test-Path $patch)){throw 'patch missing'}
   $headers=@(Get-Content $patch | Where-Object {$_ -match '^(---|\+\+\+) [ab]/'})
   if(!$headers.Count){throw 'patch has no file headers'}
   foreach($head in $headers){
    $p=$head.Substring(6)
    if($p -notmatch '^(src/kairoskopion/|tests/|docs/)'){throw "patch path forbidden: $p"}
   }
   & git -C $wt apply --check $patch *> (Join-Path $dir 'APPLY_CHECK.log')
   AssertLast 'git apply --check'
   & git -C $wt apply $patch *> (Join-Path $dir 'APPLY.log')
   AssertLast 'git apply'
  }else{
   $allow=@(
     'src/kairoskopion/kairon_provider/publication_runner.py',
     'tests/test_publication_runner.py',
     'scripts/run_publication_controls.py',
     'docs/operations/PUBLICATION_IMPORT_RUNNER.md',
     'docs/publication-import.schema.json'
   )
   foreach($rel in $allow){
    $from=Join-Path $stage ($rel.Replace('/','\'))
    if(!(Test-Path $from)){throw "bundle file missing: $rel"}
    $to=Join-Path $wt ($rel.Replace('/','\'))
    New-Item -ItemType Directory -Force -Path (Split-Path $to -Parent)|Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
   }
  }
  $changed=@(& git -C $wt status --porcelain)
  $changed|Set-Content -Encoding UTF8 (Join-Path $dir 'CHANGED_FILES.md')
  if(!$changed.Count){throw 'no source changes after extraction'}
  $test=LocalTests $wt $kind $dir
  Log "$kind local tests=$test"
  & git -C $wt add -A -- src tests docs scripts *> (Join-Path $dir 'STAGE.log')
  AssertLast 'git add'
  & git -C $wt diff --cached --check *> (Join-Path $dir 'DIFF_CHECK.log')
  AssertLast 'diff check'
  $files=@(& git -C $wt diff --cached --name-only)
  if(!($files | Where-Object {$_ -match '^src/'})){throw 'no staged source'}
  if(!($files | Where-Object {$_ -match '^tests/'})){throw 'no staged tests'}
  & git -C $wt commit -m ("wip(kairon): recover "+$kind+" existing CLI code bundle") *> (Join-Path $dir 'COMMIT.log')
  AssertLast 'git commit'
  $commit=(& git -C $wt rev-parse HEAD).Trim()
  & git -C $wt push origin ("HEAD:refs/heads/"+$branch) *> (Join-Path $dir 'PUSH.log')
  AssertLast 'git push'
  $status='PUSHED_NEEDS_PR'
  $title="WIP: $kind existing CLI source and tests recovered"
  $body="Issue #$issue. Recovered existing Codex result $job, ZIP SHA256 $hash, local targeted pytest=$test. Draft only. CI and integration acceptance are separate. No external submission."
  $pr=(& gh pr create --repo $repoName --base main --head $branch --draft --title $title --body $body 2>&1|Out-String).Trim()
  if($LASTEXITCODE -eq 0){$status='DRAFT_PR_PUBLISHED'}
 }catch{
  $errorText=$_.Exception.Message
  if($status -ne 'PUSHED_NEEDS_PR'){$status='BLOCKED_WITH_LOCAL_SOURCE'}
  Log "$kind blocked: $errorText"
 }finally{
  @("STATUS=$status","SOURCE_JOB=$job","ISSUE=$issue","COMMIT=$commit","DRAFT_PR=$pr","TESTS=$test","ERROR=$errorText","EVIDENCE=$dir") |
   Set-Content -Encoding UTF8 $receipt
  Log "$kind $status sha=$commit pr=$pr"
  try{Note $issue ("HEAD-TRIMURTI existing ZIP recovery: $status; job=$job; SHA256=$hash; Git SHA=$commit; draft PR=$pr; local tests=$test; blocker=$errorText; local audit=$dir. No P06/P07 or deep venue runtime acceptance claimed.")}catch{Log 'issue comment failed'}
 }
}
try {
 Log 'START recover existing Codex outputs'
 Recover 'HS016' 20 'jx-400cc79259c4' 'C:\projects\kairoskopion-hs016-codex' '2c9a8f46b391c1924258c0f28df682ddfcad1324' 'HS016_PATCH_BUNDLE.zip' 'fix/head-trimurti-hs016-recovery-20261013'
 Recover 'P06P07' 21 'jx-d34a15cf3431' 'C:\projects\kairoskopion-package-factory' 'b8e2e4b89bf248a5db5f8b9af63ea7d3e02d973e' 'publication-spine-source-bundle.zip' 'feat/head-trimurti-p06p07-recovery-20261013'
} finally {
 'FINISHED'|Set-Content -Encoding UTF8 (Join-Path $root 'TERMINAL.txt')
 Log 'FINISHED'
 $lock.ReleaseMutex()
 $lock.Dispose()
}
