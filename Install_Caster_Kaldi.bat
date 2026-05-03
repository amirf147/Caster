@echo off
set currentpath=%~dp0
echo Installation path: %currentpath%
echo Using this python/pip:
py -3.10 -m pip -V

echo Installing Caster Dependencies
py -3.10 -m pip install -r "%currentpath%requirements.txt"
py -3.10 -m pip install dragonfly2[kaldi]

echo Remember: Manually install kaldi a model. 
echo See Caster kaldi install instructions on ReadTheDocs.

pause 1
