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

function Get-DefaultAnchorChecks {
    $labels = @(
        ([string][char]0x5718 + [char]0x9AD4 + [char]0x7DE8 + [char]0x865F),
        ([string][char]0x5718 + [char]0x9AD4 + [char]0x540D + [char]0x7A31),
        ([string][char]0x51FA + [char]0x767C + [char]0x65E5 + [char]0x671F),
        ([string][char]0x96C6 + [char]0x5408 + [char]0x6642 + [char]0x9593),
        ([string][char]0x9818 + [char]0x968A + [char]0x59D3 + [char]0x540D),
        ([string][char]0x96C6 + [char]0x5408 + [char]0x5730 + [char]0x9EDE),
        ([string][char]0x8B58 + [char]0x5225 + [char]0x724C),
        ([string][char]0x6A5F + [char]0x5834 + [char]0x5C08 + [char]0x54E1)
    )
    $coordinates = @(
        @(1, 1, 1),
        @(1, 1, 1),
        @(1, 2, 1),
        @(1, 2, 2),
        @(1, 2, 3),
        @(1, 3, 1),
        @(1, 4, 1),
        @(1, 4, 2)
    )
    $checks = @()
    for ($index = 0; $index -lt $labels.Count; $index += 1) {
        $checks += [ordered]@{
            label = $labels[$index]
            table = $coordinates[$index][0]
            row = $coordinates[$index][1]
            column = $coordinates[$index][2]
        }
    }
    return $checks
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string]$Text)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
        return ([BitConverter]::ToString(
            $sha.ComputeHash($bytes)
        )).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-NormalizedPoint {
    param([Parameter(Mandatory = $true)][double]$Value)
    return [Math]::Round($Value, 2, [MidpointRounding]::AwayFromZero)
}

function Assert-ExactProperties {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string[]]$Expected
    )
    $actualText = @(
        $Value.PSObject.Properties.Name | Sort-Object
    ) -join ","
    $expectedText = @($Expected | Sort-Object) -join ","
    if ($actualText -cne $expectedText) {
        throw "WORD_JOB_SCHEMA_INVALID"
    }
}

function Assert-WordJobShape {
    param([Parameter(Mandatory = $true)]$Job)
    if ([int]$Job.schema_version -ne 2) {
        return
    }
    $common = @(
        "schema_version",
        "action",
        "ownership_nonce",
        "word_pid_path",
        "report_path"
    )
    switch ([string]$Job.action) {
        "inspect-v2" {
            Assert-ExactProperties -Value $Job -Expected (
                $common + @("sample_paths")
            )
            if ($Job.sample_paths.Count -ne 3) {
                throw "WORD_JOB_SCHEMA_INVALID"
            }
            $resolvedSamples = @(
                $Job.sample_paths | ForEach-Object {
                    [IO.Path]::GetFullPath([string]$_)
                }
            )
            if (@($resolvedSamples | Select-Object -Unique).Count -ne 3) {
                throw "WORD_JOB_SCHEMA_INVALID"
            }
        }
        "calibrate" {
            Assert-ExactProperties -Value $Job -Expected (
                $common +
                @("source_path", "working_copy_path", "output_docx")
            )
        }
        default { throw "WORD_JOB_SCHEMA_INVALID" }
    }
    $jobDirectory = [IO.Path]::GetDirectoryName(
        [IO.Path]::GetFullPath($JobPath)
    )
    foreach ($localOutput in @(
        [string]$Job.word_pid_path,
        [string]$Job.report_path
    )) {
        $outputDirectory = [IO.Path]::GetDirectoryName(
            [IO.Path]::GetFullPath($localOutput)
        )
        if ($outputDirectory -cne $jobDirectory) {
            throw "WORD_JOB_SCHEMA_INVALID"
        }
    }
}

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

function Get-RangeFormatSignature {
    param([Parameter(Mandatory = $true)]$Range)
    $styleName = ""
    try { $styleName = [string]$Range.Style.NameLocal } catch {}
    return @(
        $styleName,
        [string]$Range.Font.Name,
        [string]$Range.Font.NameFarEast,
        [string]$Range.Font.Size,
        [string]$Range.Font.Bold,
        [string]$Range.Font.Italic,
        [string]$Range.ParagraphFormat.Alignment,
        [string]$Range.ParagraphFormat.SpaceBefore,
        [string]$Range.ParagraphFormat.SpaceAfter,
        [string]$Range.ParagraphFormat.LineSpacing,
        [string]$Range.ParagraphFormat.LineSpacingRule
    ) -join "|"
}

