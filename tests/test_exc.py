"""tests for libvcs exceptions."""
import pytest

from libvcs import exc


def test_command_error():
    with pytest.raises(exc.CommandError) as e:
        returncode = 0
        command = ["command", "arg"]
        raise exc.CommandError("this is output", returncode, command)
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

    with pytest.raises(exc.CommandError) as e:
        command = "command arg"
        raise exc.CommandError("this is output", 0, command)
    assert e.value.cmd == command


def test_invalid_pip_url():
    with pytest.raises(exc.InvalidPipURL) as e:
        raise exc.InvalidPipURL("http://github.com/wrong/format")
    assert str(e.value) == e.value.message
