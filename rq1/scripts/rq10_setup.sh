#!/bin/bash
# RQ10 setup on PC3 (RTX 4090): the 11 specialists' repositories at fixed commits and one conda env per code base,
# at each README's versions. Only the CUDA build of torch is chosen for the 4090 (Ada needs CUDA >= 11.0 builds with
# sm_80/sm_86 kernels); every such choice is listed in DEVIATIONS below and in the Plan of Action doc.
# Resumable: finished envs are skipped. Run unattended:
#   systemd-run --user --unit=rq10setup --collect bash -c "bash ~/survey/rq1/scripts/rq10_setup.sh > ~/rq10_setup.log 2>&1"
# Then: bash ~/survey/rq1/scripts/rq10_setup.sh check
set -u
ROOT=${ROOT:-$HOME/survey/rq10}
REPOS=$ROOT/repos
OK=$ROOT/envs_ok
mkdir -p "$REPOS" "$OK"
source ~/miniconda3/etc/profile.d/conda.sh
TS=https://download.pytorch.org/whl/torch_stable.html
W=https://download.pytorch.org/whl
PYG=https://data.pyg.org/whl
say() { echo "$(date '+%F %T') $*"; }

# name|github repo|commit audited 4 Nov 2026|env
REPO_LIST="
fmlp|Woeee/FMLP-Rec|51acc8c|fmlp
hsd|zc-97/HSD|9c146a0|recbole
steam|TempSDU/STEAM|3ae6de2|steam
ssdrec|zc-97/SSDRec|299421e|recbole
iadsr|Applied-Machine-Learning-Lab/IADSR|3ffc9a8|iadsr
preferdiff|lswhim/PreferDiff|fdf45b0|preferdiff
damrs|XMUDM/DA-MRS|7dee19e|damrs
guider|Neon-Jing/Guider|fb0ee56|mmrec
gdmsr|tsinghua-fib-lab/Graph-Denoising-SocialRec|0916e29|gdmsr
gbsr|yimutianyang/KDD24-GBSR|881d712|gbsr
hdsr|laowangzi/HDSR|9721276|hdsr
"
# DEVIATIONS from the READMEs (all forced by the 4090 or by the README itself):
# fmlp     README: Python 3.7, PyTorch 1.8 (no CUDA named)           -> torch 1.8.0+cu111
# steam    requirements: torch 1.8.0+cu111                            -> as written
# recbole  HSD/SSDRec requirements: torch 1.12.0 (no CUDA named)      -> torch 1.12.0+cu116; dgl/pyg are imported only
#          inside RecBole's graph export, never on the sequential path, so they are not installed
# iadsr    requirements.txt is a pip freeze whose pins conflict (llm2vec 0.2.2 wants transformers <= 4.40.2, the
#          freeze has 4.47.1, which Llama 3.1 needs); the whole freeze (torch 2.5.1 with its cu124 libraries) is
#          installed with --no-deps to reproduce the authors' env exactly; flash-attn from its prebuilt wheel
# preferdiff README gives no versions -> torch 2.5.1+cu121 (as PC1) + accelerate, transformers, pyyaml
# damrs    README list: torch 2.0.0, pyg 2.3.0 ...                    -> torch 2.0.0+cu118; torch_scatter and the
#          unlisted imports (torchvision, sklearn, matplotlib, pillow) added
# mmrec    GUIDER requirements (= MMRec's): python 3.7.11, torch 1.11.0 -> torch 1.11.0+cu113; unlisted imports added
#          (torch_geometric 2.0.4, torch_scatter, geomloss, lmdb, sklearn, matplotlib, pillow). FREEDOM runs here too.
# gdmsr    README: PyTorch 1.7.1 (+ dgl, unlisted)                    -> torch 1.7.1+cu110, dgl-cu110 0.6.1
# gbsr     paper numbers are from the TF 1.15 code (CUDA 10, cannot use a 4090); we run the authors' PyTorch port
#          (torch_version/) with requirements' torch 1.10.0 built for cu113 instead of cudatoolkit 10.2
# hdsr     requirements: torch 1.13.1+cu117 and the pt113cu117 PyG wheels -> as written

mkenv() {  # name python [pip args...]: create env r10-<name> and install; skipped when done before
  local n=$1 py=$2; shift 2
  [ -f "$OK/$n" ] && { say "env $n: done before"; return 0; }
  conda env remove -y -q -n r10-$n > /dev/null 2>&1
  conda create -y -q -n r10-$n python=$py > /dev/null 2>&1 || conda create -y -q -n r10-$n -c conda-forge python=$py > /dev/null \
    || { say "env $n: FAILED (python $py)"; return 1; }
  "$@" && touch "$OK/$n" && say "env $n: ok" || say "env $n: FAILED"
}
pipn() { ~/miniconda3/envs/r10-$N/bin/pip install -q "$@"; }