function Get-ListInspectionV2 {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)]$AnchorChecks
    )
    $basic = Get-ListInspection -Document $Document -AnchorChecks $AnchorChecks
    $requiredLabels = @(
        $AnchorChecks | ForEach-Object { [string]$_.label }
    )
    Assert-BasicListContract -Inspection $basic -RequiredAnchorLabels $requiredLabels
    $section = $Document.Sections.Item(1)
    $columnWidths = @()
    $formatParts = @()
    $borderParts = @()
    for ($tableIndex = 1; $tableIndex -le 4; $tableIndex += 1) {
        $table = $Document.Tables.Item($tableIndex)
        $widths = @()
        for ($column = 1; $column -le $table.Columns.Count; $column += 1) {
            $widths += Get-NormalizedPoint -Value ([double]$table.Columns.Item($column).Width)
        }
        $columnWidths += ,$widths
        $range = if ($tableIndex -eq 3) {
            $table.Rows.Item([Math]::Min(2, $table.Rows.Count)).Range
        }
        else {
            $table.Rows.Item(1).Range
        }
        $formatParts += "table-$tableIndex|" + (
            Get-RangeFormatSignature -Range $range
        )
        $tableBorders = @()
        foreach ($border in $table.Borders) {
            $tableBorders += @(
                [string]$border.Type,
                [string]$border.LineStyle,
                [string]$border.LineWidth,
                [string]$border.Color
            ) -join ":"
        }
        $borderParts += "table-$tableIndex|" + ($tableBorders -join ",")
    }
    $dailyTable = $Document.Tables.Item(3)
    $dailyHeaderRange = $dailyTable.Rows.Item(1).Range
    $dailyBodyRange = $dailyTable.Rows.Item(
        [Math]::Min(2, $dailyTable.Rows.Count)
    ).Range
    $fontSize = [double]$dailyBodyRange.Font.Size
    if ($fontSize -le 0 -or $fontSize -gt 72) { $fontSize = 10.0 }
    $lineSpacing = [double]$dailyBodyRange.ParagraphFormat.LineSpacing
    if ($lineSpacing -le 0 -or $lineSpacing -gt 72) {
        $lineSpacing = $fontSize + 2.0
    }
    $spaceAfter = [double]$dailyBodyRange.ParagraphFormat.SpaceAfter
    if ($spaceAfter -lt 0 -or $spaceAfter -gt 72) { $spaceAfter = 0.0 }
    $topPadding = [Math]::Max(0.01, [double]$dailyTable.TopPadding)
    $bottomPadding = [Math]::Max(0.01, [double]$dailyTable.BottomPadding)
    $shapeGeometry = @()
    $shapeNumber = 0
    foreach ($shape in $Document.InlineShapes) {
        $shapeNumber += 1
        $shapeGeometry += ,@(
            "inline-$('{0:D3}' -f $shapeNumber)",
            0.0,
            0.0,
            (Get-NormalizedPoint -Value ([double]$shape.Width)),
            (Get-NormalizedPoint -Value ([double]$shape.Height))
        )
    }
    foreach ($shape in $Document.Shapes) {
        $shapeNumber += 1
        $shapeGeometry += ,@(
            "floating-$('{0:D3}' -f $shapeNumber)",
            (Get-NormalizedPoint -Value ([double]$shape.Left)),
            (Get-NormalizedPoint -Value ([double]$shape.Top)),
            (Get-NormalizedPoint -Value ([double]$shape.Width)),
            (Get-NormalizedPoint -Value ([double]$shape.Height))
        )
    }
    $formatText = $formatParts -join [Environment]::NewLine
    return [ordered]@{
        schema_version = 2
        day_count = [int]$dailyTable.Rows.Count - 1
        table_shapes = $basic.table_shapes
        anchor_labels = $basic.anchor_labels
        list_header_accessible_cells = $basic.list_header_accessible_cells
        list_header_paragraph_count = $basic.list_header_paragraph_count
        section_count = $basic.section_count
        page_width_points = $basic.page_width_points
        page_height_points = $basic.page_height_points
        orientation = $basic.orientation
        margins_points = @(
            (Get-NormalizedPoint -Value ([double]$section.PageSetup.TopMargin)),
            (Get-NormalizedPoint -Value ([double]$section.PageSetup.RightMargin)),
            (Get-NormalizedPoint -Value ([double]$section.PageSetup.BottomMargin)),
            (Get-NormalizedPoint -Value ([double]$section.PageSetup.LeftMargin))
        )
        header_distance_points = Get-NormalizedPoint -Value ([double]$section.PageSetup.HeaderDistance)
        footer_distance_points = Get-NormalizedPoint -Value ([double]$section.PageSetup.FooterDistance)
        table_column_widths_points = $columnWidths
        merged_cell_map = @(
            "table-1:accessible:$($basic.list_header_accessible_cells.Count)"
        )
        qr_shape_count = [int]$basic.header_qr_candidate_count
        shape_geometry_points = $shapeGeometry
        style_digest = Get-Sha256Text -Text $formatText
        font_digest = Get-Sha256Text -Text ("font|" + $formatText)
        paragraph_digest = Get-Sha256Text -Text ("paragraph|" + $formatText)
        border_digest = Get-Sha256Text -Text ($borderParts -join [Environment]::NewLine)
        shading_digest = Get-Sha256Text -Text (
            "header|" + [string]$dailyHeaderRange.Shading.BackgroundPatternColor +
            "|body|" + [string]$dailyBodyRange.Shading.BackgroundPatternColor
        )
        daily_header_digest = Get-Sha256Text -Text (
            Get-RangeFormatSignature -Range $dailyHeaderRange
        )
        daily_body_prototype_digest = Get-Sha256Text -Text (
            Get-RangeFormatSignature -Range $dailyBodyRange
        )
        dynamic_content_digest = Get-Sha256Text -Text ([string]$Document.Content.Text)
        adaptive_profiles = @(
            [ordered]@{
                name = "normal"
                body_font_points = Get-NormalizedPoint -Value $fontSize
                line_spacing_points = Get-NormalizedPoint -Value $lineSpacing
                paragraph_space_after_points = Get-NormalizedPoint -Value $spaceAfter
                cell_top_margin_points = Get-NormalizedPoint -Value $topPadding
                cell_bottom_margin_points = Get-NormalizedPoint -Value $bottomPadding
            },
            [ordered]@{
                name = "compact"
                body_font_points = Get-NormalizedPoint -Value ([Math]::Max(8.0, $fontSize - 1.0))
                line_spacing_points = Get-NormalizedPoint -Value ([Math]::Max(9.0, $lineSpacing - 1.5))
                paragraph_space_after_points = 0.0
                cell_top_margin_points = Get-NormalizedPoint -Value $topPadding
                cell_bottom_margin_points = Get-NormalizedPoint -Value $bottomPadding
            }
        )
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
        $dailyRows -lt 2
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
        $prototype = $Table.Rows.Item(2)
        $newRow = $Table.Rows.Add()
        $newRow.Range.FormattedText = $prototype.Range.FormattedText
    }
}

