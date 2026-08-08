@echo off
echo Running Kaldi from Dragonfly CLI (Dragonfly Latest + Kaldi 3.1.0)

set currentpath=%~dp0

:: Point Python to your local development Dragonfly and pyvda folders
set PYTHONPATH=%USERPROFILE%\Documents\repos\pyvda;%USERPROFILE%\Documents\repos\dragonfly

TITLE Caster: Status Window (Dragonfly + Kaldi Latest)
"%currentpath%.venv_latest\Scripts\python.exe" -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"

pause 1
