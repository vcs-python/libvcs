# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest

from libvcs import GitRepo, MercurialRepo, SubversionRepo
from libvcs.shortcuts import create_repo_from_pip_url
from libvcs.exc import InvalidPipURL


@pytest.mark.parametrize('repo_dict,repo_class,raises_exception', [
    ({
        'url': 'git+https://github.com/freebsd/freebsd.git',
        'name': 'hi'
     }, GitRepo, False,),
    ({
        'url': 'hg+https://bitbucket.org/birkenfeld/sphinx',
        'name': 'hi'
     }, MercurialRepo, False,),
    ({
        'url': 'svn+http://svn.code.sf.net/p/docutils/code/trunk',
        'name': 'hi'
     }, SubversionRepo, False,),
    ({
        'url': 'sv+http://svn.code.sf.net/p/docutils/code/trunk',
        'name': 'hi'
     }, None, InvalidPipURL,),
])
def test_create_repo_from_pip_url(
    repo_dict, repo_class, raises_exception,
    tmpdir
):
    repo_dict['parent_dir'] = str(tmpdir)  # add parent_dir via fixture

    if raises_exception:
        with pytest.raises(raises_exception):
            create_repo_from_pip_url(**repo_dict)
    else:
        repo = create_repo_from_pip_url(**repo_dict)
        assert isinstance(repo, repo_class)