function Set-ListLayoutProfile {
    param(
        [Parameter(Mandatory = $true)]$DailyTable,
        [Parameter(Mandatory = $true)]$Profile
    )
    for ($row = 2; $row -le $DailyTable.Rows.Count; $row += 1) {
        $range = $DailyTable.Rows.Item($row).Range
        $range.Font.Size = [double]$Profile.body_font_points
        $range.ParagraphFormat.LineSpacing = [double]$Profile.line_spacing_points
        $range.ParagraphFormat.SpaceAfter = [double]$Profile.paragraph_space_after_points
    }
    $DailyTable.TopPadding = [double]$Profile.cell_top_margin_points
    $DailyTable.BottomPadding = [double]$Profile.cell_bottom_margin_points
}

function Add-ContinuationGroupHeader {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)][string]$GroupText
    )
    $header = $Document.Sections.Item(1).Headers.Item(1)
    $range = $header.Range.Duplicate
    $range.Collapse(0)
    if ($range.Start -gt 0) {
        $range.InsertAfter([string][char]13)
        $range.Collapse(0)
    }
    $range.InsertAfter("IF ")
    $range.Collapse(0)
    [void]$Document.Fields.Add($range, 33, "PAGE", $true)
    $range.Collapse(0)
    $range.InsertAfter(" > 1 " + [char]34 + $GroupText + [char]34 + " " + [char]34 + [char]34)
    $conditionRange = $header.Range.Paragraphs.Last.Range
    [void]$Document.Fields.Add($conditionRange, 7)
}

