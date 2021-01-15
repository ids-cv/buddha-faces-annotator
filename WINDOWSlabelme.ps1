

Try{conda -V}
catch
{
    start /wait "" source/Miniconda_insatllers/Miniconda3-latest-Windows-x86_64.exe /S /D=%UserProfile%\Miniconda3
    conda activate powershell
    conda update conda -y
}

conda deactivate

try{conda activate labelme}
catch{
    conda create --name=labelme python=3.6 -y
    conda activate labelme
}

pip install labelme
pip install mxnet
pip install opencv-python-headless
pip install tqdm
pip install scikit-image

python3 source/__main__.py

conda deactivate
