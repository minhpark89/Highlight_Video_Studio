import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('github_deploy_flow', Path(__file__).resolve().parents[1] /
                                           'checkpoints/tools/v1.2.3/github_deploy.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


@pytest.mark.parametrize('exists,draft,expected', [
    (False, True, ['inspect', 'push', 'draft', 'upload', 'publish', 'verify']),
    (True, True, ['inspect', 'push', 'resume', 'upload', 'publish', 'verify']),
    (True, False, ['inspect', 'push', 'resume', 'verify']),
])
def test_deploy_resumes_the_exact_release_and_does_not_republish_existing_public_assets(exists, draft, expected):
    calls = []
    def invoke(action):
        calls.append(action)
        return {'release_exists': exists, 'push_permission': True} if action == 'inspect' else {'draft': draft}
    flow.deploy(invoke)
    assert calls == expected


def test_failed_push_never_creates_or_uploads_a_release():
    calls = []
    def invoke(action):
        calls.append(action)
        if action == 'push':
            raise RuntimeError('connection unavailable')
        return {'release_exists': False, 'push_permission': True}
    with pytest.raises(RuntimeError, match='connection unavailable'):
        flow.deploy(invoke)
    assert calls == ['inspect', 'push']


def test_denied_repository_permission_stops_before_mutations():
    calls = []
    def invoke(action):
        calls.append(action)
        return {'push_permission': False}
    with pytest.raises(RuntimeError, match='no push permission'):
        flow.deploy(invoke)
    assert calls == ['inspect']
