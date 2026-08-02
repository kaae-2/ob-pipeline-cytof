from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from benchmark_config import find_module, find_stage, load_config  # noqa: E402
import validate_benchmark_config as validator  # noqa: E402


class FinalMetricsPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_path = ROOT / 'Clustering_conda-reviewer-final.yml'
        self.config = load_config(self.config_path)

    def assert_rejected(self, parameters: list[dict[str, list[str]]]) -> None:
        config = deepcopy(self.config)
        metrics_stage = find_stage(config, 'metrics')
        find_module(metrics_stage, 'flow_metrics')['parameters'] = parameters
        real_load_config = validator.load_config

        def load_with_rejected_metrics(path: str | Path) -> dict:
            if Path(path).name == validator.FINAL_CONFIG:
                return config
            return real_load_config(path)

        with patch.object(
            validator,
            'load_config',
            side_effect=load_with_rejected_metrics,
        ):
            errors = validator.validate(self.config_path)

        self.assertTrue(
            any('final reviewer metrics must request exactly' in item for item in errors)
        )

    def test_final_config_requests_exactly_the_approved_metrics(self) -> None:
        metrics = find_module(find_stage(self.config, 'metrics'), 'flow_metrics')

        self.assertEqual(metrics['parameters'], validator.final_metrics_parameters())
        self.assertEqual(
            validator.FINAL_METRICS,
            ('accuracy', 'precision', 'recall', 'balanced_accuracy', 'f1'),
        )
        self.assertNotIn('mutual_information', metrics['parameters'][0]['values'][1])
        self.assertEqual(validator.validate(self.config_path), [])

    def test_default_empty_and_all_metric_requests_are_rejected(self) -> None:
        rejected = (
            [],
            [{'values': ['--metric', '']}],
            [{'values': ['--metric', 'all']}],
        )

        for parameters in rejected:
            with self.subTest(parameters=parameters):
                self.assert_rejected(parameters)

    def test_mutual_information_metric_request_is_rejected(self) -> None:
        self.assert_rejected(
            [
                {
                    'values': [
                        '--metric',
                        'accuracy,precision,recall,balanced_accuracy,f1,mutual_information',
                    ]
                }
            ]
        )


if __name__ == '__main__':
    unittest.main()
