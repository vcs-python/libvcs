(quickstart)=

# Quickstart

## Installation

For latest official version:

```console
$ pip install --user libvcs
```

Upgrading:

```console
$ pip install --user --upgrade libvcs
```

(developmental-releases)=

### Developmental releases

New versions of libvcs are published to PyPI as alpha, beta, or release candidates. In their
versions, you will see notations like `a1`, `b1`, and `rc1`, respectively. For example, `1.10.0b4` would mean
the 4th beta release of `1.10.0` before general availability.

Installation options:

- Via pip (pre-release versions):

  ```console
  $ pip install --user --upgrade --pre libvcs
  ```

- Via trunk (development version, may be unstable):

  ```console
  $ pip install --user -e git+https://github.com/vcs-python/libvcs.git#egg=libvcs
  ```

[pip]: https://pip.pypa.io/en/stable/
