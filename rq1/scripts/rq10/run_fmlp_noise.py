"""
FMLP-Rec runner for noise-variant datasets (Beauty_N0, Beauty_N2_20, etc.).

The original utils.get_seq_dic only recognises hardcoded names like 'Beauty',
'Sports', 'Yelp' that appear in sequential_data_list.  Noise variants like
'Beauty_N0' fall through both branches and leave seq_dic unbound.

This wrapper:
  1. Patches utils.get_seq_dic to handle any name matching <Base>_<level>[_s<seed>], level N0, I10, I20 (stage 2)
     or N2_20, N3_30 (5 Nov).
     Noise variants are also added to sequential_data_list at runtime so the
     downstream functions get_dataloder() and get_rating_matrix() take the
     right sequential path.
  2. For the sample file (negative evaluation candidates), noise variants reuse
     the base dataset's _sample.txt (noise only affects training sequences).
  3. Sets the loaded module's __name__ to '__main__' so main.py's
     if __name__ == '__main__': block fires when it is exec'd.

Usage (run from the fmlp repo dir):
  python run_fmlp_noise.py --data_name Beauty_N0 [other main.py args...]
"""
import sys
import re
import importlib.util
import os

# ── 1. Import and patch utils BEFORE main.py is loaded ───────────────────────
import utils as _u

_original_get_seq_dic = _u.get_seq_dic

# 5 Nov names (Beauty_N2_20) and RQ10 stage-2 names (Beauty_I10_s1, Sports_and_Outdoors_N0_s2): <base>_<level>[_s<seed>]
_NOISE_PAT = re.compile(r'_(N0|N2_20|N3_30|I10|I20)(_s\d+)?$')


def _patched_get_seq_dic(args):
    if not _NOISE_PAT.search(args.data_name):
        return _original_get_seq_dic(args)

    base = _NOISE_PAT.sub('', args.data_name)

    # Register in sequential_data_list so get_dataloder + get_rating_matrix
    # take the sequential path (they check the same list).
    if args.data_name not in _u.sequential_data_list:
        _u.sequential_data_list.append(args.data_name)

    # Noise .txt file; base dataset's _sample.txt (negatives are unchanged).
    args.data_file   = args.data_dir + args.data_name + '.txt'
    args.sample_file = args.data_dir + base + '_sample.txt'

    user_seq, max_item, num_users, sample_seq = \
        _u.get_user_seqs_and_sample(args.data_file, args.sample_file)

    seq_dic = {
        'user_seq':    user_seq,
        'num_users':   num_users,
        'sample_seq':  sample_seq,
    }
    return seq_dic, max_item


_u.get_seq_dic = _patched_get_seq_dic

# ── 2. Load and run main.py ───────────────────────────────────────────────────
# Set __name__ to '__main__' so the if __name__ == '__main__': guard fires.
# sys.argv is left intact so argparse in main.py sees our --data_name arg.

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "__main__", os.path.join(_here, "main.py"))
_mod = importlib.util.module_from_spec(_spec)
_mod.__name__ = "__main__"
sys.modules.setdefault("__main_fmlp__", _mod)   # don't clobber real __main__
_spec.loader.exec_module(_mod)
