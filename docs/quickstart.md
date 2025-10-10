(quickstart)=

# Quickstart

## Installation

For the latest official version:

```console
$ python -m pip install libvcs
```

Upgrading to the latest version:

```console
$ python -m pip install --upgrade libvcs
```

(developmental-releases)=

### Developmental releases

New versions of libvcs are published to PyPI as alpha, beta, or release candidates. These versions
are marked with notations like `a1`, `b1`, and `rc1`, respectively. For example, `1.10.0b4` indicates
the 4th beta release of version `1.10.0` before its general availability.

Installation options:

- Via pip (pre-release versions):

  ```console
  $ python -m pip install --upgrade --pre libvcs
  ```

- Via trunk (development version, may be unstable):

  ```console
  $ python -m pip install -e git+https://github.com/vcs-python/libvcs.git#egg=libvcs
  ```

[pip]: https://pip.pypa.io/en/stable/
