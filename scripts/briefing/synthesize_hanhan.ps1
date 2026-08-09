#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$JobPath
)

$ErrorActionPreference = "Stop"

function Invoke-HanhanSynthesis {
    param([string]$ResolvedJobPath)

    $speaker = $null
    try {
        $job = Get-Content -LiteralPath $ResolvedJobPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if (
            [int]$job.schema_version -ne 1 -or
            [string]::IsNullOrWhiteSpace([string]$job.voice) -or
            $null -eq $job.segments -or
            @($job.segments).Count -eq 0
        ) {
            return 22
        }
        if (
            [int]$job.audio.sample_rate -ne 44100 -or
            [int]$job.audio.bits_per_sample -ne 16 -or
            [int]$job.audio.channels -ne 1
        ) {
            return 22
        }

        Add-Type -AssemblyName System.Speech
        $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $installedVoices = @(
            $speaker.GetInstalledVoices() |
                Where-Object { $_.Enabled } |
                ForEach-Object { $_.VoiceInfo.Name }
        )
        if ($installedVoices -cnotcontains [string]$job.voice) {
            return 21
        }

        $speaker.SelectVoice([string]$job.voice)
        $speaker.Rate = [int]$job.rate
        $format = New-Object `
            -TypeName System.Speech.AudioFormat.SpeechAudioFormatInfo `
            -ArgumentList 44100, `
                ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), `
                ([System.Speech.AudioFormat.AudioChannel]::Mono)

        foreach ($segment in @($job.segments)) {
            $segmentId = [string]$segment.segment_id
            $segmentText = [string]$segment.text
            $outputPath = [string]$segment.output_path
            if (
                [string]::IsNullOrWhiteSpace($segmentId) -or
                [string]::IsNullOrWhiteSpace($segmentText) -or
                [string]::IsNullOrWhiteSpace($outputPath) -or
                [System.IO.Path]::GetExtension($outputPath) -ne ".wav" -or
                (Test-Path -LiteralPath $outputPath) -or
                -not (Test-Path -LiteralPath (Split-Path -Parent $outputPath) -PathType Container)
            ) {
                return 22
            }
            $speaker.SetOutputToWaveFile($outputPath, $format)
            try {
                $speaker.Speak($segmentText)
            }
            finally {
                $speaker.SetOutputToNull()
            }
        }
        return 0
    }
    catch {
        return 23
    }
    finally {
        if ($null -ne $speaker) {
            $speaker.Dispose()
        }
    }
}

try {
    $resolvedJobPath = (Resolve-Path -LiteralPath $JobPath -ErrorAction Stop).Path
}
catch {
    [Console]::Error.WriteLine("HANHAN_JOB_INVALID")
    exit 22
}

$exitCode = Invoke-HanhanSynthesis -ResolvedJobPath $resolvedJobPath
switch ($exitCode) {
    0 { exit 0 }
    21 { [Console]::Error.WriteLine("LOCAL_TTS_UNAVAILABLE"); exit 21 }
    22 { [Console]::Error.WriteLine("HANHAN_JOB_INVALID"); exit 22 }
    default { [Console]::Error.WriteLine("HANHAN_SYNTHESIS_FAILED"); exit 23 }
}
