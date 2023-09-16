#!bin/bash
export role=$1

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

#-- Downloading Required weights and data -- #
echo "Downloading GroundingDINO & Segment Anything Model (SAM) Weights"
WEIGHT_DIR=$ROOT_DIR/artifacts/weights
if [[ ! -e $WEIGHT_DIR ]]; then
    mkdir -p $WEIGHT_DIR
    cd $WEIGHT_DIR
    wget -q https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
    wget -q https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
elif [[ ! -d $WEIGHT_DIR ]]; then
    echo "$WEIGHT_DIR already exists but is not a directory" 1>&2
fi

# -- Installing Dependencies which can't be installed via toml -- #
python3 -m pip install -e "git+https://github.com/CompVis/taming-transformers.git@master#egg=taming-transformers"

# -- Stable Diffusion -- #
cd /opt/Neuro-Symbolic-Video-Frame-Search/ns_vfs/model/diffusion/stable_diffusion
python3 -m pip install -e .

# -- Installing video_to_automaton -- #
echo "Installing video_to_automaton"
cd $ROOT_DIR
python3 -m pip install --upgrade pip build
if [[ $role == "dev" ]];
then 
    python3 -m pip install --editable ."[dev, test]"
else
    python3 -m pip install -e .
fi
