from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import pytest

from repo2docker.contentproviders import Mercurial


def _add_content_to_hg(repo_dir):
    """Add content to file 'test' in hg repository and commit."""
    # use append mode so this can be called multiple times
    with open(Path(repo_dir) / "test", "a") as f:
        f.write("Hello")

    subprocess.check_call(["hg", "add", "test"], cwd=repo_dir)
    subprocess.check_call(["hg", "commit", "-m", "Test commit"], cwd=repo_dir)


def _get_sha1(repo_dir):
    """Get repository's current commit SHA1."""
    sha1 = subprocess.Popen(["hg", "identify"], stdout=subprocess.PIPE, cwd=repo_dir)
    return sha1.stdout.read().decode().strip()


@pytest.fixture()
def hg_repo():
    """
    Make a dummy git repo in which user can perform git operations

    Should be used as a contextmanager, it will delete directory when done
    """
    with TemporaryDirectory() as gitdir:
        subprocess.check_call(["hg", "init"], cwd=gitdir)
        yield gitdir


@pytest.fixture()
def hg_repo_with_content(hg_repo):
    """Create a hg repository with content"""
    _add_content_to_hg(hg_repo)
    sha1 = _get_sha1(hg_repo)

    yield hg_repo, sha1


def test_detect_mercurial(hg_repo_with_content, repo_with_content):
    mercurial = Mercurial()
    assert mercurial.detect("this-is-not-a-directory") is None
    assert mercurial.detect("https://github.com/jupyterhub/repo2docker") is None

    git_repo = repo_with_content[0]
    assert mercurial.detect(git_repo) is None

    hg_repo = hg_repo_with_content[0]
    assert mercurial.detect(hg_repo) == {"repo": hg_repo, "ref": None}


def test_clone(hg_repo_with_content):
    """Test simple hg clone to a target dir"""
    upstream, sha1 = hg_repo_with_content

    with TemporaryDirectory() as clone_dir:
        spec = {"repo": upstream}
        mercurial = Mercurial()
        for _ in mercurial.fetch(spec, clone_dir):
            pass
        assert (Path(clone_dir) / "test").exists()

        assert mercurial.content_id == sha1[:7]


def test_bad_ref(hg_repo_with_content):
    """
    Test trying to checkout a ref that doesn't exist
    """
    upstream, sha1 = hg_repo_with_content
    with TemporaryDirectory() as clone_dir:
        spec = {"repo": upstream, "ref": "does-not-exist"}
        with pytest.raises(ValueError):
            for _ in Mercurial().fetch(spec, clone_dir):
                pass
