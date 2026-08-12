param(
    [Parameter(Mandatory = $true)]
    [string]$JobPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class EasyTravelWordNativeMethods {
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@

$ExpectedHeaderCells = "1:1,2:1,2:2,2:3,3:1,4:1,4:2"
$WdAlertsNone = 0
$WdFormatDocumentDefault = 16
$WdStatisticPages = 2
$WdYellow = 7

function Write-JsonExclusive {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $parent = [IO.Path]::GetDirectoryName($Path)
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [IO.Directory]::CreateDirectory($parent) | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 12
    $encoding = New-Object Text.UTF8Encoding($false)
    $stream = New-Object IO.FileStream(
        $Path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None
    )
    try {
        $writer = New-Object IO.StreamWriter($stream, $encoding)
        try {
            $writer.Write($json)
        }
        finally {
            $writer.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Get-WordOwnerRecord {
    param(
        [Parameter(Mandatory = $true)]$Word,
        [Parameter(Mandatory = $true)][string]$OwnershipNonce
    )
    [uint32]$processId = 0
    [void][EasyTravelWordNativeMethods]::GetWindowThreadProcessId(
        [IntPtr]$Word.Hwnd,
        [ref]$processId
    )
    if ($processId -le 0) {
        throw "WORD_PID_UNAVAILABLE"
    }
    $process = Get-Process -Id $processId -ErrorAction Stop
    if ($process.ProcessName -cne "WINWORD") {
        throw "WORD_PID_MISMATCH"
    }
    return [ordered]@{
        schema_version = 1
        ownership_nonce = $OwnershipNonce
        pid = [int]$processId
        process_name = "WINWORD"
        start_time_utc_ticks = [int64]$process.StartTime.ToUniversalTime().Ticks
    }
}

function Get-Cell {
    param(
        [Parameter(Mandatory = $true)]$Table,
        [Parameter(Mandatory = $true)][int]$Row,
        [Parameter(Mandatory = $true)][int]$Column
    )
    try {
        return $Table.Cell($Row, $Column)
    }
    catch {
        throw "LIST_CELL_UNAVAILABLE"
    }
}

function Get-CellText {
    param([Parameter(Mandatory = $true)]$Cell)
    return ([string]$Cell.Range.Text).TrimEnd([char]13, [char]7).Trim()
}

function Test-SquareGraphic {
    param(
        [Parameter(Mandatory = $true)][double]$Width,
        [Parameter(Mandatory = $true)][double]$Height
    )
    if ($Width -lt 10 -or $Height -lt 10) {
        return $false
    }
    $ratio = $Width / $Height
    return $ratio -ge 0.8 -and $ratio -le 1.2
}

function Get-HeaderQrCandidateCount {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)]$HeaderCell
    )
    $start = [int]$HeaderCell.Range.Start
    $end = [int]$HeaderCell.Range.End
    $count = 0
    foreach ($shape in $Document.InlineShapes) {
        $position = [int]$shape.Range.Start
        if (
            $position -ge $start -and
            $position -le $end -and
            (Test-SquareGraphic -Width $shape.Width -Height $shape.Height)
        ) {
            $count += 1
        }
    }
    foreach ($shape in $Document.Shapes) {
        $position = [int]$shape.Anchor.Start
        if (
            $position -ge $start -and
            $position -le $end -and
            (Test-SquareGraphic -Width $shape.Width -Height $shape.Height)
        ) {
            $count += 1
        }
    }
    return $count
}

function Get-ListInspection {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)]$AnchorChecks
    )
    $tableShapes = @()
    for ($index = 1; $index -le $Document.Tables.Count; $index += 1) {
        $table = $Document.Tables.Item($index)
        $tableShapes += [ordered]@{
            rows = [int]$table.Rows.Count
            columns = [int]$table.Columns.Count
        }
    }
    if ($Document.Tables.Count -lt 1) {
        throw "LIST_TABLES_MISSING"
    }
    $headerTable = $Document.Tables.Item(1)
    $headerCell = Get-Cell -Table $headerTable -Row 1 -Column 1
    $accessibleCells = @()
    for ($row = 1; $row -le 4; $row += 1) {
        for ($column = 1; $column -le 3; $column += 1) {
            try {
                [void]$headerTable.Cell($row, $column)
                $accessibleCells += ,@($row, $column)
            }
            catch {
                # A merged coordinate is intentionally inaccessible through Word COM.
            }
        }
    }
    $foundAnchors = @()
    foreach ($anchor in $AnchorChecks) {
        if ([int]$anchor.table -ne 1) {
            throw "LIST_ANCHOR_TABLE_UNSUPPORTED"
        }
        $text = Get-CellText (
            Get-Cell `
                -Table $headerTable `
                -Row ([int]$anchor.row) `
                -Column ([int]$anchor.column)
        )
        if ($text.Contains([string]$anchor.label)) {
            $foundAnchors += [string]$anchor.label
        }
    }
    $section = $Document.Sections.Item(1)
    $orientation = if ([int]$section.PageSetup.Orientation -eq 0) {
        "portrait"
    }
    else {
        "landscape"
    }
    return [ordered]@{
        table_shapes = $tableShapes
        anchor_labels = $foundAnchors
        list_header_accessible_cells = $accessibleCells
        list_header_paragraph_count = [int]$headerCell.Range.Paragraphs.Count
        header_qr_candidate_count = [int](
            Get-HeaderQrCandidateCount -Document $Document -HeaderCell $headerCell
        )
        section_count = [int]$Document.Sections.Count
        page_width_points = [Math]::Round(
            [double]$section.PageSetup.PageWidth,
            2
        )
        page_height_points = [Math]::Round(
            [double]$section.PageSetup.PageHeight,
            2
        )
        orientation = $orientation
    }
}

function Assert-BasicListContract {
    param(
        [Parameter(Mandatory = $true)]$Inspection,
        [Parameter(Mandatory = $true)]$RequiredAnchorLabels,
        [int]$RequiredDayCount = 0
    )
    if ($Inspection.table_shapes.Count -ne 4) {
        throw "LIST_TABLE_COUNT_CHANGED"
    }
    $shapeText = @($Inspection.table_shapes | ForEach-Object {
        "$($_.rows)x$($_.columns)"
    })
    if (
        $shapeText[0] -ne "4x3" -or
        $shapeText[1] -ne "3x6" -or
        $shapeText[3] -ne "1x3"
    ) {
        throw "LIST_TABLE_SHAPE_CHANGED"
    }
    $dailyRows = [int]$Inspection.table_shapes[2].rows
    if (
        [int]$Inspection.table_shapes[2].columns -ne 7 -or
        $dailyRows -lt 6 -or
        $dailyRows -gt 8
    ) {
        throw "LIST_DAILY_TABLE_SHAPE_CHANGED"
    }
    if ($RequiredDayCount -gt 0 -and $dailyRows -ne ($RequiredDayCount + 1)) {
        throw "LIST_DAY_COUNT_MISMATCH"
    }
    if (($Inspection.anchor_labels -join ",") -cne ($RequiredAnchorLabels -join ",")) {
        throw "LIST_ANCHORS_CHANGED"
    }
    $cellText = @($Inspection.list_header_accessible_cells | ForEach-Object {
        "$($_[0]):$($_[1])"
    }) -join ","
    if ($cellText -ne $ExpectedHeaderCells) {
        throw "LIST_MERGED_CELLS_CHANGED"
    }
    if ([int]$Inspection.list_header_paragraph_count -ne 4) {
        throw "LIST_HEADER_PARAGRAPHS_CHANGED"
    }
    if ([int]$Inspection.header_qr_candidate_count -lt 1) {
        throw "LIST_QR_MISSING"
    }
    if (
        [int]$Inspection.section_count -ne 1 -or
        $Inspection.orientation -cne "portrait" -or
        [Math]::Abs([double]$Inspection.page_width_points - 595.28) -gt 2 -or
        [Math]::Abs([double]$Inspection.page_height_points - 841.89) -gt 2
    ) {
        throw "LIST_PAGE_GEOMETRY_CHANGED"
    }
}

function Set-TokenHighlight {
    param(
        [Parameter(Mandatory = $true)]$Range,
        [string]$Token
    )
    if ([string]::IsNullOrEmpty($Token)) {
        return
    }
    $boundary = [int]$Range.End - 1
    $cursor = [int]$Range.Start
    $matches = 0
    while ($cursor -lt $boundary) {
        $search = $Range.Duplicate
        $search.SetRange($cursor, $boundary)
        $search.Find.ClearFormatting()
        $search.Find.Text = $Token
        $search.Find.Forward = $true
        $search.Find.Wrap = 0
        if (-not $search.Find.Execute()) {
            break
        }
        $search.HighlightColorIndex = $WdYellow
        $matches += 1
        $cursor = [int]$search.End
    }
    if ($matches -eq 0) {
        throw "LIST_HIGHLIGHT_TOKEN_MISSING"
    }
}

function Set-HeaderParagraph {
    param(
        [Parameter(Mandatory = $true)]$HeaderCell,
        [Parameter(Mandatory = $true)]$Patch
    )
    $number = [int]$Patch.paragraph
    if ($number -lt 1 -or $number -gt $HeaderCell.Range.Paragraphs.Count) {
        throw "LIST_HEADER_PARAGRAPH_MISSING"
    }
    $paragraph = $HeaderCell.Range.Paragraphs.Item($number)
    $paragraph.Range.Text = ([string]$Patch.text) + "`r"
    $paragraph = $HeaderCell.Range.Paragraphs.Item($number)
    Set-TokenHighlight -Range $paragraph.Range -Token ([string]$Patch.highlight_text)
}

function Set-ListCell {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)]$Patch
    )
    $tableNumber = [int]$Patch.table
    if ($tableNumber -lt 1 -or $tableNumber -gt $Document.Tables.Count) {
        throw "LIST_TABLE_MISSING"
    }
    $cell = Get-Cell `
        -Table $Document.Tables.Item($tableNumber) `
        -Row ([int]$Patch.row) `
        -Column ([int]$Patch.column)
    $cell.Range.Text = ([string]$Patch.text) + "`r`a"
    $cell = Get-Cell `
        -Table $Document.Tables.Item($tableNumber) `
        -Row ([int]$Patch.row) `
        -Column ([int]$Patch.column)
    Set-TokenHighlight -Range $cell.Range -Token ([string]$Patch.highlight_text)
}

