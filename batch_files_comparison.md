# Caster Kaldi Batch Files Comparison

This document provides a terse comparison of the three speech-recognition batch scripts available in the Caster directory.

---

## 1. Run_Caster_Kaldi.bat
* **Path**: [Run_Caster_Kaldi.bat](file:///c:/Users/Amir/Documents/Caster/Run_Caster_Kaldi.bat)
* **Python Executable**: Global Python Launcher (`py -3.10`)
* **Virtual Environment**: **No** (uses system-wide site-packages)
* **Dragonfly Source**: Globally installed `dragonfly2==0.35.0` package from PyPI
* **Accessibility Backend**: IAccessible2 (`ia2.py` fallback only; fails on modern UWP/Windows Terminal windows)
* **Command Executed**:
  ```bat
  py -3.10 -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"
  ```

---

## 2. run_caster_kaldi_uia.bat
* **Path**: [run_caster_kaldi_uia.bat](file:///c:/Users/Amir/Documents/Caster/run_caster_kaldi_uia.bat)
* **Python Executable**: Global Python Launcher (`py -3.10`)
* **Virtual Environment**: **No** (runs in global Python context, but overrides `PYTHONPATH`)
* **Dragonfly Source**: Local BPC fork at `repos\dragonfly-bpc-oss` (checked out to UIA development branch `feat/windows-uia-accessibility`)
* **Accessibility Backend**: UI Automation (`uia.py` preferred; robust focus tracking across modern Windows apps/Terminal)
* **Command Executed**:
  ```bat
  set PYTHONPATH=%USERPROFILE%\Documents\repos\dragonfly-bpc-oss
  py -3.10 -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"
  ```

---

## 3. Run_Caster_Kaldi_Latest.bat
* **Path**: [Run_Caster_Kaldi_Latest.bat](file:///c:/Users/Amir/Documents/Caster/Run_Caster_Kaldi_Latest.bat)
* **Python Executable**: Local Virtual Environment Python (`.venv_latest\Scripts\python.exe`)
* **Virtual Environment**: **Yes** (`.venv_latest` directory inside Caster folder)
* **Dragonfly & Pyvda Source**: Local repos at `repos\pyvda` (stale COM pointer fix fork) and `repos\dragonfly`
* **Accessibility Backend**: IAccessible2 (`ia2.py` fallback only; UIA code is not present)
* **Command Executed**:
  ```bat
  set PYTHONPATH=%USERPROFILE%\Documents\repos\pyvda;%USERPROFILE%\Documents\repos\dragonfly
  "%currentpath%.venv_latest\Scripts\python.exe" -m dragonfly load _*.py --engine kaldi --no-recobs-messages --engine-options "model_dir=kaldi_model, vad_padding_end_ms=300"
  ```
