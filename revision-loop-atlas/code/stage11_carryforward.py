"""STAGE 1.1: carry-forward reprocessing of the recorded Stage-1 trajectories.

Adrian's adjudication 2026-10-07: the commentary confound (27% of rounds contain
no numeric answer; the volunteer praises/affirms instead of revising) is a
measurement-layer gap. Fix: for rounds t in 1..8 where the FROZEN parser extracts
no numeric answer, the round is a non-revision -> e(t) = e(t-1),
exact(t) = exact(t-1), flagged non_revision. The model's active hypothesis is
unchanged, so measured error must not jump.

No new LLM calls. The frozen 4-detector battery (Track A + B1 + B2 + B3, Stage-0.2
calibrated thresholds) is re-run on the corrected trajectories. Bar 0 for this
scope: if >= 75% of trajectories show zero detector firings, the state hypothesis
is retired for (model x task family x revision prompt x measurement x horizon).
"""
import json
import numpy as np
import sys

sys.path.insert(0, '/home/hatch/workspace/ai-theory')
from revision_measure import extract_final_number

BASE = '/home/hatch/workspace/ai-theory/revision_loop'
res = json.load(open(f'{BASE}/revision_loop_results.json'))
thr = res['detector_thresholds']
B1_S, B2_AMP, B3_T = thr['B1_S'], thr['B2_AMP'], thr['B3_T']
N = 9


def b1_fire(e):
    W = np.array(e[3:9])
    slope = np.polyfit(np.arange(3, 9), W, 1)[0]
    return bool((W.mean() > 0.4) and (abs(slope) < B1_S))


def b2_fire(e):
    de = np.diff(np.array(e))
    opp = de[:-1] * de[1:] < 0
    big = (np.abs(de[:-1]) > B2_AMP) & (np.abs(de[1:]) > B2_AMP)
    return bool(np.sum(opp & big) >= 3)


def b3_fire(e):
    e = np.array(e)
    de = np.diff(e)
    return bool((np.sum(de > 0) >= 5) and ((e[8] - e[0]) > B3_T))


def tracka_fire(ex):
    F = np.array(ex, dtype=bool)
    return bool(np.any(~F[:-1] & F[1:]))


out_trajs = []
cf_rounds_total = 0
for t in res['trajectories']:
    rounds = t['rounds']
    e_corr, ex_corr, nonrev = [], [], []
    for i, r in enumerate(rounds):
        if i == 0:
            has_num = extract_final_number(r['answer']) is not None
            e_corr.append(r['e'])
            ex_corr.append(r['exact'])
            nonrev.append(False)
            if not has_num:
                print(f"NOTE: traj {t['traj_id']} round 0 has no numeric answer")
        else:
            if extract_final_number(r['answer']) is None:
                e_corr.append(e_corr[-1])
                ex_corr.append(ex_corr[-1])
                nonrev.append(True)
                cf_rounds_total += 1
            else:
                e_corr.append(r['e'])
                ex_corr.append(r['exact'])
                nonrev.append(False)
    de_corr = [0.0] + [e_corr[i] - e_corr[i - 1] for i in range(1, N)]
    detectors = {
        'TrackA_solve': tracka_fire(ex_corr),
        'B1_stall': b1_fire(e_corr),
        'B2_oscillation': b2_fire(e_corr),
        'B3_divergence': b3_fire(e_corr),
    }
    m = t['m']
    informative = any((mm > 0.05 and abs(dd) > 0.02)
                      for mm, dd in zip(m[1:], de_corr[1:]))
    out_trajs.append({
        'traj_id': t['traj_id'],
        'e_corrected': [round(v, 4) for v in e_corr],
        'exact_corrected': ex_corr,
        'non_revision_rounds': [i for i, f in enumerate(nonrev) if f],
        'detectors': detectors,
        'n_firings': sum(detectors.values()),
        'informative': informative,
    })

counts = {k: sum(t['detectors'][k] for t in out_trajs)
          for k in ['TrackA_solve', 'B1_stall', 'B2_oscillation', 'B3_divergence']}
zero_fire = sum(1 for t in out_trajs if t['n_firings'] == 0)
informative_n = sum(1 for t in out_trajs if t['informative'])

bar0 = {
    'n_trajectories': len(out_trajs),
    'zero_firing_trajectories': zero_fire,
    'zero_firing_fraction': zero_fire / len(out_trajs),
    'threshold': 0.75,
    'fires': (zero_fire / len(out_trajs)) >= 0.75,
}

out = {
    'stage': '1.1 carry-forward reprocessing',
    'rule': 't in 1..8 with extract_final_number(answer) is None -> '
            'e(t)=e(t-1), exact(t)=exact(t-1), flagged non_revision',
    'no_new_llm_calls': True,
    'carryforward_rounds': cf_rounds_total,
    'detector_thresholds': thr,
    'counts': counts,
    'expected_null_firings': res['aggregate_counts']['expected_null_firings'],
    'informative': informative_n,
    'bar0': bar0,
    'trajectories': out_trajs,
}
json.dump(out, open(f'{BASE}/revision_loop_results_11.json', 'w'), indent=1)

print('carry-forward rounds applied:', cf_rounds_total)
print('counts:', counts)
print('expected null:', res['aggregate_counts']['expected_null_firings'])
print('informative:', informative_n, '/ 30')
print('Bar 0: zero-firing fraction = %.3f (bar 0.75) -> %s'
      % (bar0['zero_firing_fraction'], 'FIRES - RETIRE' if bar0['fires'] else 'does not fire'))
for t in out_trajs:
    if t['n_firings']:
        fired = [k for k, v in t['detectors'].items() if v]
        print(f"  traj {t['traj_id']}: {fired} nonrev={t['non_revision_rounds']}")
