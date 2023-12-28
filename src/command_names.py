from __future__ import annotations

from enum import Enum
from typing import Literal


class CommandNames(Enum):
    SHUFFLE = "shuffle"
    PICK = "A"
    START = "start"


# needed for typing, sadly there is no better way to do this correctly:
# https://github.com/python/typing/issues/781
CommandNamesLiteral = Literal[  # type: ignore
    tuple(x.value for x in CommandNames.__members__.values())
]
