# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import pytest

from libvcs.util import mkdir_p


def test_mkdir_p(tmpdir):
    path = tmpdir.join('file').ensure()

    with pytest.raises_regexp(
        Exception, 'Could not create directory %s' % path
    ):
        mkdir_p(str(path))

    # already exists is a noop
    mkdir_p(str(tmpdir))
