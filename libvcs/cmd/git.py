import pathlib


class Git:
    def __init__(self, dir: pathlib.Path):
        self.dir: pathlib.Path = dir
