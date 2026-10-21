"""One bounded upstream MCTS call, owned/reaped by the common arena worker.

The pinned native callback library owns upstream replay, encode20, legal mask,
canonical policy and original sequential run_mcts. This module owns the existing
FP32 TorchScript head only. No Sigma encoding/search, game loop or fallback.
"""

import argparse
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import threading

UPSTREAM = "ae093653e62ad700e201706fa5ed767093d0d68e"
MAX_REQUEST = 65536


def validate(request):
    fields = {"prefix", "legal", "simulations", "c_puct", "max_head_calls", "library", "model"}
    if set(request) != fields:
        raise ValueError("exact Claustrophobia request fields")
    for name in ("prefix", "legal"):
        values = request[name]
        if not isinstance(values, list) or any(
            type(a) is not int or not 0 <= a < 209 for a in values
        ):
            raise ValueError("absolute209 ordered prefix/legal IDs")
    if (
        len(request["prefix"]) > 65535
        or not request["legal"]
        or len(set(request["legal"])) != len(request["legal"])
    ):
        raise ValueError("bounded prefix and nonempty unique legal set")
    if (
        type(request["simulations"]) is not int
        or not 0 <= request["simulations"] <= 2**32 - 1
        or type(request["max_head_calls"]) is not int
        or not 0 < request["max_head_calls"] < 2**64
        or type(request["c_puct"]) not in (int, float)
        or not math.isfinite(request["c_puct"])
        or request["c_puct"] <= 0
        or any(not Path(request[k]).is_absolute() for k in ("library", "model"))
    ):
        raise ValueError("explicit finite upstream budget and owned absolute assets")
    return request


class Output(C.Structure):
    _fields_ = [
        ("abi", C.c_uint32),
        ("action", C.c_uint32),
        ("simulations", C.c_uint32),
        ("head_calls", C.c_uint64),
        ("root_value", C.c_float),
        ("legal_absolute", C.c_uint8 * 209),
    ]


def checked_result(request, *, action, simulations, calls, value, legal):
    if (
        type(simulations) is not int
        or type(calls) is not int
        or (action is not None and type(action) is not int)
        or type(value) not in (int, float)
        or sorted(legal) != sorted(request["legal"])
        or simulations != request["simulations"]
        or not 0 < calls <= request["max_head_calls"]
        or not math.isfinite(value)
        or abs(value) > 1
        or (simulations > 0 and action not in legal)
        or (simulations == 0 and action is not None)
    ):
        raise ValueError("upstream result/root legality/budget mismatch; no partial success")
    return {
        "upstream": UPSTREAM,
        "entry": "mcts::run_mcts",
        "action": action,
        "simulations": simulations,
        "head_calls": calls,
        "root_value_stm": value,
        "inner_history": "upstream board-only; common arena owns full-prefix threefold adjudication",
        "nodes": None,
        "search_value": None,
    }


def execution_point():
    """Self-observed process/thread/CPU points, not configured or continuous CPU claims."""
    libc = C.CDLL(None, use_errno=True)
    libc.sched_getcpu.argtypes = []
    libc.sched_getcpu.restype = C.c_int
    core = libc.sched_getcpu()
    if core < 0:
        error = C.get_errno()
        raise OSError(error, os.strerror(error))
    return {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "tid": threading.get_native_id(),
        "core": core,
        "affinity": sorted(os.sched_getaffinity(0)),
    }


