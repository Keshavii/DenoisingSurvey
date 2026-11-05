"""
Full-ranking evaluation of a trained STEAM model (TempSDU/STEAM @ 3ae6de2) for the RQ10 common protocol.

STEAM's own test mode ranks the test item against 99 sampled negatives. RQ10 scores every method by full ranking,
leave-one-out, NDCG@10 and Recall@10. This wrapper changes no STEAM code: it imports STEAM's model, TestDataset and
helpers, loads the checkpoint of the best validation epoch (highest 'sum' in valid_result_modified.txt, STEAM's own
corrected-sequence validation), and runs the same two forward passes STEAM's test mode runs:
  original   model.forward(masked_seq)
  corrected  corrector_inference -> seqs_correction -> seqs_normalization_test -> model.forward   (STEAM's prediction)
For each pass it reports STEAM's own sampled metrics (a check: they equal STEAM's test_result*.txt for that epoch) and
full-ranking Recall@10 / NDCG@10 over all items 1..n_items, the user's earlier items excluded.

Run from the STEAM repo folder, with the arguments used for training:
  python steam_full_eval.py -ef ./Beauty/test.dat -en ./Beauty/test_neg.dat -vf ./Beauty/valid.dat -n 12104 -o ./save_x/
"""
import argparse
import ast
import json
import math
import os

import torch
import torch.utils.data as Data

from model import model as SteamModel
from dataLoader import TestDataset
from script import seqs_normalization_test, evaluate_function, get_metrics

ap = argparse.ArgumentParser()
ap.add_argument('-ef', required=True)
ap.add_argument('-en', required=True)
ap.add_argument('-vf', default='')
ap.add_argument('-b', type=int, default=256)
ap.add_argument('-dr', type=float, default=0.5)
ap.add_argument('-hd', type=int, default=64)
ap.add_argument('-hn', type=int, default=1)
ap.add_argument('-ln', type=int, default=1)
ap.add_argument('-o', required=True)
ap.add_argument('-n', type=int, required=True)
ap.add_argument('-mml', type=int, default=60)
ap.add_argument('-mi', type=int, default=5)
ap.add_argument('-k', type=int, default=10)
ap.add_argument('--out', default='')
a = ap.parse_args()


def read_valid(path):
    rows = []
    if os.path.isfile(path):
        for line in open(path):
            line = line.strip()
            if line:
                rows.append(ast.literal_eval(line))
    return rows


valid = read_valid(a.o + 'valid_result_modified.txt')
if not valid:
    raise SystemExit(f"no {a.o}valid_result_modified.txt: run STEAM's -m=valid first")
best = max(valid, key=lambda r: (r['sum'], -r['epoch']))
epoch = best['epoch']
dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
item_num, K = a.n, a.k
n_items = item_num - 3                       # ids 1..n_items; 0 padding, item_num-2 EOS, item_num-1 mask

m = SteamModel(a.dr, a.hd, item_num, a.hn, a.ln, a.mi).to(dev)
m.load_state_dict(torch.load(a.o + 'model/steam-' + str(epoch) + '.pth', map_location=dev))
m.eval()
loader = Data.DataLoader(TestDataset(a.ef, a.en, item_num, a.mml), batch_size=a.b, shuffle=False, num_workers=0)


def full_rank(output, target, history):
    """output (B, item_num) logits; history (B, L) item ids of the user's earlier items (0 = padding)."""
    s = output.clone().float()
    s[:, 0] = -float('inf')
    s[:, n_items + 1:] = -float('inf')
    s.scatter_(1, history, -float('inf'))
    tgt = output.gather(1, target.view(-1, 1)).float()
    s.scatter_(1, target.view(-1, 1), tgt)  # the target itself is never excluded
    rank = (s > tgt).sum(1)
    hit = (rank < K).float()
    ndcg = torch.where(rank < K, 1.0 / torch.log2(rank.float() + 2.0), torch.zeros_like(hit))
    return hit.tolist(), ndcg.tolist()


res = {p: {'sampled': [], 'hit': [], 'ndcg': []} for p in ('original', 'corrected')}
with torch.no_grad():
    for batch in loader:
        _, test_neg, masked_seq, leave_one_seq, target = [t.to(dev) for t in batch]
        history = leave_one_seq.clone()                 # earlier items (original sequence), 0 = padding
        out = m.forward(masked_seq)[masked_seq == item_num - 1]
        res['original']['sampled'] += evaluate_function(out, target, test_neg)
        h, g = full_rank(out, target, history)
        res['original']['hit'] += h
        res['original']['ndcg'] += g
        full_o, ins_o = m.corrector_inference(leave_one_seq)
        mod = m.seqs_correction(full_o, ins_o, leave_one_seq)
        mod_masked = seqs_normalization_test(mod, a.mml, item_num).to(dev)
        out2 = m.forward(mod_masked)[mod_masked == item_num - 1]
        res['corrected']['sampled'] += evaluate_function(out2, target, test_neg)
        h, g = full_rank(out2, target, history)
        res['corrected']['hit'] += h
        res['corrected']['ndcg'] += g

rec = {'method': 'STEAM', 'checkpoint': a.o, 'best_valid_epoch': epoch, 'best_valid_sum': best['sum'],
       'users': len(res['original']['hit']), 'n_items': n_items, 'k': K}
for p, r in res.items():
    rec[p] = {f'recall@{K}': sum(r['hit']) / len(r['hit']), f'ndcg@{K}': sum(r['ndcg']) / len(r['ndcg']),
              'sampled_recall@10': get_metrics('recall@10', r['sampled']), 'sampled_mrr@10': get_metrics('mrr@10', r['sampled'])}
rec['reported'] = rec['corrected']           # STEAM predicts from the corrected sequence
out_path = a.out or (a.o + 'full_eval.json')
json.dump(rec, open(out_path, 'w'), indent=1)
print('RESULT', json.dumps(rec))
