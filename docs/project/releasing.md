(releasing)=

# Releasing

Use this page to prepare release notes, the release commit, tags, and publish
fallback commands. Keep release notes accurate before running any publish step.

## Version policy

libvcs is pre-1.0. Any minor bump (e.g. 0.39 to 0.40) **may** contain
breaking changes. Patch bumps (0.39.0 to 0.39.1) are reserved for
bug-fixes and documentation.

## Checklist

1. Ensure {ref}`CHANGES <history>` lists every merged PR since the last tag.
   Credit contributors by [GitHub] handle.

2. Update the version in `src/libvcs/__about__.py` **and**
   `pyproject.toml`.

3. Commit and tag:

   ```console
   $ git commit -m 'Tag v0.39.1'
   ```

   ```console
   $ git tag v0.39.1
   ```

4. Push the commit and tag -- CI will publish to [PyPI] automatically:

   ```console
   $ git push && git push --tags
   ```

## Manual publish (fallback)

```console
$ uv build
```

```console
$ uv publish
```

[GitHub]: https://github.com/vcs-python/libvcs
[PyPI]: https://pypi.org/project/libvcs/
