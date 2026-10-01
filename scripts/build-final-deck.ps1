$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$deliverables = Join-Path (Split-Path -Parent $project) 'deliverables'
$previews = Join-Path $project 'artifacts\final-deck'
New-Item -ItemType Directory -Path $deliverables,$previews -Force | Out-Null
Add-Type -AssemblyName System.Drawing
function RGB([string]$hex) {
    return [Convert]::ToInt32($hex.Substring(0,2),16) + 256*[Convert]::ToInt32($hex.Substring(2,2),16) + 65536*[Convert]::ToInt32($hex.Substring(4,2),16)
}
function Rect($s,[double]$x,[double]$y,[double]$w,[double]$h,[string]$fill='FFFFFF',[string]$line='E0E6D9',[bool]$radius=$true) {
    $kind=1; if($radius){$kind=5}
    $shape=$s.Shapes.AddShape($kind,$x,$y,$w,$h)
    $shape.Fill.Solid(); $shape.Fill.ForeColor.RGB=RGB $fill
    $shape.Line.ForeColor.RGB=RGB $line; $shape.Line.Weight=0.8
    if($radius){$shape.Adjustments.Item(1)=0.08}
    return $shape
}
function Text($s,[string]$text,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size=16,[string]$color='223C2B',[bool]$bold=$false,[string]$font='Aptos') {
    $shape=$s.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $shape.TextFrame.MarginLeft=0; $shape.TextFrame.MarginRight=0
    $shape.TextFrame.MarginTop=0; $shape.TextFrame.MarginBottom=0
    $shape.TextFrame.AutoSize=0; $shape.TextFrame.WordWrap=-1
    $shape.TextFrame.TextRange.Text=$text
    $shape.TextFrame.TextRange.Font.Name=$font
    $shape.TextFrame.TextRange.Font.Size=[single]$size
    $shape.TextFrame.TextRange.Font.Color.RGB=RGB $color
    $shape.TextFrame.TextRange.Font.Bold=-[int]$bold
    $shape.TextFrame.TextRange.ParagraphFormat.SpaceAfter=0
    return $shape
}
function Note($s,$text) {
    foreach($n in $s.NotesPage.Shapes){if($n.Type -eq 14 -and $n.PlaceholderFormat.Type -eq 2){$n.TextFrame.TextRange.Text=$text;return}}
}
function Slide($p,[int]$number,[string]$section,[string]$title,[string]$subtitle='',[bool]$dark=$false) {
    $s=$p.Slides.Add($p.Slides.Count+1,12)
    $s.FollowMasterBackground=0
    $s.Background.Fill.Solid()
    $background='F5F7EF';$ink='203B2A';$muted='7B8F70';$line='DBE3D1'
    if($dark){$background='172F23';$ink='EFF4E6';$muted='9CB389';$line='3C5634'}
    $s.Background.Fill.ForeColor.RGB=RGB $background
    $null=Text $s $section.ToUpper() 48 29 800 20 9 $muted $true
    $null=Text $s $title 48 68 862 65 34 $ink $true
    if($subtitle){$null=Text $s $subtitle 49 136 855 40 13 $muted}
    $null=Rect $s 48 505 864 0.8 $line $line $false
    $null=Text $s 'MarginGuard / Genztech' 48 516 550 14 8 $muted
    $null=Text $s ('BUILD FAST WITH AI 2026     /     '+$number.ToString('00')) 686 516 235 14 8 $muted
    return $s
}
function Picture($s,$file,$x,$y,$w,$h) {
    $path=Join-Path $project ('artifacts\'+$file)
    $bitmap=[Drawing.Image]::FromFile($path)
    $ratio=$bitmap.Width/$bitmap.Height;$bitmap.Dispose()
    $pw=$w;$ph=$w/$ratio
    if($ph -gt $h){$ph=$h;$pw=$h*$ratio}
    $null=$s.Shapes.AddPicture($path,0,-1,$x+($w-$pw)/2,$y+($h-$ph)/2,$pw,$ph)
}
function Step($s,[string]$number,[string]$title,[string]$body,[double]$x,[double]$y,[double]$w=250,[bool]$dark=$false) {
    $fill='E9F0DF';$ink='355532';$muted='7D916F'
    if($dark){$fill='29432D';$ink='DCEACD';$muted='9CAE8C'}
    $null=Rect $s $x $y 28 28 $fill $fill
    $null=Text $s $number ($x+7) ($y+7) 22 18 10 $ink $true
    $null=Text $s $title ($x+42) ($y-1) ($w-42) 28 17 $ink $true
    $null=Text $s $body ($x+42) ($y+33) ($w-42) 66 12 $muted
}
$app=New-Object -ComObject PowerPoint.Application
$p=$null
try {
    $p=$app.Presentations.Add(0)
    $p.PageSetup.SlideWidth=960; $p.PageSetup.SlideHeight=540
    $s=Slide $p 1 'PS-04 / AI Decision Engine for Business Data' 'MarginGuard' '' $true
    $s.Shapes.Item(2).TextFrame.TextRange.Font.Size=62
    $null=Text $s "Know what changed.`rDecide what survives." 48 159 560 116 39 'E4EFDA' $false 'Georgia'
    $null=Text $s 'An evidence-backed decision product for retail operators.' 51 292 520 46 19 '9CB28B'
    $null=Rect $s 622 116 289 294 '203C28' '47653B'
    Step $s '01' 'Investigate' 'Findings linked to reconciled records.' 640 138 252 $true
    Step $s '02' 'Stress-test' 'See when the recommendation changes.' 640 237 252 $true
    Step $s '03' 'Approve' 'Review the exact data and assumptions.' 640 336 252 $true
    $null=Text $s 'GENZTECH' 51 396 480 21 11 'B9CE9C' $true
    $null=Text $s 'Baleeshwar Palavadi' 51 426 470 28 23 'EEF5E2' $true
    $null=Text $s 'Team leader & member  /  Working product submission' 52 462 560 19 11 '96AD83'
    Note $s 'Working project presentation. Selected problem: PS-04, AI Decision Engine for Business Data. Team Genztech. Baleeshwar Palavadi is the supplied team leader and member. LinkedIn https://www.linkedin.com/in/eeshwar369/. All business data shown is synthetic. The product runs locally; public publishing and a live Gemini call remain pending external account/key configuration. No guarantee of winning or realized business savings is claimed.'

    $s=Slide $p 2 'The problem' 'More sales can hide a weaker business.' 'The operator needs a decision they can defend, not another plausible explanation.'
    $null=Rect $s 49 202 411 234 'FFFFFF' 'DDE5D4'
    $null=Text $s 'SYNTHETIC STORE / AUGUST TO SEPTEMBER' 70 221 367 20 9 '91A27F' $true
    $null=Text $s '+4.3%' 71 264 173 58 43 '42774C' $true
    $null=Text $s '-18.1%' 252 264 190 58 43 'B27759' $true
    $null=Text $s 'Net revenue' 74 328 165 25 14 '80956F'
    $null=Text $s 'Contribution margin' 254 328 190 25 14 '80956F'
    $null=Text $s '616 order lines. Two months. Three exports.' 71 389 363 25 12 '97A688'
    Step $s '01' 'Which records are trustworthy?' 'Duplicate refunds and missing costs can change the answer.' 508 205 386
    Step $s '02' 'Which explanation is supported?' 'Trace numerical claims to the formula and source rows.' 508 300 386
    Step $s '03' 'Which action survives uncertainty?' 'A discount change can lose contribution if volume falls.' 508 395 386
    Note $s 'These figures come from the seeded sample generator, not customer results. August net revenue is INR 303490 and contribution is INR 163044. September revenue is INR 316499 and contribution is INR 133515. Rounded changes are +4.3% and -18.1%. Contribution excludes overhead and tax. User persona is a small direct-to-consumer retail founder/operator. Customer discovery and adoption have not been measured.'

    $s=Slide $p 3 'Working product' 'Three exports. One inspectable decision.' 'Import orders, refunds, and fulfilment costs. Keep the numbers and their evidence together.'
    $null=Rect $s 48 193 591 295 'FFFFFF' 'DDE5D4'
    Picture $s 'deck-overview.png' 56 200 574 280
    Step $s '01' 'Reconcile' 'Exact paise arithmetic and an accounting bridge.' 666 205 246
    Step $s '02' 'Investigate' 'A question becomes a saved, verifiable run.' 666 302 246
    Step $s '03' 'Decide' 'Scenario ranges and a versioned approval record.' 666 398 246
    Note $s 'This is an actual browser screenshot of the implemented application. Each source file has a SHA-256 fingerprint. Dataset versions are immutable. DuckDB bulk-loads validated records; refunds are aggregated before joins. Costs and discounts are line totals, unit price is multiplied by quantity, and refunds are attributed to the original order month.'

    $s=Slide $p 4 'Data quality as a product feature' 'Bad inputs do not get a confident answer.' 'A review gate is part of the workflow, with an issue history the operator can inspect.'
    Step $s '01' 'Quarantine duplicates' 'Identical repeated refunds are excluded and flagged.' 49 201 314
    Step $s '02' 'Block contradictory records' 'Missing costs, conflicting IDs, or excessive refunds require a corrected export.' 49 301 314
    Step $s '03' 'Version every correction' 'A reason, before/after values, and a new data hash.' 49 411 314
    $null=Rect $s 388 195 524 293 'FFFFFF' 'DDE5D4'
    Picture $s 'deck-quality.png' 396 202 508 279
    Note $s 'Demonstrate the quality challenge from Data sources. It creates a new synthetic dataset containing an identical repeated refund. Before acknowledgement, scenario and investigation endpoints return 409. The duplicate is quarantined, not counted twice. Conflicting keys or missing costs cannot be bypassed through acknowledgement. Test coverage includes multiple partial refunds without multiplication of costs, excessive recoveries, date conflicts, and orphan rows.'

    $s=Slide $p 5 'Bounded AI + numerical verification' 'AI plans. Accounting proves.' 'The model selects typed analyses. It never generates executable SQL or the financial values.' $true
    $stages=@(@('VALIDATE','Freeze the data version'),@('PLAN','Choose bounded tools'),@('INVESTIGATE','Test against the records'),@('VERIFY','Reconcile every number'))
    for($i=0;$i -lt 4;$i++){
        $x=48+$i*219
        $null=Rect $s $x 205 204 93 '25412B' '47633B'
        $null=Text $s $stages[$i][0] ($x+15) 222 177 24 15 'DDEBCD' $true
        $null=Text $s $stages[$i][1] ($x+15) 258 177 27 11 'A3B68F'
    }
    $null=Rect $s 48 332 427 115 '203A27' '405C35'
    $null=Text $s 'Challenge a false hypothesis.' 66 351 393 28 20 'D6E7C6' $true
    $null=Text $s '"Did discounts decrease?"  >  Contradicted.' 66 393 393 28 15 'AECA96'
    $null=Text $s 'Saved checkpoints survive interruptions.' 509 345 386 31 20 'DCEBCB' $true
    $null=Text $s 'Consent before Gemini. Numeric summaries only. Explicit fallback if the provider is unavailable.' 510 388 373 61 14 'A1B88A'
    $null=Text $s 'IMPLEMENTED INTEGRATION / LIVE PROVIDER CALL NOT YET VERIFIED / DEMO USES VERIFIED MODE' 50 471 861 20 8 '789769' $true
    Note $s 'LangGraph orchestrates four real stages with custom database checkpoints. Completed nodes are skipped when a run resumes against the original data version. A Gemini response is validated against an AnalysisPlan schema allowing at most five known metrics and a claimed direction. Financial outputs are computed deterministically. The provider success path is tested using a test double; an injected outage tests explicit fallback. No API key was configured during the recorded demo and no real model invocation is claimed. Deterministic keyword routing is not semantic AI. A crash before persisting the model-stage checkpoint can repeat a provider call.'

    $s=Slide $p 6 'Decision lab' 'A recommendation should be easy to challenge.' 'A small change in uncertainty can change the preferred action. The operator can see why.'
    $null=Text $s 'Baseline contribution' 51 207 350 25 12 '8B9C7A'
    $null=Text $s 'INR 1,33,515' 49 239 368 58 38 '3F6842' $true
    $null=Rect $s 49 318 351 64 'EAF2DF' 'D8E5C9'
    $null=Text $s 'Extra return cost: INR 0-4 / order' 65 329 324 20 12 '668554'
    $null=Text $s 'Prefer shipping cost reduction' 65 353 324 23 16 '3E653D' $true
    $null=Rect $s 49 396 351 64 'F3EEDA' 'E5DCC0'
    $null=Text $s 'Extra return cost: INR 0-20 / order' 65 408 324 20 12 '9E8A52'
    $null=Text $s 'Prefer keeping the current policy' 65 432 324 23 16 '8B7037' $true
    $null=Text $s 'Explicit bounds. Whole orders. No guaranteed savings.' 50 476 412 17 9 '91A17D'
    $null=Rect $s 439 190 473 301 'FFFFFF' 'DDE5D4'
    Picture $s 'deck-decision.png' 446 197 458 287
    Note $s 'Calculated from the sample: 336 current orders and INR 133515 baseline contribution. At INR5 shipping saving per order and extra return cost between INR0 and INR4, shipping contribution ranges from INR133851 to INR135195. Increase the maximum extra return cost to INR20 and downside becomes INR128475, below the current policy. The maximin rule then favors no change. A INR10 discount reduction has a continuous break-even demand loss of approximately 2.45% for this sample. The simulator is a finite-action sensitivity comparison, not causal inference, a sales forecast, or a calibrated probability. Implementation cost and whole-order rounding are included.'

    $s=Slide $p 7 'Human approval + durable history' 'Changed inputs require a new decision.' 'The approval belongs to a data version and a set of assumptions, not just to a document title.'
    $null=Rect $s 49 197 862 229 'FFFFFF' 'DDE5D4'
    Picture $s 'deck-stale.png' 58 204 844 214
    $null=Text $s 'REVIEW' 63 454 185 22 12 '678453' $true
    $null=Text $s 'APPROVE EXACT INPUTS' 258 454 235 22 12 '678453' $true
    $null=Text $s 'CORRECT A COST' 514 454 215 22 12 '678453' $true
    $null=Text $s 'OLD MEMO: STALE' 744 454 181 22 12 'AD8C50' $true
    Note $s 'Actual screenshot after approving a memo and correcting a cost. The new dataset clears the current scenario and marks previous memos stale. Server-side transactions recheck expected data and scenario hashes at approval, including races between browser sessions. Reverting to previous assumptions creates a new draft instead of restoring an old approval. Historical approver and approval time are retained. Export PDF/JSON includes status, scenario bounds, findings, and source fingerprints. Approval records the owner decision; separate approver roles are not implemented.'

    $s=Slide $p 8 'Architecture built for the working scope' 'A complete product, with a clear boundary.' 'One deployable service. Persistent state. Bounded AI. Reproducible analysis.'
    $blocks=@(@('INTERFACE','Next.js + TypeScript','Responsive workspace and evidence explorer'),@('APPLICATION','FastAPI + Pydantic','Sessions, CSRF, isolation, approval transactions'),@('ANALYSIS','DuckDB + Decimal','Validated ledger and exact scenario arithmetic'),@('WORKFLOW','LangGraph + Gemini','Typed planning and recoverable checkpoints'))
    for($i=0;$i -lt 4;$i++){
        $x=49+($i%2)*441;$y=197+[Math]::Floor($i/2)*124
        $null=Rect $s $x $y 422 105 'FFFFFF' 'DDE5D4'
        $null=Text $s $blocks[$i][0] ($x+17) ($y+13) 380 17 8 '91A17F' $true
        $null=Text $s $blocks[$i][1] ($x+17) ($y+37) 383 27 21 '3C6038' $true
        $null=Text $s $blocks[$i][2] ($x+17) ($y+76) 385 24 11 '7F936D'
    }
    $null=Text $s 'Neon PostgreSQL + Render Free   /   PDF exports   /   Audit trail   /   Docker + CI' 53 454 859 28 12 '658551' $true
    $null=Text $s 'Single instance by design. Public deployment, live AI verification, and independent security review remain.' 53 483 859 16 9 '94A181'
    Note $s 'The Next frontend is statically exported and served by FastAPI, so the production service does not require a Node runtime. PostgreSQL stores cloud state separately from Render; local development can use SQLite WAL. Accounts, snapshots, checkpoints, and approvals survive an app restart. The free blueprint has usage quotas and cold starts. One process owns the worker executor; two threads process bounded investigations, with at most twelve queued/running jobs globally and one per workspace. DuckDB is per-request and in-memory. Product controls include scrypt hashes, HTTP-only cookies, CSRF, origin checks, production CSP, upload limits, and rate limits. Horizontal scaling still needs a distributed queue and coordinated recovery. The Linux Docker image builds successfully; free Render deployment and live Gemini verification require account setup.'

    $s=Slide $p 9 'Measured verification' 'Evidence for the product itself.' 'Local checks exercise accounting correctness, failure handling, access boundaries, and the visible workflow.'
    $stats=@(@('54','tests / SQLite + Postgres'),@('3','browser journeys passed'),@('0 paise','reconciliation residual'))
    for($i=0;$i -lt 3;$i++){
        $x=49+$i*294
        $null=Rect $s $x 197 274 104 'FFFFFF' 'DDE5D4'
        $null=Text $s $stats[$i][0] ($x+19) 211 239 51 36 '537C42' $true
        $null=Text $s $stats[$i][1] ($x+20) 269 239 21 12 '8B9E77'
    }
    $null=Text $s 'PARSE + VALIDATE + ANALYZE / LOCAL MEDIAN OF THREE RUNS' 51 329 861 20 9 '8CA079' $true
    $rows=@(@('616 order lines + matching costs','103.3 ms'),@('10,000 order lines + matching costs','541.6 ms'),@('50,000 order lines + matching costs','2,225.1 ms'))
    for($i=0;$i -lt 3;$i++){
        $y=361+$i*35
        $null=Text $s $rows[$i][0] 53 $y 650 27 15 '728C5E'
        $null=Text $s $rows[$i][1] 763 $y 150 27 16 '3F6939' $true
    }
    $null=Text $s 'Windows 11 / Python 3.12.11 / synthetic timing fixture with zero refunds / excludes network and model calls' 53 479 858 18 8.5 '9BA98A'
    Note $s 'All reported numbers are observed local results, recorded in docs/VERIFICATION.md and raw artifacts. The same 54 pytest tests passed against SQLite and PostgreSQL 17. New tests cover reconnect persistence, rollback, concurrency, TLS enforcement, and parameter binding. Three Playwright journeys passed in real installed Chrome, including mobile at 390 pixels. The production frontend and TypeScript compiled. Backend tests cover exact money, partial refunds, duplicate quarantine, join/date validation, account isolation, CSRF, stale approvals, compare-and-swap correction, checkpoint resume, stream limits, mocked typed model success and provider outage fallback. Benchmark fixtures contain 616/10000/50000 order lines and equal costs, zero refund rows, three sequential runs each. All nine accounting bridges reconcile exactly. This is not deployed throughput, model latency, an SLA, a broad model-quality benchmark, or evidence of business savings.'

    $s=Slide $p 10 'Genztech / final submission' 'Decisions with receipts.' '' $true
    $null=Text $s 'Built and tested. Ready for a judge to challenge.' 50 151 852 50 29 'D6E7C5' $false 'Georgia'
    Step $s '01' 'Challenge the hypothesis.' 'Ask whether discounts decreased. Inspect the contradiction.' 51 239 400 $true
    Step $s '02' 'Change the assumptions.' 'Make shipping riskier and watch the decision change.' 51 345 400 $true
    $null=Rect $s 511 226 400 234 '223F29' '48663C'
    $null=Text $s 'TEAM LEADER & MEMBER' 532 247 352 22 9 '9AB686' $true
    $null=Text $s 'Baleeshwar Palavadi' 531 282 359 42 28 'EBF3DF' $true
    $null=Text $s 'Genztech' 533 337 356 29 21 'BED5A5'
    $link=Text $s 'linkedin.com/in/eeshwar369/' 533 391 356 26 14 'A3C58C'
    $link.ActionSettings.Item(1).Hyperlink.Address='https://www.linkedin.com/in/eeshwar369/'
    $null=Text $s 'PS-04 / AI Decision Engine for Business Data' 533 431 355 18 10 '7F9F6C'
    $repoLink=Text $s 'github.com/eeshwar369/MarginGuard' 53 483 858 20 11 'A3C58C'
    $repoLink.ActionSettings.Item(1).Hyperlink.Address='https://github.com/eeshwar369/MarginGuard'
    Note $s 'Final demonstration prompts: challenge a false discount hypothesis, inspect source evidence, increase return-cost uncertainty, approve a memo, correct a cost, and observe stale approval. The working product, reproducible source, local test evidence, deployment files, presentation, and narrated actual browser demo are prepared. The source is published at https://github.com/eeshwar369/MarginGuard. The deployed service and hosted demo URLs still require account access and verification. This deck contains exactly ten slides. Team identity and LinkedIn are user-provided.'

    $pptx=Join-Path $deliverables 'MarginGuard_Final_Project.pptx'
    $pdf=Join-Path $deliverables 'MarginGuard_Final_Project.pdf'
    $p.SaveAs($pptx,24)
    $p.SaveAs($pdf,32)
    $p.Export($previews,'PNG',1600,900)
    Write-Output "Created $($p.Slides.Count) slides: $pptx"
    Write-Output $pdf
} finally {
    if($p){$p.Close()}
    $app.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
