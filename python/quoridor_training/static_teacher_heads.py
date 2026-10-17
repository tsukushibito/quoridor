"""The two fixed static heads using canonical existing model bodies.

No Search/MCTS, loss, scale, sign conversion, warmup or feature change. Normal
entry owns immutable model/source refs, actual device resources and whole caps.
"""

import importlib.util
from pathlib import Path
import time

import numpy as np


class StaticHead:
    def __init__(self, kind, model_path, *, device, batch_rows, max_attempted_rows):
        if (
            kind not in ("sigma", "claustrophobia")
            or device not in ("cpu", "cuda:0")
            or type(batch_rows) is not int
            or not 0 < batch_rows <= 4096
            or type(max_attempted_rows) is not int
            or max_attempted_rows <= 0
        ):
            raise ValueError("explicit fixed teacher/device and finite batch/row limits")
        import torch

        self.kind, self.device = kind, device
        self.batch_rows, self.row_limit = batch_rows, max_attempted_rows
        self.attempted = self.returned = self.failed_attempted_rows = self.calls = 0
        self.constructor_model_calls = 0
        self.seconds = 0.0
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.use_deterministic_algorithms(True)
        if kind == "sigma":
            # The already maintained graph/weights/value formula is the sole
            # body. New batched runtime still requires its finite actual parity.
            path = Path(__file__).resolve().parents[2] / "tools/model-export/folded_sigma.py"
            spec = importlib.util.spec_from_file_location("quoridor_fixed_sigma_body", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.model = module.load(model_path)
        else:
            self.model = torch.jit.load(str(model_path), map_location="cpu")
        original_dtypes = sorted({str(p.dtype) for p in self.model.parameters()})
        self.model = self.model.eval().float().to(device)
        if any(p.is_floating_point() and p.dtype != torch.float32 for p in self.model.parameters()):
            raise ValueError("canonical teacher FP32 parameters required")
        self.runtime = {
            "torch": torch.__version__,
            "original_parameter_dtypes": original_dtypes,
            "device": device,
            "fp32": True,
            "autocast": False,
            "tf32": False,
            "constructor_model_calls": self.constructor_model_calls,
            "value": "raw-local-stm-single-network-post-tanh",
            "batch_parity": "requires actual separately bound new-runtime evidence",
        }

    def __call__(self, inputs):
        import torch

        x = np.asarray(inputs)
        channels = 8 if self.kind == "sigma" else 20
        if (
            x.dtype != np.dtype("float32")
            or x.ndim != 4
            or x.shape[1:] != (channels, 9, 9)
            or not x.flags.c_contiguous
            or not 0 < len(x) <= self.batch_rows
            or not np.isfinite(x).all()
        ):
            raise ValueError("bounded contiguous finite FP32 canonical input")
        if self.attempted + len(x) > self.row_limit:
            raise ValueError("inclusive attempted teacher row budget exhausted")
        self.attempted += len(x)
        self.calls += 1
        started = time.monotonic()
        try:
            with torch.inference_mode():
                policy, value, *_ = self.model(torch.from_numpy(x).to(self.device))
                policy_width = 136 if self.kind == "sigma" else 209
                if (
                    policy.dtype != torch.float32
                    or policy.shape != (len(x), policy_width)
                    or value.dtype != torch.float32
                    or value.shape != (len(x), 1)
                    or not torch.isfinite(policy).all()
                ):
                    raise ValueError("canonical joint policy/value result shape/dtype")
                values = value.detach().cpu().numpy().reshape(-1).copy()
            if not np.isfinite(values).all() or np.any(np.abs(values) > 1):
                raise ValueError("finite raw post-tanh scalar in [-1,1] required")
            self.returned += len(x)
            return values
        except BaseException:
            self.failed_attempted_rows += len(x)
            raise
        finally:
            self.seconds += time.monotonic() - started

    def facts(self):
        return {
            **self.runtime,
            "calls_attempted": self.calls,
            "logical_rows_attempted": self.attempted,
            "finite_rows_returned": self.returned,
            "failed_attempted_rows": self.failed_attempted_rows,
            "failed_kernel_execution_rows": "UNKNOWN without actual profiling",
            "head_seconds": self.seconds,
        }
