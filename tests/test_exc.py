"""tests for libvcs exceptions."""

from __future__ import annotations

import pytest

from libvcs import exc


def test_command_error() -> None:
    """Test CommandError exception."""
    command = None
    with pytest.raises(exc.CommandError) as e:
        returncode = 0
        command = ["command", "arg"]
        msg = "this is output"
        raise exc.CommandError(msg, returncode, command)

    assert command is not None

    assert e.value.cmd == " ".join(command)
    assert (
        str(e.value)
        == exc.CommandError.message.format(
            returncode=e.value.returncode,
            cmd=e.value.cmd,
        )
        + f"\n{e.value.output}"
    )

    with pytest.raises(exc.CommandError) as e:
        returncode = 0
        command = ["command", "arg"]
        msg = ""
        raise exc.CommandError(msg, returncode, command)
    assert e.value.cmd == " ".join(command)
    assert str(e.value) == exc.CommandError.message.format(
        returncode=e.value.returncode,
        cmd=e.value.cmd,
    )

    command_2 = None

    with pytest.raises(exc.CommandError) as e:
        command_2 = "command arg"
        msg = "this is output"
        raise exc.CommandError(msg, 0, command_2)

    assert command_2 is not None
    assert e.value.cmd == command_2
