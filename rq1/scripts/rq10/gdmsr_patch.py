"""
GDMSR runner with PyTorch 1.7 compatibility patch.

The GDMSR repo uses nn.TransformerEncoderLayer(embedding_size, 1, batch_first=True),
but `batch_first` was only added in PyTorch 1.9.  r10-gdmsr ships PyTorch 1.7.1.

Fix: monkey-patch nn.TransformerEncoderLayer.__init__ to silently drop `batch_first=True`
AND wrap the forward() so that input is transposed to (seq, batch, feat) before the
encoder and transposed back to (batch, seq, feat) after — matching what batch_first=True
would have provided.

Usage (run from the gdmsr repo dir):
  python gdmsr_patch.py --dataset_name yelp [other main.py args...]
"""
import sys
import os
import torch.nn as nn

# ── 1. Patch TransformerEncoderLayer to strip batch_first ────────────────────

_OrigTEL = nn.TransformerEncoderLayer
_orig_tel_init = _OrigTEL.__init__
_orig_tel_fwd  = _OrigTEL.forward


def _patched_tel_init(self, *args, **kwargs):
    self._survey_batch_first = kwargs.pop('batch_first', False)
    _orig_tel_init(self, *args, **kwargs)


def _patched_tel_fwd(self, src, *args, **kwargs):
    if getattr(self, '_survey_batch_first', False):
        # input is (batch, seq, feat); encoder expects (seq, batch, feat)
        src = src.transpose(0, 1)
        out = _orig_tel_fwd(self, src, *args, **kwargs)
        return out.transpose(0, 1)
    return _orig_tel_fwd(self, src, *args, **kwargs)


nn.TransformerEncoderLayer.__init__ = _patched_tel_init
nn.TransformerEncoderLayer.forward  = _patched_tel_fwd

# ── 2. Ensure log dirs exist for the requested dataset ───────────────────────
# GDMSR also fails if log/<dataset> doesn't exist; create it here.
import argparse as _ap
_p = _ap.ArgumentParser(add_help=False)
_p.add_argument('--dataset_name', default='yelp')
_known, _ = _p.parse_known_args()
os.makedirs(os.path.join('log', _known.dataset_name), exist_ok=True)

# ── 3. Load and run main.py ───────────────────────────────────────────────────
import importlib.util
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "__main__", os.path.join(_here, "main.py"))
_mod = importlib.util.module_from_spec(_spec)
_mod.__name__ = "__main__"
_spec.loader.exec_module(_mod)
