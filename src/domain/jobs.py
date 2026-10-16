"""Worker failures carry only safe recovery context across the execution boundary."""


class TemporaryWorkFailure(Exception):
    def __init__(self, *, source_validated: bool = False) -> None:
        self.source_validated = source_validated