def run(request):
    validate(request)  # Before importing/loading any ML/native asset.
    execution_started = execution_point()
    import numpy as np
    import torch

    from .static_teacher_heads import StaticHead

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    library = C.CDLL(request["library"])
    library.quoridor_claustrophobia_commit_v1.restype = C.c_char_p
    if library.quoridor_claustrophobia_commit_v1().decode("ascii") != UPSTREAM:
        raise ValueError("fixed upstream source identity")
    head = None  # Native root/prefix/legal correspondence precedes model load.
    failures = []
    callback_type = C.CFUNCTYPE(
        C.c_int,
        C.c_void_p,
        C.POINTER(C.c_float),
        C.POINTER(C.c_uint8),
        C.POINTER(C.c_float),
        C.POINTER(C.c_float),
    )

    @callback_type
    def forward(_user, tensor, mask, policy, value):
        nonlocal head
        try:
            if head is None:
                head = StaticHead(
                    "claustrophobia",
                    request["model"],
                    device="cpu",
                    batch_rows=1,
                    max_attempted_rows=request["max_head_calls"],
                )
            inputs = np.ctypeslib.as_array(tensor, shape=(1620,)).reshape(1, 20, 9, 9).copy()
            allowed = np.ctypeslib.as_array(mask, shape=(209,)).astype(bool)
            logits, scalar = head.policy_value(inputs)
            # Same CPU FP32 mask-before-softmax policy as upstream nn.rs.
            probabilities = torch.softmax(
                torch.from_numpy(logits[0]).masked_fill(~torch.from_numpy(allowed), -torch.inf),
                dim=0,
            ).numpy()
            np.ctypeslib.as_array(policy, shape=(209,))[:] = probabilities
            value[0] = float(scalar[0])
            return 0
        except BaseException as error:
            failures.append(error)
            return 1  # Never let ctypes swallow an exception and return garbage.

    call = library.quoridor_claustrophobia_search_v1
    call.argtypes = [
        C.POINTER(C.c_uint16),
        C.c_size_t,
        C.c_uint32,
        C.c_double,
        C.c_uint64,
        C.POINTER(C.c_uint8),
        callback_type,
        C.c_void_p,
        C.POINTER(Output),
    ]
    call.restype = C.c_int
    prefix = (C.c_uint16 * max(1, len(request["prefix"])))(*request["prefix"])
    expected_legal = (C.c_uint8 * 209)(*[int(a in request["legal"]) for a in range(209)])
    output = Output()
    code = call(
        prefix,
        len(request["prefix"]),
        request["simulations"],
        request["c_puct"],
        request["max_head_calls"],
        expected_legal,
        forward,
        None,
        C.byref(output),
    )
    if failures:
        error = BaseExceptionGroup("original Claustrophobia head errors", failures)
        if head is not None:
            error.add_note(
                "available head facts (not a completed search): " + json.dumps(head.facts())
            )
        raise error
    if code != 0 or output.abi != 1:
        error = ValueError(f"upstream call refused/failed: {code}")
        if head is not None:
            error.add_note(
                "available head facts (not a completed search): " + json.dumps(head.facts())
            )
        raise error
    if head is None or head.facts()["logical_rows_attempted"] != output.head_calls:
        raise ValueError("native callback and actual joint-head attempt counts disagree")
    result = checked_result(
        request,
        action=None if output.action == 2**32 - 1 else output.action,
        simulations=output.simulations,
        calls=output.head_calls,
        value=output.root_value,
        legal=[a for a, enabled in enumerate(output.legal_absolute) if enabled],
    )
    result["head"] = head.facts()
    try:
        execution_returned = execution_point()
    except BaseException as error:
        error.add_note("available upstream facts, ownership incomplete: " + json.dumps(result))
        raise
    result["execution"] = {"started": execution_started, "returned": execution_returned}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--request", type=Path, help="absolute bounded request file")
    sources.add_argument(
        "--stdin", action="store_true", help="read the arena request from stdin (default)"
    )
    parser.add_argument("--request-sha256", help="SHA256 of the exact request file bytes")
    args = parser.parse_args()
    if (args.request is None) != (args.request_sha256 is None):
        parser.error("--request and --request-sha256 are required together")
    if args.request is not None and (
        not args.request.is_absolute()
        or len(args.request_sha256) != 64
        or any(c not in "0123456789abcdef" for c in args.request_sha256)
    ):
        parser.error("absolute request path and lowercase SHA256 required")
    raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
    if len(raw) > MAX_REQUEST:
        raise ValueError("bounded request")
    if args.request is not None:
        if raw:
            raise ValueError("file and stdin requests are mutually exclusive")
        # Guardian file requests have empty stdin. Nonblocking/no-follow open
        # refuses special files without waiting for a pipe or loading any asset.
        with open(
            args.request,
            "rb",
            opener=lambda path, flags: os.open(path, flags | os.O_NONBLOCK | os.O_NOFOLLOW),
        ) as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("regular request file required")
            raw = stream.read(MAX_REQUEST + 1)
        if len(raw) > MAX_REQUEST:
            raise ValueError("bounded request")
        if hashlib.sha256(raw).hexdigest() != args.request_sha256:
            raise ValueError("request SHA256 mismatch")
    result = run(json.loads(raw))
    print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
