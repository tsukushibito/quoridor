"""Persistent bounded protocol I/O, inside the existing CycleResources job family."""

from collections import deque
import json
import os
from pathlib import Path
import selectors
import subprocess
import time


class EngineError(RuntimeError):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class Process:
    """Own one direct child; the outer execute guardian owns its descendants."""

    def __init__(self, argv, *, cwd, log, cancelled=lambda: False, limit=65536):
        if not argv or len(argv) > 64 or any(len(str(x)) > 4096 for x in argv):
            raise ValueError("bounded argv required")
        self.log = Path(log)
        self.cancelled = cancelled
        self.limit = limit
        self.tail = bytearray()
        self.bytes_seen = 0
        self.buffer = bytearray()
        self.lines = deque()
        self.selector = selectors.DefaultSelector()
        self.child = subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.closed = False
        self.stdout_eof = False
        self.cleanup = None
        for stream in (self.child.stdin, self.child.stdout, self.child.stderr):
            os.set_blocking(stream.fileno(), False)
        self.selector.register(self.child.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(self.child.stderr, selectors.EVENT_READ, "stderr")

    def _record(self, direction, data):
        self.bytes_seen += len(data)
        self.tail.extend(direction.encode() + b": " + data)
        del self.tail[: max(0, len(self.tail) - self.limit)]

    def _check(self, deadline):
        if self.cancelled():
            raise EngineError("cancelled", "arena cancellation requested")
        if time.monotonic() >= deadline:
            raise EngineError("timeout", "protocol wall deadline")

    def _pump(self, deadline):
        self._check(deadline)
        writable = False
        for key, _ in self.selector.select(min(0.05, max(0, deadline - time.monotonic()))):
            if key.data == "stdin":
                writable = True
                continue
            data = os.read(key.fd, 16384)
            self._record(key.data, data)
            if not data:
                self.selector.unregister(key.fileobj)
                if key.data == "stdout":
                    self.stdout_eof = True
                continue
            if key.data == "stdout":
                self.buffer.extend(data)
                while b"\n" in self.buffer:
                    line, _, rest = self.buffer.partition(b"\n")
                    self.buffer[:] = rest
                    self.lines.append(line.decode("utf-8", errors="replace").rstrip("\r"))
                if (
                    len(self.buffer) > self.limit
                    or len(self.lines) > 1024
                    or sum(len(x) + 1 for x in self.lines) > self.limit
                ):
                    raise EngineError("protocol", "stdout frame/queue exceeds bound")
        return writable

    def send(self, line, deadline):
        data = (line + "\n").encode()
        if len(data) > self.limit:
            raise EngineError("protocol", "request exceeds bound")
        self._record("stdin", data)
        self.selector.register(self.child.stdin, selectors.EVENT_WRITE, "stdin")
        try:
            while data:
                if self._pump(deadline):
                    try:
                        n = os.write(self.child.stdin.fileno(), data)
                    except BrokenPipeError as error:
                        raise EngineError("crash", "engine closed stdin") from error
                    data = data[n:]
        finally:
            self.selector.unregister(self.child.stdin)

    def line(self, deadline):
        while not self.lines:
            self._pump(deadline)
            if self.stdout_eof and not self.lines:
                code = self.child.poll()
                raise EngineError(
                    "crash" if code not in (None, 0) else "eof", f"stdout EOF; exit={code}"
                )
        self._check(deadline)
        return self.lines.popleft()

    def json_request(self, payload, *, deadline):
        self.send(json.dumps(payload, separators=(",", ":")), deadline)
        try:
            result = json.loads(self.line(deadline))
        except ValueError as error:
            raise EngineError("protocol", "invalid JSONL response") from error
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise EngineError("protocol", f"JSONL request failed: {result}")
        return result

    def close(self):
        if self.closed:
            return
        self.closed = True
        errors = []
        exited_before_close = self.child.poll() is not None
        try:
            if self.child.poll() is None:
                self.child.terminate()
                try:
                    self.child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.child.kill()
            self.child.wait(timeout=3)
        except BaseException as error:
            errors.append(str(error))
        finally:
            # A reply may arrive before stderr is fully drained. Preserve the
            # remaining kernel-buffered tail without waiting on descendants.
            until = time.monotonic() + 1
            for name, stream in (("stdout", self.child.stdout), ("stderr", self.child.stderr)):
                try:
                    while time.monotonic() < until:
                        try:
                            data = os.read(stream.fileno(), 16384)
                        except BlockingIOError:
                            break
                        if not data:
                            break
                        self._record(name, data)
                except OSError as error:
                    errors.append(str(error))
            for stream in (self.child.stdin, self.child.stdout, self.child.stderr):
                try:
                    stream.close()
                except BaseException as error:
                    errors.append(str(error))
            self.selector.close()
            self.log.write_bytes(self.tail)
            self.cleanup = {
                "exitCode": self.child.returncode,
                "unexpectedExit": exited_before_close and self.child.returncode not in (None, 0),
                "directReaped": self.child.returncode is not None,
                "bytesSeen": self.bytes_seen,
                "bytesRetained": len(self.tail),
                "errors": errors,
            }
            self.log.with_suffix(self.log.suffix + ".json").write_text(
                json.dumps(self.cleanup) + "\n"
            )
        if errors:
            raise EngineError("cleanup", "; ".join(errors))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class Native:
    def __init__(self, process):
        self.process = process

    def request(self, op, *, deadline, **fields):
        result = self.process.json_request(dict(op=op, **fields), deadline=deadline)
        key = (
            "status"
            if op == "status"
            else "move"
            if op in ("search", "simple")
            else "score"
            if op == "evaluate"
            else "state"
        )
        if key not in result:
            raise EngineError("protocol", f"native response missing {key}")
        if key == "status" and (
            not isinstance(result[key], dict)
            or not {"terminal", "mustPass", "legalMoves", "black", "white"} <= result[key].keys()
        ):
            raise EngineError("protocol", "invalid native status")
        if key == "state" and (
            not isinstance(result[key], dict)
            or not {"board", "toMove", "version"} <= result[key].keys()
        ):
            raise EngineError("protocol", "invalid native state")
        self.last_response = result
        return result

    def choose(self, state, *, deadline, simple=False, time_ms=1000, tt_mib=32):
        request = {"state": state}
        if not simple:
            request.update(timeMs=time_ms, ttMiB=tt_mib, maxDepth=64, exactEmpties=12)
        return self.request("simple" if simple else "search", deadline=deadline, **request)["move"]
