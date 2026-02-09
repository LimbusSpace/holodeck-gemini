"""
Simple integration test for factory architecture
"""

import unittest
from unittest.mock import patch

from holodeck_core.clients.factory import LLMClientFactory
from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer


class TestFactoryIntegration(unittest.TestCase):
    """Simple integration test to verify factory architecture works"""

    def test_factory_initialization(self):
        """Test that factory can be initialized"""
        factory = LLMClientFactory()
        self.assertIsNotNone(factory)

    def test_unified_vlm_registration(self):
        """Test that unified_vlm is registered in factory"""
        factory = LLMClientFactory()
        available_clients = factory.get_available_clients()

        # unified_vlm should be available
        self.assertIn('unified_vlm', available_clients)

    def test_scene_analyzer_factory_mode(self):
        """Test SceneAnalyzer factory mode initialization"""
        analyzer = SceneAnalyzer(use_factory=True)
        self.assertTrue(analyzer.use_factory)

    def test_priority_order(self):
        """Test that unified_vlm is in priority order"""
        factory = LLMClientFactory()
        priority_order = factory._priority_order

        # unified_vlm should be first in priority
        self.assertEqual(priority_order[0], "unified_vlm")

    def test_feature_support(self):
        """Test VLM feature support"""
        factory = LLMClientFactory()

        # Test that VLM supports required features
        supports_vision = factory._supports_features("unified_vlm", ["vision"])
        supports_object_extraction = factory._supports_features("unified_vlm", ["object_extraction"])

        self.assertTrue(supports_vision)
        self.assertTrue(supports_object_extraction)


if __name__ == '__main__':
    unittest.main()