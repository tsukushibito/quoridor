"""Configuration proposals only; no training, statistics fit, or model import."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/nnue-training'))
from common import resolve_config

POINTS = [0, 1, 2, 5, 10, 20, 50, 100, 200, 400, 800, 1200, 1600, 2000]


def configuration(stage_train_rows, validation_rows, scale_path, scale_sha256):
    if type(stage_train_rows) is not int or stage_train_rows <= 0 or type(validation_rows) is not int or validation_rows <= 0:
        raise ValueError('nonempty qualified train/validation required')
    cfg = resolve_config(overrides=[
        'optimizer.lr=0.0001', 'optimizer.weight_decay=0', 'training.steps=2000',
        'training.batch_size=128', 'training.seed=19080311', 'training.sampling="game"',
        'training.target="rootmean"', 'training.threads=1', 'training.device="cpu"',
        'evaluation.interval=100', 'evaluation.early_stopping_patience=0',
        'data.overlap_policy="report"', 'limits.seconds=120',
        'limits.samples=' + str(256000 + len(POINTS) * (stage_train_rows + validation_rows))])
    # Shared CLI has interval evaluation and raw distances. These are deliberately
    # separate from supported config keys, not falsely passed to shared trainer.
    settings = {'proposal_only': True, 'model_training_connected': False,
                'evaluation_points': POINTS, 'train_samples': 256000,
                'evaluation_sample_upper': len(POINTS) * (stage_train_rows + validation_rows),
                'distance_scale': {'path': scale_path, 'sha256': scale_sha256,
                                   'rule': 'fixed old train-only population moments; no refit',
                                   'initial_function': 'h distance columns *= sigma; bias += original columns @ mu'},
                'future_required': ['private dense-point observer', 'initial-function-preserving scale adapter/evaluator binding'],
                'baseline': ['same initial', 'stage train-only gameequal constant', 'stage train-only distance WLS'],
                'statistics_partitions': ['train'], 'test_selection': False}
    return cfg, settings
