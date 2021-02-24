CALL conda -V
IF %ERRORLEVEL% EQU 0 GOTO Env
CALL START /wait "" source/Miniconda_installers/Miniconda3-latest-Windows-x86_64.exe /S /D=%UserProfile%/miniconda3

:Env
set PATH=%PATH%;%UserProfile%/miniconda3;%UserProfile%/miniconda3/Scripts;%UserProfile%/miniconda3/Library/bin
CALL conda update conda -y

CALL conda deactivate
CALL conda remove --name labelme --all -y
CALL conda create --name=labelme python=3.6 -y
CALL conda activate labelme
CALL pip install -r source/requirements.txt
CALL python source/__main__.py --autosave

CALL conda deactivate
