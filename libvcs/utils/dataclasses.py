import dataclasses
from operator import attrgetter


class SkipDefaultFieldsReprMixin:
    def __repr__(self):
        """Skip default fields.

        Credit: Pietro Oldrati, 2022-05-08, Unilicense

        See also: https://stackoverflow.com/a/72161437/1396928
        """
        nodef_f_vals = (
            (f.name, attrgetter(f.name)(self))
            for f in dataclasses.fields(self)
            if attrgetter(f.name)(self) != f.default
        )

        nodef_f_repr = ",".join(f"{name}={value}" for name, value in nodef_f_vals)
        return f"{self.__class__.__name__}({nodef_f_repr})"