function Set-DailyRowCount {
    param(
        [Parameter(Mandatory = $true)]$Table,
        [Parameter(Mandatory = $true)][int]$DayCount
    )
    $targetRows = $DayCount + 1
    while ($Table.Rows.Count -gt $targetRows) {
        $Table.Rows.Item($Table.Rows.Count).Delete()
    }
    while ($Table.Rows.Count -lt $targetRows) {
        [void]$Table.Rows.Add()
    }
}

function Invoke-Probe {
    param(
        [Parameter(Mandatory = $true)]$Job,
        [Parameter(Mandatory = $true)]$Word
    )
    $result = [ordered]@{
        schema_version = 1
        action = "probe"
        word_version = [string]$Word.Version
    }
    Write-JsonExclusive -Value $result -Path ([string]$Job.report_path)
}

function Invoke-Inspect {
    param(
        [Parameter(Mandatory = $true)]$Job,
        [Parameter(Mandatory = $true)]$Word
    )
    $template = [IO.Path]::GetFullPath([string]$Job.template_path)
    if (
        -not [IO.File]::Exists($template) -or
        [IO.Path]::GetExtension($template).ToLowerInvariant() -notin @(".doc", ".docx")
    ) {
        throw "LIST_TEMPLATE_MISSING"
    }
    if ($Job.anchor_checks.Count -ne 8) {
        throw "LIST_ANCHOR_PLAN_INVALID"
    }
    $coordinateSignature = @($Job.anchor_checks | ForEach-Object {
        "$($_.table):$($_.row):$($_.column)"
    }) -join ","
    if ($coordinateSignature -cne "1:1:1,1:1:1,1:2:1,1:2:2,1:2:3,1:3:1,1:4:1,1:4:2") {
        throw "LIST_ANCHOR_PLAN_INVALID"
    }
    $requiredLabels = @($Job.anchor_checks | ForEach-Object {
        [string]$_.label
    })
    $document = $null
    try {
        $document = $Word.Documents.Open($template, $false, $true)
        $inspection = Get-ListInspection `
            -Document $document `
            -AnchorChecks $Job.anchor_checks
        Assert-BasicListContract `
            -Inspection $inspection `
            -RequiredAnchorLabels $requiredLabels
        $result = [ordered]@{
            schema_version = 1
            action = "inspect"
            word_version = [string]$Word.Version
            inspection = $inspection
        }
        Write-JsonExclusive -Value $result -Path ([string]$Job.report_path)
    }
    finally {
        if ($null -ne $document) {
            try { $document.Close($false) } catch {}
            try {
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject(
                    $document
                )
            }
            catch {}
        }
    }
}

