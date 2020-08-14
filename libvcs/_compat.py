# flake8: NOQA
import sys

_identity = lambda x: x
implements_to_string = _identity

console_encoding = sys.__stdout__.encoding


def console_to_str(s):
    """ From pypa/pip project, pip.backwardwardcompat. License MIT. """
    try:
        return s.decode(console_encoding)
    except UnicodeDecodeError:
        return s.decode('utf_8')
    except AttributeError:  # for tests, #13
        return s
