@echo off
echo Running Kaldi from Dragonfly CLI (UIA Development Branch)

set currentpath=%~dp0

:: Force the global Python launcher to check your development folder first
set PYTHONPATH=%USERPROFILE%\Documents\repos\dragonfly-bpc-oss

TITLE Caster: Status Window
py -3.10 -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"

pause 1