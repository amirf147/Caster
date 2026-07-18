@echo off
REM Explicitly hijack the import loop to use our local tracked 0.35 codebase
set PYTHONPATH=%USERPROFILE%\Documents\repos\dragonfly-v0.35

py -3.10 -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"