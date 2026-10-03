# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional bounded installed-weight CPU/GPU check; never downloads weights."""
import argparse
import copy
import json
import math
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import lmgguf
import lmlikelihood
import lmlikelihoodconfig as settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Existing complete local GGUF')
    parser.add_argument('--python', default=settings.DEFAULTS['python'])
    parser.add_argument('--gpu-device', type=int, default=0)
    parser.add_argument('--modes', default='cpu', help='Comma-separated cpu,cuda-partial,cuda-full')
    parser.add_argument('--context-tokens', type=int, default=256)
    parser.add_argument('--score-tolerance', type=float, default=.5,
                        help='Explicit absolute summed-score tolerance for this short CPU/GPU example (quantized backend arithmetic differs)')
    parser.add_argument('--output', help='Optional private local diagnostic file')
    args = parser.parse_args()
    if not math.isfinite(args.score_tolerance) or args.score_tolerance < 0:
        parser.error('Score tolerance must be finite and nonnegative')
    model = lmgguf.inspect(args.model)
    model.update(source='path', model_id=model['name'])
    modes = args.modes.split(',')
    if any(mode not in ('cpu', 'cuda-partial', 'cuda-full') for mode in modes):
        parser.error('Choose cpu,cuda-partial,cuda-full')
    request = {'left': 'Loro ', 'right': ' detto ciao.', 'word': {
        'text': 'anno', 'word_id': 's0w1', 'segment_id': 's0', 'asr_confidence': .2,
        'asr_alternatives': [{'text': 'hanno', 'score': None}], 'alternatives_available': True}}
    results = {}
    baseline, baseline_tokens = None, None
    for mode in modes:
        cfg = dict(settings.DEFAULTS, model=model, python=args.python,
                   backend='cpu' if mode == 'cpu' else 'cuda',
                   gpu_layers=0 if mode == 'cpu' else 2 if mode == 'cuda-partial' else -1,
                   gpu_device=args.gpu_device, threads=2, context_tokens=args.context_tokens,
                   beam_width=2, candidate_count=3, replacement_tokens=3, target_seconds=30)
        started = time.monotonic()
        settings.validate(cfg)
        session = lmlikelihood.Session(cfg, lambda: lmgguf.revalidate(model))
        try:
            first = session.request({'op': 'target', 'request': request}, 60)['result']
            second = session.request({'op': 'target', 'request': request}, 60)['result']
            scores = lambda data: {c['text']: c['log_likelihood'] for c in data['candidates'] if c['log_likelihood'] is not None}
            left, right = scores(first), scores(second)
            print(json.dumps({'mode': mode, 'repeat_differences': {k: right[k] - left[k] for k in left.keys() & right.keys()}, 'first_candidates': list(left), 'second_candidates': list(right)}), flush=True)
            assert left.keys() == right.keys() and all(abs(left[k] - right[k]) < 1e-6 for k in left), 'Independent repeat scores differ'
            reordered = copy.deepcopy(request)
            reordered['word']['asr_alternatives'] = [{'text': 'is', 'score': None}, {'text': 'hanno', 'score': None}]
            reordered_scores = scores(session.request({'op': 'target', 'request': reordered}, 60)['result'])
            assert all(k in reordered_scores and abs(left[k] - reordered_scores[k]) < 1e-6 for k in left), 'Candidate evaluation order changed scores'
            assert first['coverage']['state'] == 'complete' and {'anno', 'hanno'} <= left.keys(), 'Incomplete mandatory coverage'
            hw = first['hardware']
            if mode != 'cpu':
                assert hw['backend'] == 'cuda' and hw['offloaded_layers'] > 0, 'GPU request fell back to CPU'
                if mode == 'cuda-partial':
                    assert hw['offloaded_layers'] == 2, 'Partial offload ignored'
                else:
                    assert hw['offloaded_layers'] >= hw['model_layers'], 'Full offload incomplete'
            else:
                assert hw['offloaded_layers'] == 0 and hw['device'] is None, 'CPU run allocated model layers on GPU'
                baseline = left
                baseline_tokens = {c['text']: c['evaluated_tokens'] for c in first['candidates']}
            differences = {k: left[k] - baseline[k] for k in left.keys() & baseline.keys()} if baseline else {}
            print(json.dumps({'mode': mode, 'scores': left, 'difference_from_cpu': differences}), flush=True)
            assert all(abs(v) <= args.score_tolerance for v in differences.values()), 'CPU/GPU score difference exceeds the explicit numerical tolerance'
            if baseline:
                assert first['tied_best'] == [max(baseline, key=baseline.get)], 'The short example’s best candidate changed across backends'
                assert all(c['evaluated_tokens'] == baseline_tokens[c['text']] for c in first['candidates'] if c['text'] in baseline_tokens), 'CPU/GPU supplied token counts differ'
            results[mode] = {'hardware': hw, 'scores': left,
                'origins': {c['text']: [o['kind'] for o in c['origins']] for c in first['candidates']},
                'coverage': first['coverage'], 'elapsed_seconds': round(time.monotonic() - started, 3),
                'scoring_seconds': first['elapsed_seconds'], 'repeat_scores_identical_within_1e-6': True,
                'candidate_order_isolated': True,
                'difference_from_cpu': differences}
            print(json.dumps({'completed': mode, 'hardware': hw, 'scoring_seconds': first['elapsed_seconds']}), flush=True)
        finally:
            session.close()
        assert lmlikelihood.loaded_count() == 0, 'Worker remained loaded'
    if 'cuda-full' in modes:
        # A real native load must remain cancellable. The parent kills its own
        # child even if model loading has not reached a cooperative callback.
        event = threading.Event()
        timer = threading.Timer(.15, event.set)
        def check():
            if event.is_set():
                raise lmgguf.ScoringError('cancelled', 'Cancelled smoke load.')
        started = time.monotonic(); timer.start()
        try:
            cancelled = lmlikelihood.Session(dict(cfg, backend='cuda', gpu_layers=-1), check)
            cancelled.close()
            raise AssertionError('The bounded load unexpectedly finished before cancellation')
        except lmgguf.ScoringError as error:
            assert error.code == 'cancelled'
            results['loading_cancellation'] = {'elapsed_seconds': round(time.monotonic() - started, 3), 'workers_remaining': lmlikelihood.loaded_count()}
            assert lmlikelihood.loaded_count() == 0
        finally:
            timer.cancel()
    lmgguf.revalidate(model)
    report = {'model': model['name'], 'runtime': settings.PIN, 'weight_identity_unchanged': True,
              'accuracy_evaluated': False, 'cpu_gpu_score_tolerance': args.score_tolerance, 'results': results}
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checks_passed': True, 'modes': modes, 'weight_identity_unchanged': True}), flush=True)


if __name__ == '__main__':
    main()
