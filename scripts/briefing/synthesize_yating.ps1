#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$JobPath
)

$ErrorActionPreference = "Stop"

function Wait-WindowsRuntimeOperation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Operation,

        [Parameter(Mandatory = $true)]
        [Type]$ResultType
    )

    $asTask = @(
        [System.WindowsRuntimeSystemExtensions].GetMethods() |
            Where-Object {
                $_.Name -ceq "AsTask" -and
                $_.IsGenericMethod -and
                $_.GetGenericArguments().Count -eq 1 -and
                $_.GetParameters().Count -eq 1
            }
    )[0]
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

function Write-NewUtf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $file = $null
    $writer = $null
    try {
        $file = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $writer = New-Object System.IO.StreamWriter(
            $file,
            (New-Object System.Text.UTF8Encoding($false))
        )
        $file = $null
        $writer.Write($Content)
        $writer.Flush()
    }
    finally {
        if ($null -ne $writer) {
            $writer.Dispose()
        }
        if ($null -ne $file) {
            $file.Dispose()
        }
    }
}

function Invoke-YatingSynthesis {
    param([string]$ResolvedJobPath)

    $synthesizer = $null
    $speechStream = $null
    $inputStream = $null
    $outputStream = $null
    try {
        $job = Get-Content -LiteralPath $ResolvedJobPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if (
            [int]$job.schema_version -ne 1 -or
            [string]$job.engine -cne "windows-media-speech" -or
            [string]$job.voice -cne "Microsoft Yating" -or
            [string]$job.language -cne "zh-TW" -or
            [string]::IsNullOrWhiteSpace([string]$job.ssml) -or
            [string]::IsNullOrWhiteSpace([string]$job.output_wav) -or
            [string]::IsNullOrWhiteSpace([string]$job.output_bookmarks)
        ) {
            return 22
        }

        $outputWav = [System.IO.Path]::GetFullPath([string]$job.output_wav)
        $outputBookmarks = [System.IO.Path]::GetFullPath(
            [string]$job.output_bookmarks
        )
        if (
            [System.IO.Path]::GetExtension($outputWav) -cne ".wav" -or
            [System.IO.Path]::GetExtension($outputBookmarks) -cne ".json" -or
            $outputWav -ceq $outputBookmarks -or
            (Test-Path -LiteralPath $outputWav) -or
            (Test-Path -LiteralPath $outputBookmarks) -or
            -not (Test-Path -LiteralPath (
                [System.IO.Path]::GetDirectoryName($outputWav)
            ) -PathType Container) -or
            -not (Test-Path -LiteralPath (
                [System.IO.Path]::GetDirectoryName($outputBookmarks)
            ) -PathType Container)
        ) {
            return 22
        }

        Add-Type -AssemblyName System.Runtime.WindowsRuntime
        [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType=WindowsRuntime] | Out-Null
        [Windows.Media.SpeechSynthesis.SpeechSynthesisStream, Windows.Media.SpeechSynthesis, ContentType=WindowsRuntime] | Out-Null
        [Windows.Media.IMediaMarker, Windows.Media, ContentType=WindowsRuntime] | Out-Null

        $matchingVoices = @(
            [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
                Where-Object {
                    $_.DisplayName -ceq "Microsoft Yating" -and
                    $_.Language -ceq "zh-TW"
                }
        )
        if ($matchingVoices.Count -ne 1) {
            return 21
        }

        $synthesizer = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
        $synthesizer.Voice = $matchingVoices[0]
        $operation = $synthesizer.SynthesizeSsmlToStreamAsync([string]$job.ssml)
        $speechStream = Wait-WindowsRuntimeOperation `
            -Operation $operation `
            -ResultType ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
        if ($null -eq $speechStream -or [uint64]$speechStream.Size -eq 0) {
            return 23
        }

        $markerType = [Windows.Media.IMediaMarker, Windows.Media, ContentType=WindowsRuntime]
        $timeProperty = $markerType.GetProperty("Time")
        $typeProperty = $markerType.GetProperty("MediaMarkerType")
        $textProperty = $markerType.GetProperty("Text")
        $markers = @()
        foreach ($rawMarker in @($speechStream.Markers)) {
            $markerKind = [string]$typeProperty.GetValue($rawMarker)
            if ($markerKind -ceq "Speech:Bookmark") {
                $markerTime = $timeProperty.GetValue($rawMarker)
                $markers += [ordered]@{
                    type = $markerKind
                    name = [string]$textProperty.GetValue($rawMarker)
                    time_ticks = [long]$markerTime.Ticks
                }
            }
        }

        $inputStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead(
            $speechStream
        )
        $outputStream = [System.IO.File]::Open(
            $outputWav,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $inputStream.CopyTo($outputStream)
        $outputStream.Flush()
        if ($outputStream.Length -eq 0) {
            return 23
        }
        $outputStream.Dispose()
        $outputStream = $null

        $bookmarkPayload = [ordered]@{
            schema_version = 1
            voice = [string]$matchingVoices[0].DisplayName
            markers = $markers
        }
        Write-NewUtf8File `
            -Path $outputBookmarks `
            -Content ($bookmarkPayload | ConvertTo-Json -Depth 4 -Compress)
        return 0
    }
    catch {
        return 23
    }
    finally {
        if ($null -ne $outputStream) {
            $outputStream.Dispose()
        }
        if ($null -ne $inputStream) {
            $inputStream.Dispose()
        }
        if ($null -ne $speechStream) {
            $speechStream.Dispose()
        }
        if ($null -ne $synthesizer) {
            $synthesizer.Dispose()
        }
    }
}

try {
    $resolvedJobPath = (Resolve-Path -LiteralPath $JobPath -ErrorAction Stop).Path
}
catch {
    [Console]::Error.WriteLine("YATING_JOB_INVALID")
    exit 22
}

$exitCode = Invoke-YatingSynthesis -ResolvedJobPath $resolvedJobPath
switch ($exitCode) {
    0 { exit 0 }
    21 { [Console]::Error.WriteLine("LOCAL_TTS_UNAVAILABLE"); exit 21 }
    22 { [Console]::Error.WriteLine("YATING_JOB_INVALID"); exit 22 }
    default { [Console]::Error.WriteLine("YATING_SYNTHESIS_FAILED"); exit 23 }
}
