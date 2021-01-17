CALL conda -V
IF %ERRORLEVEL% EQU 0 GOTO Env
set PATH=%PATH%;%UserProfile%\miniconda3;%UserProfile%\miniconda3\Scripts
CALL conda -V
IF %ERRORLEVEL% EQU 0 GOTO Env
CALL START /wait "" source/Miniconda_installers/Miniconda3-latest-Windows-x86_64.exe /S /D=%UserProfile%\miniconda3
SET PATH=%PATH%;%UserProfile%\miniconda3;%UserProfile%\miniconda3\Scripts

:Env
CALL conda.bat activate
CALL conda update conda -y

CALL conda deactivate
CALL conda activate labelme
IF %ERRORLEVEL% EQU 0 goto App
CALL conda create --name=labelme python=3.6 -y
CALL conda activate labelme
CALL pip install labelme
CALL pip install mxnet
CALL pip install opencv-python-headless
CALL pip install tqdm
CALL pip install scikit-image

:App
CALL python source/__main__.py

CALL conda deactivate
