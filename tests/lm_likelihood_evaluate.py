# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional fixed-case evaluation with existing ASR evidence and installed weights.

No ASR rerun, downloads, model-manager loading or chat requests. References
are supplied by the reviewer and are never inserted as Whisper alternatives.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('lib', 'youtube/lib')]
import asrcorrection
import lmgguf
import lmlikelihood
import lmlikelihoodconfig as settings
import sttpanel


def read(path, limit=32 << 20):
    path = Path(path)
    if path.stat().st_size > limit:
        raise ValueError('Evaluation fixture is too large')
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', required=True, help='Private JSON list: name, asr_file, word_ids, optional filtered_word_ids and references')
    models = parser.add_mutually_exclusive_group(required=True)
    models.add_argument('--model-id', help='Exact discovered installed model ID')
    models.add_argument('--model-path', help='Existing complete local GGUF')
    parser.add_argument('--source', choices=('unsloth', 'ollama'), default='unsloth')
    parser.add_argument('--manager-url', default=settings.DEFAULTS['manager_url'])
    parser.add_argument('--backend', choices=('cpu', 'cuda', 'metal', 'vulkan'), default='cpu')
    parser.add_argument('--python', default=settings.DEFAULTS['python'])
    parser.add_argument('--context-tokens', type=int, default=settings.DEFAULTS['context_tokens'])
    parser.add_argument('--filtered', action='store_true', help='Use the configured probability floor and similar-sound filter')
    parser.add_argument('--minimum-probability', type=float, default=settings.DEFAULTS['minimum_candidate_probability'])
    parser.add_argument('--output', required=True, help='Private output JSON; created with owner-only permissions')
    args = parser.parse_args()
    if args.model_path:
        model = lmgguf.inspect(args.model_path)
        model.update(source='path', model_id=model['name'])
    else:
        inventory, _ = lmgguf.discover(args.source, args.manager_url)
        found = [m for m in inventory if m['model_id'] == args.model_id]
        if len(found) != 1:
            parser.error('The selected installed model was not resolved unambiguously')
        model = found[0]
    cases_file = Path(args.cases).resolve()
    cases = read(cases_file)
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        parser.error('Supply 1–32 fixed cases')
    config = dict(settings.DEFAULTS, model=model, python=args.python,
                  backend=args.backend, gpu_layers=0 if args.backend == 'cpu' else -1,
                  context_tokens=args.context_tokens,
                  target_seconds=60, phonetic_filter=args.filtered,
                  minimum_candidate_probability=args.minimum_probability if args.filtered else 0)
    settings.validate(config)
    prepared, count = [], 0
    for case in cases:
        source = read(cases_file.parent / case['asr_file'])
        panel, _ = sttpanel.segments_to_panel(source['segments'])
        evidence = asrcorrection.evidence(source['segments'], panel, source['language'])
        ids = case.get('filtered_word_ids', case['word_ids']) if args.filtered else case['word_ids']
        requests = lmlikelihood.requests(evidence, panel, config, ids)
        count += len(requests)
        if count > 500:
            parser.error('This bounded evaluation accepts at most 500 targets')
        prepared.append((case, requests))
    rows = []
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    session = lmlikelihood.Session(config, lambda: lmgguf.revalidate(model))
    try:
        for case, requests in prepared:
            refs = {r['word_id']: r for r in case.get('references', [])}
            for i, request in enumerate(requests):
                started = time.monotonic()
                try:
                    result = session.request({'op': 'target', 'request': request}, 90)['result']
                except lmgguf.ScoringError as error:
                    result = {'failure': error.say, 'code': error.code}
                rows.append({'model': model['model_id'], 'video': case['name'],
                             'word_id': request['word']['word_id'], 'original': request['word']['text'],
                             'asr_score': request['word']['asr_confidence'],
                             'reference': refs.get(request['word']['word_id']), 'result': result,
                             'seconds': round(time.monotonic() - started, 3)})
                raw = json.dumps({'basis': 'Reviewer references; accuracy depends on their validation.',
                                  'results': rows}, ensure_ascii=False, allow_nan=False)
                if len(raw.encode('utf-8')) > 32 << 20:
                    raise ValueError('Evaluation diagnostics exceeded 32 MiB')
                temporary = output.with_name(output.name + '.tmp')
                with temporary.open('w', encoding='utf-8') as f:
                    os.chmod(temporary, 0o600)
                    f.write(raw)
                os.replace(temporary, output)
                print(json.dumps({'case': case['name'], 'done': i + 1, 'total': len(requests),
                                  'failed': bool(result.get('failure'))}), flush=True)
    finally:
        session.close()


if __name__ == '__main__':
    main()
