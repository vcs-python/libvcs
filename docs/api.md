# API Reference

## Creating a repo object

Helper methods are available in `libvcs.shortcuts` which can return a
repo object from a single entry-point.

`libvcs.shortcuts.create_repo`
`libvcs.shortcuts.create_repo_from_pip_url`

## Instantiating a repo by hand

Tools like `libvcs.shortcuts.create_repo` and
`libvcs.shortcuts.create_repo_from_pip_url` are just wrappers around
instantiated these classes.

See examples below of git, mercurial, and subversion.

## Git

::: libvcs.git.GitRepo

</div>

<div class="autoclass" members="" show-inheritance="">

libvcs.git.GitRemote

</div>

<div class="autofunction">

libvcs.git.extract_status

</div>

## Mercurial

aka `hg(1)`

<div class="autoclass" members="" show-inheritance="">

libvcs.hg.MercurialRepo

</div>

## Subversion

aka `svn(1)`

<div class="autoclass" members="" show-inheritance="">

libvcs.svn.SubversionRepo

</div>

## Adding your own VCS

Extending libvcs can be done through subclassing `BaseRepo`.

<div class="autoclass" members="" show-inheritance="">

libvcs.base.BaseRepo

</div>

## Utility stuff

<div class="automodule" members="">

libvcs.util

</div>
