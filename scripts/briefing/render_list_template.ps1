param(
    [Parameter(Mandatory = $true)]
    [string]$JobPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class EasyTravelWordRenderNativeMethods {
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@

$WdAlertsNone = 0
$WdExportFormatPdf = 17
$WdStatisticPages = 2

function Write-JsonExclusive {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )
    $json = $Value | ConvertTo-Json -Depth 8
    $encoding = New-Object Text.UTF8Encoding($false)
    $stream = New-Object IO.FileStream(
        $Path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None
    )
    try {
        $writer = New-Object IO.StreamWriter($stream, $encoding)
        try { $writer.Write($json) } finally { $writer.Dispose() }
    }
    finally {
        $stream.Dispose()
    }
}

function Write-OwnerRecord {
    param(
        [Parameter(Mandatory = $true)]$Word,
        [Parameter(Mandatory = $true)]$Job
    )
    [uint32]$processId = 0
    [void][EasyTravelWordRenderNativeMethods]::GetWindowThreadProcessId(
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
    $owner = [ordered]@{
        schema_version = 1
        ownership_nonce = [string]$Job.ownership_nonce
        pid = [int]$processId
        process_name = "WINWORD"
        start_time_utc_ticks = [int64]$process.StartTime.ToUniversalTime().Ticks
    }
    Write-JsonExclusive -Value $owner -Path ([string]$Job.word_pid_path)
}

$word = $null
$document = $null
$wordStarted = $false
try {
    $resolvedJob = [IO.Path]::GetFullPath($JobPath)
    if (-not [IO.File]::Exists($resolvedJob)) {
        throw "WORD_JOB_MISSING"
    }
    $job = Get-Content -LiteralPath $resolvedJob -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if (
        [int]$job.schema_version -ne 1 -or
        [string]$job.action -cne "render" -or
        [string]$job.ownership_nonce -notmatch '^[0-9a-f]{32}$'
    ) {
        throw "WORD_RENDER_JOB_UNSUPPORTED"
    }
    $inputDocx = [IO.Path]::GetFullPath([string]$job.input_docx)
    $outputPdf = [IO.Path]::GetFullPath([string]$job.output_pdf)
    if (
        -not [IO.File]::Exists($inputDocx) -or
        [IO.Path]::GetExtension($inputDocx).ToLowerInvariant() -ne ".docx" -or
        [IO.File]::Exists($outputPdf) -or
        $inputDocx -eq $outputPdf
    ) {
        throw "WORD_RENDER_PATH_INVALID"
    }
    $word = New-Object -ComObject Word.Application
    $wordStarted = $true
    $word.Visible = $false
    $word.DisplayAlerts = $WdAlertsNone
    Write-OwnerRecord -Word $word -Job $job
    $document = $word.Documents.Open($inputDocx, $false, $true)
    $document.Repaginate()
    $pageCount = [int]$document.ComputeStatistics($WdStatisticPages)
    if ($pageCount -ne 1) {
        throw "LIST_PAGE_COUNT_BLOCKED"
    }
    $document.ExportAsFixedFormat($outputPdf, $WdExportFormatPdf)
    if (-not [IO.File]::Exists($outputPdf)) {
        throw "LIST_PDF_NOT_CREATED"
    }
    $report = [ordered]@{
        schema_version = 1
        action = "render"
        word_version = [string]$word.Version
        computed_page_count = $pageCount
        output_bytes = [int64](Get-Item -LiteralPath $outputPdf).Length
    }
    Write-JsonExclusive -Value $report -Path ([string]$job.report_path)
}
catch {
    [Console]::Error.WriteLine("WORD_RENDER_ERROR")
    if (-not $wordStarted) {
        exit 21
    }
    exit 30
}
finally {
    if ($null -ne $document) {
        try { $document.Close($false) } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) } catch {}
    }
    if ($null -ne $word) {
        try { $word.Quit() } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) } catch {}
    }
}

exit 0
