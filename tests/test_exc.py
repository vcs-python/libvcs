"""tests for libvcs exceptions."""
import pytest

from libvcs import exc


def test_command_error() -> None:
    command = None
    with pytest.raises(exc.CommandError) as e:
        returncode = 0
        command = ["command", "arg"]
        raise exc.CommandError("this is output", returncode, command)

    assert command is not None

    assert e.value.cmd == " ".join(command)
    assert (
        str(e.value)
        == exc.CommandError.message.format(
            returncode=e.value.returncode, cmd=e.value.cmd
        )
        + "\n%s" % e.value.output
    )

    with pytest.raises(exc.CommandError) as e:
        returncode = 0
        command = ["command", "arg"]
        raise exc.CommandError("", returncode, command)
    assert e.value.cmd == " ".join(command)
    assert str(e.value) == exc.CommandError.message.format(
        returncode=e.value.returncode, cmd=e.value.cmd
    )

    command_2 = None

    with pytest.raises(exc.CommandError) as e:
        command_2 = "command arg"
        raise exc.CommandError("this is output", 0, command_2)

    assert command_2 is not None
    assert e.value.cmd == command_2
