#!/bin/zsh
cd -- "$(dirname "$0")"

conda -V || { #except
  sudo ./source/Miniconda_installers/Miniconda3-latest-MacOSX-x86_64.sh -b -p
  source $HOME/miniconda3/bin/activate
  export PATH=$PATH:$HOME/.local/bin
  conda init zsh
  conda update conda -y
}

eval "$(conda shell.bash hook)"
conda deactivate
conda activate labelme || { #except
  conda create --name=labelme python=3.6 -y
  conda activate labelme
  pip install -r source/requirements.txt
}

python3 source/__main__.py --autosave

conda deactivate
