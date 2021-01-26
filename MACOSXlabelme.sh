#!/bin/bash

conda -V || { #except
  sudo ./source/Miniconda_insatllers/Miniconda3-latest-MacOSX-x86_64.sh -b -p
  conda update conda -y
}
eval "$(conda shell.bash hook)"
conda deactivate
conda activate labelme || { #except
  conda create --name=labelme python=3.6 -y
  conda activate labelme
  pip install -r source/requirements.txt
}

python3 source/__main__.py

conda deactivate