function Invoke-Patch {
    param(
        [Parameter(Mandatory = $true)]$Job,
        [Parameter(Mandatory = $true)]$Word
    )
    $template = [IO.Path]::GetFullPath([string]$Job.template_path)
    $workingCopy = [IO.Path]::GetFullPath([string]$Job.working_copy_path)
    $outputDocx = [IO.Path]::GetFullPath([string]$Job.output_docx)
    if (-not [IO.File]::Exists($template)) {
        throw "LIST_TEMPLATE_MISSING"
    }
    $suffix = [IO.Path]::GetExtension($template).ToLowerInvariant()
    if ($suffix -notin @(".doc", ".docx")) {
        throw "LIST_TEMPLATE_TYPE_UNSUPPORTED"
    }
    if (
        [IO.File]::Exists($workingCopy) -or
        [IO.File]::Exists($outputDocx) -or
        $template -eq $workingCopy -or
        $template -eq $outputDocx -or
        $workingCopy -eq $outputDocx
    ) {
        throw "LIST_OUTPUT_NOT_EXCLUSIVE"
    }
    if (
        [int]$Job.plan.schema_version -ne 1 -or
        [string]$Job.plan.generator_version -cne "list-word/1"
    ) {
        throw "LIST_PATCH_PLAN_UNSUPPORTED"
    }
    [IO.File]::Copy($template, $workingCopy, $false)
    $document = $null
    try {
        $document = $Word.Documents.Open($workingCopy, $false, $false)
        if ($Job.plan.anchor_checks.Count -ne 8) {
            throw "LIST_ANCHOR_PLAN_INVALID"
        }
        $coordinateSignature = @($Job.plan.anchor_checks | ForEach-Object {
            "$($_.table):$($_.row):$($_.column)"
        }) -join ","
        if ($coordinateSignature -cne "1:1:1,1:1:1,1:2:1,1:2:2,1:2:3,1:3:1,1:4:1,1:4:2") {
            throw "LIST_ANCHOR_PLAN_INVALID"
        }
        $requiredLabels = @($Job.plan.anchor_checks | ForEach-Object {
            [string]$_.label
        })
        if (@($requiredLabels | Where-Object {
            [string]::IsNullOrWhiteSpace($_)
        }).Count -gt 0) {
            throw "LIST_ANCHOR_PLAN_INVALID"
        }
        $sourceInspection = Get-ListInspection `
            -Document $document `
            -AnchorChecks $Job.plan.anchor_checks
        Assert-BasicListContract `
            -Inspection $sourceInspection `
            -RequiredAnchorLabels $requiredLabels
        $dayCount = [int]$Job.plan.target_day_count
        if ($dayCount -lt 5 -or $dayCount -gt 7) {
            throw "LIST_DAY_COUNT_UNSUPPORTED"
        }
        Set-DailyRowCount -Table $document.Tables.Item(3) -DayCount $dayCount
        $headerCell = Get-Cell -Table $document.Tables.Item(1) -Row 1 -Column 1
        foreach ($patch in $Job.plan.header_paragraphs) {
            Set-HeaderParagraph -HeaderCell $headerCell -Patch $patch
        }
        foreach ($patch in $Job.plan.cells) {
            Set-ListCell -Document $document -Patch $patch
        }
        $outputInspection = Get-ListInspection `
            -Document $document `
            -AnchorChecks $Job.plan.anchor_checks
        Assert-BasicListContract `
            -Inspection $outputInspection `
            -RequiredAnchorLabels $requiredLabels `
            -RequiredDayCount $dayCount
        $document.Repaginate()
        $pageCount = [int]$document.ComputeStatistics($WdStatisticPages)
        if ($pageCount -ne 1) {
            throw "LIST_PAGE_COUNT_BLOCKED"
        }
        $document.SaveAs2($outputDocx, $WdFormatDocumentDefault)
        if (-not [IO.File]::Exists($outputDocx)) {
            throw "LIST_DOCX_NOT_CREATED"
        }
        $report = [ordered]@{
            schema_version = 1
            action = "patch"
            word_version = [string]$Word.Version
            source_inspection = $sourceInspection
            output_inspection = $outputInspection
            computed_page_count = $pageCount
            output_bytes = [int64](Get-Item -LiteralPath $outputDocx).Length
        }
        Write-JsonExclusive -Value $report -Path ([string]$Job.report_path)
    }
    finally {
        if ($null -ne $document) {
            try { $document.Close($false) } catch {}
            try {
                [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject(
                    $document
                )
            }
            catch {}
        }
        if ([IO.File]::Exists($workingCopy)) {
            try { [IO.File]::Delete($workingCopy) } catch {}
        }
    }
}

$word = $null
$wordStarted = $false
try {
    $resolvedJob = [IO.Path]::GetFullPath($JobPath)
    if (-not [IO.File]::Exists($resolvedJob)) {
        throw "WORD_JOB_MISSING"
    }
    $job = Get-Content -LiteralPath $resolvedJob -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if ([int]$job.schema_version -ne 1) {
        throw "WORD_JOB_UNSUPPORTED"
    }
    if ([string]$job.ownership_nonce -notmatch '^[0-9a-f]{32}$') {
        throw "WORD_OWNERSHIP_NONCE_INVALID"
    }
    $word = New-Object -ComObject Word.Application
    $wordStarted = $true
    $word.Visible = $false
    $word.DisplayAlerts = $WdAlertsNone
    $owner = Get-WordOwnerRecord `
        -Word $word `
        -OwnershipNonce ([string]$job.ownership_nonce)
    Write-JsonExclusive -Value $owner -Path ([string]$job.word_pid_path)
    switch ([string]$job.action) {
        "probe" { Invoke-Probe -Job $job -Word $word }
        "inspect" { Invoke-Inspect -Job $job -Word $word }
        "patch" { Invoke-Patch -Job $job -Word $word }
        default { throw "WORD_JOB_ACTION_UNSUPPORTED" }
    }
}
catch {
    [Console]::Error.WriteLine("WORD_ADAPTER_ERROR")
    if (-not $wordStarted) {
        exit 21
    }
    exit 30
}
finally {
    if ($null -ne $word) {
        try { $word.Quit() } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) } catch {}
    }
}

exit 0
