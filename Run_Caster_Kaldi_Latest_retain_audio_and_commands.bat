@echo off
echo Running Kaldi from Dragonfly CLI (Retaining Audio and Commands)

set currentpath=%~dp0

:: Ensure output directory exists for audio recordings and metadata TSV
if not exist "%currentpath%saved_audio" mkdir "%currentpath%saved_audio"

:: Point Python to your local development Dragonfly and pyvda folders
set PYTHONPATH=%USERPROFILE%\Documents\repos\pyvda;%USERPROFILE%\Documents\repos\dragonfly

TITLE Caster: Status Window (Kaldi Latest - Retain Audio and Commands)
"%currentpath%.venv_latest\Scripts\python.exe" -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300, retain_dir=saved_audio"

pause 1
