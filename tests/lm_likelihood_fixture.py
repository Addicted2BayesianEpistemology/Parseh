# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare temporary data for the offline likelihood browser test."""
import json
from pathlib import Path
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / p) for p in ('lib', 'youtube/lib', 'tests')]
import asrcorrection
import lmlikelihood
import lmlikelihoodconfig
import lmlikelihoodcore
import lmlikelihoodpage
import network
from test_lm_likelihood import TinyModel

panel = '0:00\nB x!\n'
evidence = asrcorrection.evidence([{'start': 0, 'end': 2, 'text': 'B x!', 'words': [
    {'text': 'B', 'score': .9}, {'text': 'x!', 'score': .2, 'asr_alternatives': [{'text': 'y', 'score': None}]}]}], panel, 'it')
request = lmlikelihood.requests(evidence, panel, lmlikelihoodconfig.DEFAULTS)[0]
data = lmlikelihoodcore.evaluate(TinyModel(), request['left'], request['right'], lmlikelihoodcore.candidates(request['word'], ['ab']))
suggestion = lmlikelihood.proposal(request, data, {'model_id': 'tiny-installed'})
fixture = {'text': panel, 'review': {'choice': 'likelihood', 'evidence': evidence,
           'result': {'task': 'likelihood', 'suggestions': [suggestion]}, 'diagnostics': []}}
Path('/tmp/parseh-likelihood-browser-fixture.json').write_text(json.dumps(fixture))
Path('/tmp/parseh-likelihood-browser-defaults.json').write_text(json.dumps(lmlikelihoodconfig.DEFAULTS))
Path('/tmp/parseh-likelihood-settings-host.html').write_text(lmlikelihoodpage.page(network.SELF))
Path('/tmp/parseh-likelihood-settings-remote.html').write_text(lmlikelihoodpage.page(network.LAN))
