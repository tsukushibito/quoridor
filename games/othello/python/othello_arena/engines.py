"""GTP adapters for the pinned official external builds."""

import re
import time

from . import coordinate, move_index
from .protocol import EngineError


class GTP:
    def __init__(self, process, *, engine, time_ms=1000):
        if engine not in ("edax", "egaroucid"):
            raise ValueError("unknown external engine")
        self.process = process
        self.engine = engine
        self.time_ms = time_ms
        self.sequence = 0

    def command(self, command, *, deadline):
        self.sequence += 1
        tag = str(self.sequence)
        self.process.send(f"{tag} {command}", deadline)
        while True:
            line = self.process.line(deadline)
            if line.startswith(("=", "?")):
                break
        match = re.fullmatch(r"([=?])\s*(\d+)\s*(.*)", line)
        if not match or match[2] != tag:
            raise EngineError("protocol", f"GTP response ID mismatch: {line!r}")
        parts = [match[3]]
        while (line := self.process.line(deadline)) != "":
            parts.append(line)
        if match[1] == "?":
            raise EngineError("protocol", "GTP error: " + "\n".join(parts))
        return "\n".join(parts).strip()

    def reset(self, *, deadline):
        self.command("clear_board", deadline=deadline)
        if self.engine == "edax":
            if self.time_ms != 1000:
                raise ValueError("Edax initial GTP clock supports the pinned 1s profile only")
            # Edax uses main_time as options.time even in its per-move mode.
            # A positive stone count selects that mode; 0 1 1 would budget 0ms.
            self.command("time_settings 1 0 1", deadline=deadline)

    def observe(self, side, move, *, deadline):
        color = "black" if side == 1 else "white"
        square = "pass" if move is None else coordinate(move)
        self.command(f"play {color} {square}", deadline=deadline)

    def prepare(self, state, *, deadline):
        if self.engine == "edax":
            color = "black" if state["toMove"] == 1 else "white"
            self.command(f"time_left {color} 1 1", deadline=deadline)

    def choose(self, state, *, deadline):
        color = "black" if state["toMove"] == 1 else "white"
        response = self.command(f"genmove {color}", deadline=deadline)
        try:
            return move_index(response)
        except ValueError as error:
            raise EngineError("protocol", str(error)) from error


class NativePlayer:
    def __init__(self, native, *, simple=False, time_ms=1000, tt_mib=32):
        self.native = native
        self.simple = simple
        self.time_ms = time_ms
        self.tt_mib = tt_mib

    def reset(self, *, deadline):
        pass

    def observe(self, side, move, *, deadline):
        pass

    def prepare(self, state, *, deadline):
        pass

    def choose(self, state, *, deadline):
        move = self.native.choose(
            state, deadline=deadline, simple=self.simple, time_ms=self.time_ms, tt_mib=self.tt_mib
        )
        self.last_search = self.native.last_response
        return move


class EgaroucidFixedTime:
    """Pinned Console7.8.1 engine + external fixed-time adapter, separate from GTP."""

    def __init__(self, process):
        self.process = process

    def reset(self, *, deadline):
        self.process.json_request({"op": "reset"}, deadline=deadline)

    def observe(self, side, move, *, deadline):
        pass

    def prepare(self, state, *, deadline):
        pass

    def search_response(self, state, *, deadline):
        result = self.process.json_request(
            {"op": "search", "state": state, "timeMs": 1000}, deadline=deadline
        )
        self.last_search = result
        if "move" not in result:
            raise EngineError("protocol", "fixed-time adapter omitted move")
        return result

    def choose(self, state, *, deadline):
        return self.search_response(state, deadline=deadline)["move"]


def io_deadline(seconds=5):
    """Protocol setup/transfer envelope, independent of scientific thinking budget."""
    return time.monotonic() + seconds
