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


class FinalSplitAuditPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_path = ROOT / 'Clustering_conda-reviewer-final.yml'
        self.config = load_config(self.config_path)

    def validate_modified(self, config: dict) -> list[str]:
        real_load_config = validator.load_config

        def load_config_override(path: str | Path) -> dict:
            if Path(path).name == validator.FINAL_CONFIG:
                return config
            return real_load_config(path)

        with patch.object(
            validator,
            'load_config',
            side_effect=load_config_override,
        ):
            return validator.validate(self.config_path)

    def test_final_config_pins_and_declares_canonical_split_audit(self) -> None:
        preprocessing = find_stage(self.config, 'preprocessing')
        stratify = find_stage(self.config, 'stratify')
        analysis = find_stage(self.config, 'analysis')

        self.assertEqual(
            find_module(preprocessing, 'data_preprocessing')['repository']['commit'],
            validator.PREPROCESSING_COMMIT,
        )
        self.assertEqual(
            find_module(stratify, 'data_stratify')['repository']['commit'],
            validator.STRATIFY_COMMIT,
        )
        self.assertIn(validator.PREPROCESSING_AUDIT_OUTPUT, preprocessing['outputs'])
        self.assertIn(validator.STRATIFY_AUDIT_OUTPUT, stratify['outputs'])
        self.assertEqual(
            analysis['inputs'],
            [
                {
                    'entries': [
                        'data.train_matrix',
                        'data.train_labels',
                        'data.test_matrix',
                        'data.metadata',
                    ]
                }
            ],
        )
        self.assertEqual(validator.validate(self.config_path), [])

    def test_stale_pins_and_missing_audit_outputs_are_rejected(self) -> None:
        config = deepcopy(self.config)
        preprocessing = find_stage(config, 'preprocessing')
        stratify = find_stage(config, 'stratify')
        find_module(preprocessing, 'data_preprocessing')['repository']['commit'] = '7ef034f'
        stratify['outputs'].remove(validator.STRATIFY_AUDIT_OUTPUT)

        errors = self.validate_modified(config)

        self.assertTrue(any('final preprocessing must be pinned' in item for item in errors))
        self.assertIn('final stratify must declare data.split_audit', errors)

    def test_dedicated_audit_does_not_change_model_inputs(self) -> None:
        config = deepcopy(self.config)
        find_stage(config, 'analysis')['inputs'][0]['entries'].append('data.split_audit')

        errors = self.validate_modified(config)

        self.assertTrue(any('final model inputs must remain unchanged' in item for item in errors))


if __name__ == '__main__':
    unittest.main()