function Get-DayPageMap {
    param(
        [Parameter(Mandatory = $true)]$DailyTable,
        [Parameter(Mandatory = $true)][int]$DayCount
    )
    $items = @()
    for ($day = 1; $day -le $DayCount; $day += 1) {
        $range = $DailyTable.Rows.Item($day + 1).Range
        $startRange = $range.Duplicate
        $startRange.Collapse(1)
        $startPage = [int]$startRange.Information(3)
        $endRange = $range.Duplicate
        $endRange.Collapse(0)
        $endPage = [int]$endRange.Information(3)
        if ($startPage -ne $endPage) {
            throw "LIST_DAY_ROW_TOO_TALL"
        }
        $items += [ordered]@{
            day_number = $day
            start_page = $startPage
            end_page = $endPage
        }
    }
    return $items
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

function Invoke-InspectV2 {
    param(
        [Parameter(Mandatory = $true)]$Job,
        [Parameter(Mandatory = $true)]$Word
    )
    if ($Job.sample_paths.Count -ne 3) {
        throw "LIST_CALIBRATION_SAMPLE_COUNT_INVALID"
    }
    $anchorChecks = Get-DefaultAnchorChecks
    $sampleReports = @()
    for ($index = 0; $index -lt 3; $index += 1) {
        $samplePath = [IO.Path]::GetFullPath(
            [string]$Job.sample_paths[$index]
        )
        if (
            -not [IO.File]::Exists($samplePath) -or
            [IO.Path]::GetExtension($samplePath).ToLowerInvariant() -notin @(".doc", ".docx")
        ) {
            throw "LIST_CALIBRATION_SAMPLE_INVALID"
        }
        $document = $null
        try {
            $document = $Word.Documents.Open($samplePath, $false, $true)
            $inspection = Get-ListInspectionV2 -Document $document -AnchorChecks $anchorChecks
            $sampleReports += [ordered]@{
                sample_id = "sample-$('{0:D3}' -f ($index + 1))"
                inspection = $inspection
            }
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
    Write-JsonExclusive -Value ([ordered]@{
        schema_version = 2
        action = "inspect-v2"
        word_version = [string]$Word.Version
        samples = $sampleReports
    }) -Path ([string]$Job.report_path)
}

function Invoke-Calibrate {
    param(
        [Parameter(Mandatory = $true)]$Job,
        [Parameter(Mandatory = $true)]$Word
    )
    $source = [IO.Path]::GetFullPath([string]$Job.source_path)
    $workingCopy = [IO.Path]::GetFullPath([string]$Job.working_copy_path)
    $outputDocx = [IO.Path]::GetFullPath([string]$Job.output_docx)
    if (
        -not [IO.File]::Exists($source) -or
        [IO.Path]::GetExtension($source).ToLowerInvariant() -notin @(".doc", ".docx") -or
        [IO.File]::Exists($workingCopy) -or
        [IO.File]::Exists($outputDocx)
    ) {
        throw "LIST_CALIBRATION_OUTPUT_NOT_EXCLUSIVE"
    }
    [IO.File]::Copy($source, $workingCopy, $false)
    $document = $null
    try {
        $document = $Word.Documents.Open($workingCopy, $false, $false)
        $anchorChecks = Get-DefaultAnchorChecks
        $headerCell = Get-Cell -Table $document.Tables.Item(1) -Row 1 -Column 1
        for ($paragraphNumber = 2; $paragraphNumber -le 4; $paragraphNumber += 1) {
            $paragraph = $headerCell.Range.Paragraphs.Item($paragraphNumber)
            $paragraph.Range.Text = [string][char]13
        }
        foreach ($coordinate in @(
            @(1, 2, 1), @(1, 2, 2), @(1, 2, 3),
            @(1, 3, 1), @(1, 4, 1), @(1, 4, 2)
        )) {
            $cell = Get-Cell -Table $document.Tables.Item($coordinate[0]) -Row $coordinate[1] -Column $coordinate[2]
            $originalText = Get-CellText -Cell $cell
            $labelBreak = $originalText.IndexOf(
                ([string][char]0xFF1A)
            )
            $labelText = if ($labelBreak -ge 0) {
                $originalText.Substring(0, $labelBreak + 1)
            }
            else {
                ""
            }
            $cell.Range.Text = $labelText + ([string][char]13) + [char]7
        }
        for ($row = 2; $row -le 3; $row += 1) {
            for ($column = 1; $column -le 6; $column += 1) {
                $document.Tables.Item(2).Cell($row, $column).Range.Text = ([string][char]13) + [char]7
            }
        }
        Set-DailyRowCount -Table $document.Tables.Item(3) -DayCount 1
        for ($column = 1; $column -le 7; $column += 1) {
            $document.Tables.Item(3).Cell(2, $column).Range.Text = ([string][char]13) + [char]7
        }
        for ($column = 2; $column -le 3; $column += 1) {
            $document.Tables.Item(4).Cell(1, $column).Range.Text = ([string][char]13) + [char]7
        }
        $inspection = Get-ListInspectionV2 -Document $document -AnchorChecks $anchorChecks
        $plainText = [string]$document.Content.Text
        $forbidden = @()
        if ($plainText -match '\b20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b') {
            $forbidden += "date"
        }
        if ($plainText -match '\b[A-Z]{2}\d{2,4}\b') {
            $forbidden += "flight"
        }
        if ($plainText -match '\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b') {
            $forbidden += "email"
        }
        if ($plainText -match '\b0\d{1,3}[- ]?\d{6,8}\b') {
            $forbidden += "phone"
        }
        $document.SaveAs2($outputDocx, $WdFormatDocumentDefault)
        if (-not [IO.File]::Exists($outputDocx)) {
            throw "LIST_MASTER_NOT_CREATED"
        }
        Write-JsonExclusive -Value ([ordered]@{
            schema_version = 2
            action = "calibrate"
            word_version = [string]$Word.Version
            master_inspection = $inspection
            forbidden_dynamic_token_types = $forbidden
            output_bytes = [int64](Get-Item -LiteralPath $outputDocx).Length
        }) -Path ([string]$Job.report_path)
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
        [int]$Job.plan.schema_version -ne 2 -or
        [string]$Job.plan.generator_version -cne "list-word/2"
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
            -RequiredAnchorLabels $requiredLabels `
            -RequiredDayCount 1
        $dayCount = [int]$Job.plan.target_day_count
        if ($dayCount -le 0) {
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
        $dailyTable = $document.Tables.Item(3)
        $dailyTable.Rows.Item(1).HeadingFormat = $true
        for ($row = 2; $row -le $dailyTable.Rows.Count; $row += 1) {
            $dailyTable.Rows.Item($row).AllowBreakAcrossPages = $false
        }
        $groupText = (
            [string]$Job.plan.header_paragraphs[1].text +
            " " +
            [string]$Job.plan.header_paragraphs[2].text
        )
        Add-ContinuationGroupHeader -Document $document -GroupText $groupText
        $outputInspection = Get-ListInspection `
            -Document $document `
            -AnchorChecks $Job.plan.anchor_checks
        Assert-BasicListContract `
            -Inspection $outputInspection `
            -RequiredAnchorLabels $requiredLabels `
            -RequiredDayCount $dayCount
        $selectedProfile = "normal"
        $normalProfile = $Job.plan.layout_profiles[0]
        Set-ListLayoutProfile -DailyTable $dailyTable -Profile $normalProfile
        $document.Repaginate()
        $pageCount = [int]$document.ComputeStatistics($WdStatisticPages)
        if ($pageCount -gt 1) {
            for ($profileIndex = 1; $profileIndex -lt $Job.plan.layout_profiles.Count; $profileIndex += 1) {
                $candidate = $Job.plan.layout_profiles[$profileIndex]
                Set-ListLayoutProfile -DailyTable $dailyTable -Profile $candidate
                $document.Repaginate()
                $candidatePages = [int]$document.ComputeStatistics($WdStatisticPages)
                if ($candidatePages -eq 1) {
                    $selectedProfile = [string]$candidate.name
                    $pageCount = $candidatePages
                    break
                }
            }
            if ($pageCount -gt 1) {
                Set-ListLayoutProfile -DailyTable $dailyTable -Profile $normalProfile
                $selectedProfile = "normal"
                $document.Repaginate()
                $pageCount = [int]$document.ComputeStatistics($WdStatisticPages)
            }
        }
        if ($pageCount -le 0) { throw "LIST_PAGE_COUNT_INVALID" }
        $dayPageMap = Get-DayPageMap -DailyTable $dailyTable -DayCount $dayCount
        $document.SaveAs2($outputDocx, $WdFormatDocumentDefault)
        if (-not [IO.File]::Exists($outputDocx)) {
            throw "LIST_DOCX_NOT_CREATED"
        }
        $report = [ordered]@{
            schema_version = 2
            action = "patch"
            word_version = [string]$Word.Version
            source_inspection = $sourceInspection
            output_inspection = $outputInspection
            selected_layout_profile = $selectedProfile
            computed_page_count = $pageCount
            day_page_map = $dayPageMap
            continuation_group_header = $true
            repeated_daily_header = $true
            qr_policy = "first_page_only"
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
    if ([int]$job.schema_version -notin @(1, 2)) {
        throw "WORD_JOB_UNSUPPORTED"
    }
    if ([string]$job.ownership_nonce -notmatch '^[0-9a-f]{32}$') {
        throw "WORD_OWNERSHIP_NONCE_INVALID"
    }
    Assert-WordJobShape -Job $job
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
        "inspect-v2" { Invoke-InspectV2 -Job $job -Word $word }
        "calibrate" { Invoke-Calibrate -Job $job -Word $word }
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
