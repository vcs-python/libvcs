<div align="center">
  <a href="https://libvcs.git-pull.com/"><img src="https://raw.githubusercontent.com/vcs-python/libvcs/master/docs/_static/img/libvcs.svg" alt="libvcs logo" height="120"></a>
  <h1>libvcs</h1>
  <p><strong>The Swiss Army Knife for Version Control Systems in Python.</strong></p>
  <p>
    <a href="https://pypi.org/project/libvcs/"><img src="https://img.shields.io/pypi/v/libvcs.svg" alt="PyPI version"></a>
    <a href="https://pypi.org/project/libvcs/"><img src="https://img.shields.io/pypi/pyversions/libvcs.svg" alt="Python versions"></a>
    <a href="https://github.com/vcs-python/libvcs/actions"><img src="https://github.com/vcs-python/libvcs/actions/workflows/tests.yml/badge.svg" alt="Tests status"></a>
    <a href="https://codecov.io/gh/vcs-python/libvcs"><img src="https://codecov.io/gh/vcs-python/libvcs/branch/master/graph/badge.svg" alt="Coverage"></a>
    <a href="https://github.com/vcs-python/libvcs/blob/master/LICENSE"><img src="https://img.shields.io/github/license/vcs-python/libvcs.svg" alt="License"></a>
  </p>
</div>

**libvcs** provides a unified, [typed](https://docs.python.org/3/library/typing.html), and pythonic interface for managing Git, Mercurial, and Subversion repositories. Whether you're building a deployment tool, a developer utility, or just need to clone a repo in a script, libvcs handles the heavy lifting.

It powers [vcspull](https://github.com/vcs-python/vcspull) and simplifies VCS interactions down to a few lines of code.

---

## Features at a Glance

- **🔄 Repository Synchronization**: Clone, update, and manage local repository copies with a high-level API.
- **🛠 Command Abstraction**: Speak fluent `git`, `hg`, and `svn` through fully-typed Python objects.
- **🔗 URL Parsing**: Robustly validate, parse, and manipulate VCS URLs (including SCP-style).
- **🧪 Pytest Fixtures**: Batteries-included fixtures for spinning up temporary repositories in your test suite.

## Installation

```bash
pip install libvcs
```

## Usage

### 1. Synchronize Repositories
Clone and update repositories with a consistent API, regardless of the VCS.

[**Learn more about Synchronization**](https://libvcs.git-pull.com/sync/)

```python
import pathlib
from libvcs.sync.git import GitSync

# Define your repository
repo = GitSync(
    url="https://github.com/vcs-python/libvcs",
    path=pathlib.Path.cwd() / "libvcs",
    remotes={
        'gitlab': 'https://gitlab.com/vcs-python/libvcs'
    }
)

# Clone (if not exists) or fetch & update (if exists)
repo.update_repo()

print(f"Current revision: {repo.get_revision()}")
```

### 2. Command Abstraction
Access the full power of the underlying CLI tools without parsing string output manually.

[**Learn more about Command Abstraction**](https://libvcs.git-pull.com/cmd/)

```python
import pathlib
from libvcs.cmd.git import Git

# Initialize the wrapper
git = Git(path=pathlib.Path.cwd() / 'libvcs')

# Run commands intuitively
git.clone(url='https://github.com/vcs-python/libvcs.git')
git.checkout(ref='master')

# Branch management
git.branches.create('feature/new-gui')
print(git.branches.ls())  # List all branches

# Remote management
git.remotes.set_url(name='origin', url='git@github.com:vcs-python/libvcs.git')

# Tag management
git.tags.create(name='v1.0.0', message='Release version 1.0.0')
```

### 3. URL Parsing
Stop writing regex for Git URLs. Let `libvcs` handle the edge cases.

[**Learn more about URL Parsing**](https://libvcs.git-pull.com/url/)

```python
from libvcs.url.git import GitURL

# Validate URLs
GitURL.is_valid(url='https://github.com/vcs-python/libvcs.git')  # True

# Parse complex URLs
url = GitURL(url='git@github.com:vcs-python/libvcs.git')

print(url.user)      # 'git'
print(url.hostname)  # 'github.com'
print(url.path)      # 'vcs-python/libvcs'

# Transform URLs
url.hostname = 'gitlab.com'
print(url.to_url())  # 'git@gitlab.com:vcs-python/libvcs.git'
```

### 4. Testing with Pytest
Writing a tool that interacts with VCS? Use our fixtures to keep your tests clean and isolated.

[**Learn more about Pytest Fixtures**](https://libvcs.git-pull.com/pytest-plugin.html)

```python
import pathlib
from libvcs.pytest_plugin import CreateRepoPytestFixtureFn
from libvcs.sync.git import GitSync

def test_my_git_tool(
    create_git_remote_repo: CreateRepoPytestFixtureFn,
    tmp_path: pathlib.Path
):
    # Spin up a real, temporary Git server
    git_server = create_git_remote_repo()
    
    # Clone it to a temporary directory
    checkout_path = tmp_path / "checkout"
    repo = GitSync(path=checkout_path, url=f"file://{git_server}")
    repo.obtain()
    
    assert checkout_path.exists()
    assert (checkout_path / ".git").is_dir()
```

## Project Information

- **Python Support**: 3.10+
- **VCS Support**: Git (including AWS CodeCommit), Mercurial (hg), Subversion (svn)
- **License**: MIT

## Links & Resources

- **Documentation**: [libvcs.git-pull.com](https://libvcs.git-pull.com)
- **Source Code**: [github.com/vcs-python/libvcs](https://github.com/vcs-python/libvcs)
- **Issue Tracker**: [GitHub Issues](https://github.com/vcs-python/libvcs/issues)
- **Changelog**: [History](https://libvcs.git-pull.com/history.html)
- **PyPI**: [pypi.org/project/libvcs](https://pypi.org/project/libvcs/)

## Support

Your donations fund development of new features, testing, and support.

- [Donation Options](https://tony.sh/support.html)