clone_all() {
  echo "$REPO_LIST" | while IFS='|' read n repo commit env; do
    [ -z "$n" ] && continue
    if [ ! -d "$REPOS/$n/.git" ]; then git clone -q "https://github.com/$repo" "$REPOS/$n" || { say "clone $n: FAILED"; continue; }; fi
    (cd "$REPOS/$n" && git checkout -q "$commit" && say "repo $n at $(git log -1 --format=%h)")
  done
}

build_all() {
  N=fmlp;       mkenv $N 3.7    pipn torch==1.8.0+cu111 -f $TS numpy scipy tqdm
  N=steam;      mkenv $N 3.8    pipn torch==1.8.0+cu111 -f $TS numpy==1.19.4 tqdm==4.64.0
  N=recbole;    mkenv $N 3.8    pipn torch==1.12.0+cu116 --extra-index-url $W/cu116 numpy==1.20.3 openpyxl==3.0.9 PyYAML==6.0 \
                                     recbole==1.0.1 tqdm==4.62.3
  N=iadsr;      mkenv $N 3.9    bash -c "pipn() { ~/miniconda3/envs/r10-iadsr/bin/pip install -q \"\$@\"; }
                                  grep -v -E '^flash-attn' $REPOS/iadsr/requirements.txt > $ROOT/iadsr_req_nodeps.txt &&
                                  pipn --no-deps -r $ROOT/iadsr_req_nodeps.txt &&
                                  pipn --no-deps info-nce-pytorch==0.1.4 &&
                                  pipn --no-deps https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.2.post1/flash_attn-2.7.2.post1+cu12torch2.5cxx11abiFALSE-cp39-cp39-linux_x86_64.whl"
  N=preferdiff; mkenv $N 3.10   pipn torch==2.5.1+cu121 --extra-index-url $W/cu121 accelerate transformers numpy pyyaml tqdm
  N=damrs;      mkenv $N 3.10.9 pipn torch==2.0.0+cu118 torchvision==0.15.1+cu118 --extra-index-url $W/cu118 numpy==1.23.5 \
                                     pandas==1.5.3 scipy==1.10.0 pyyaml==6.0 torch_geometric==2.3.0 networkx==2.8.4 tqdm==4.65.0 \
                                     lmdb==1.4.0 scikit-learn matplotlib pillow torch_scatter -f $PYG/torch-2.0.0+cu118.html
  N=mmrec;      mkenv $N 3.7.11 pipn torch==1.11.0+cu113 torchvision==0.12.0+cu113 --extra-index-url $W/cu113 numpy==1.21.5 \
                                     pandas==1.3.5 scipy==1.7.3 pyyaml==6.0 torch_geometric==2.0.4 geomloss lmdb scikit-learn \
                                     matplotlib pillow torch_scatter -f $PYG/torch-1.11.0+cu113.html
  N=gdmsr;      mkenv $N 3.7    pipn torch==1.7.1+cu110 -f $TS dgl-cu110==0.6.1 numpy pandas tqdm setproctitle
  N=gbsr;       mkenv $N 3.7    pipn torch==1.10.0+cu113 -f $TS numpy==1.19.2 faiss-cpu==1.7.1.post2 numba==0.56.2 scipy==1.3.0 \
                                     tqdm==4.62.3
  N=hdsr;       mkenv $N 3.8    pipn torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==0.13.1+cu117 --extra-index-url $W/cu117 \
                                     torch-scatter==2.1.1 torch-sparse==0.6.17 torch-cluster==1.6.1 torch-spline-conv==1.2.2 \
                                     -f $PYG/torch-1.13.1+cu117.html torch-geometric==2.3.1 numpy==1.18.0 pandas==1.1.5 \
                                     scikit-learn==1.0.2 scipy==1.7.3 seaborn==0.10.0 tqdm==4.66.1 prettytable networkx
}

check_all() {  # every env must run a real kernel on the 4090 (old CUDA builds can import but fail on Ada)
  for n in fmlp steam recbole iadsr preferdiff damrs mmrec gdmsr gbsr hdsr; do
    PY=~/miniconda3/envs/r10-$n/bin/python
    [ -x $PY ] || { echo "$n: no env"; continue; }
    printf "%-11s " $n
    $PY -c "import torch,numpy;x=torch.randn(512,512,device='cuda');y=(x@x).sum().item();print(torch.__version__,'numpy',numpy.__version__,'gpu ok')" 2>&1 | tail -1
  done
}

case "${1:-all}" in
  check) check_all ;;
  clone) clone_all ;;
  *) say "RQ10 setup start"; clone_all; build_all; say "RQ10 setup end"; check_all ;;
esac
