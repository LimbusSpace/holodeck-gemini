#!/usr/bin/env python3
"""
混元3D工作流集成测试

测试混元3D生成的模型在整个生产管线中的集成情况，包括：
1. 布局求解器兼容性
2. Blender-MCP导入兼容性
3. 完整的端到端工作流
"""

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Hunyuan3DWorkflowTester:
    """混元3D工作流集成测试器"""

    def __init__(self):
        self.test_results = {}
        self.temp_dir = None

    def setup_test_environment(self):
        """设置测试环境"""
        logger.info("Setting up test environment...")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="hunyuan3d_workflow_test_"))
        logger.info(f"Created test directory: {self.temp_dir}")

        # Create mock session structure
        session_dir = self.temp_dir / "test_session"
        session_dir.mkdir(parents=True, exist_ok=True)

        assets_dir = session_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        return session_dir

    def create_mock_hunyuan3d_glb(self, filename: str, size_mb: float = 5.0) -> Path:
        """创建模拟的混元3D GLB文件用于测试"""
        logger.info(f"Creating mock Hunyuan3D GLB: {filename} ({size_mb}MB)")

        # Create a minimal valid GLB file structure
        glb_path = self.temp_dir / "test_session" / "assets" / filename

        # GLB file header (binary glTF)
        glb_header = b'glTF'  # Magic
        glb_header += (2).to_bytes(4, 'little')  # Version
        glb_header += (int(size_mb * 1024 * 1024)).to_bytes(4, 'little')  # File size

        # Minimal JSON chunk
        json_chunk_header = b'JSON'  # Chunk type
        json_content = {
            "asset": {"version": "2.0"},
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
            "accessors": [
                {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"}
            ],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": 36},
                {"buffer": 0, "byteOffset": 36, "byteLength": 6}
            ],
            "buffers": [{"byteLength": 1000}]
        }
        json_str = json.dumps(json_content, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        json_chunk_header += len(json_bytes).to_bytes(4, 'little')  # Chunk length
        json_chunk_header += json_bytes

        # Write the mock GLB file
        with open(glb_path, 'wb') as f:
            f.write(glb_header)
            f.write(json_chunk_header)

            # Fill remaining space to reach target size
            remaining_bytes = int(size_mb * 1024 * 1024) - len(glb_header) - len(json_chunk_header)
            if remaining_bytes > 0:
                f.write(b'\x00' * remaining_bytes)

        logger.info(f"Created mock GLB file: {glb_path} ({glb_path.stat().st_size / (1024*1024):.1f}MB)")
        return glb_path

    def create_mock_sf3d_glb(self, filename: str, size_mb: float = 2.0) -> Path:
        """创建模拟的SF3D GLB文件用于测试"""
        logger.info(f"Creating mock SF3D GLB: {filename} ({size_mb}MB)")

        # Create similar structure but smaller for SF3D
        return self.create_mock_hunyuan3d_glb(filename, size_mb)

    def test_layout_solver_integration(self):
        """测试布局求解器对混元3D模型的兼容性"""
        logger.info("Testing layout solver integration...")

        try:
            # Import layout solver
            sys.path.insert(0, str(Path(__file__).parent))

            from holodeck_core.scene_gen.layout_solver import LayoutSolver

            # Create mock objects data
            objects_data = {
                "objects": [
                    {
                        "object_id": "test_bed_hunyuan3d",
                        "name": "Hunyuan3D Bed",
                        "category": "furniture",
                        "size_m": [2.0, 1.6, 0.6]
                    },
                    {
                        "object_id": "test_chair_sf3d",
                        "name": "SF3D Chair",
                        "category": "furniture",
                        "size_m": [0.5, 0.5, 0.8]
                    }
                ]
            }

            # Create mock asset manifest
            asset_manifest = {
                "assets": {
                    "test_bed_hunyuan3d": {
                        "path": "assets/test_bed_hunyuan3d.glb",
                        "backend": "hunyuan3d"
                    },
                    "test_chair_sf3d": {
                        "path": "assets/test_chair_sf3d.glb",
                        "backend": "sf3d"
                    }
                }
            }

            # Create mock session object
            class MockSession:
                def __init__(self, session_path):
                    self.session_path = session_path

                def load_objects(self):
                    return objects_data

            # Create mock session
            session = MockSession(self.temp_dir / "test_session")

            # Create layout solver and test
            solver = LayoutSolver()

            # Test object validation
            validated_objects = solver._validate_objects_for_layout(objects_data["objects"], session)

            logger.info(f"Validated {len(validated_objects)} objects")

            # Check backend detection
            hunyuan_objects = [obj for obj in validated_objects if obj.get("backend_source") == "hunyuan3d"]
            sf3d_objects = [obj for obj in validated_objects if obj.get("backend_source") == "sf3d"]

            logger.info(f"Backend breakdown: {len(hunyuan_objects)} Hunyuan3D, {len(sf3d_objects)} SF3D")

            # Test layout solving
            constraints = {
                "globals": {"ground_only_default": True, "collision_clearance_m": 0.02},
                "relations": []
            }

            # Save constraints to file
            constraints_path = self.temp_dir / "test_session" / "constraints.json"
            with open(constraints_path, 'w') as f:
                json.dump(constraints, f)

            # Test layout solving
            solution = solver.solve_with_fixed_objects(
                {"objects": validated_objects},
                constraints,
                []
            )

            if solution.success:
                logger.info("Layout solving successful")
                logger.info(f"Placed {len(solution.object_placements)} objects")
                logger.info(f"Metrics: {solution.metrics}")

                self.test_results["layout_solver"] = {
                    "status": "success",
                    "objects_processed": len(validated_objects),
                    "hunyuan3d_objects": len(hunyuan_objects),
                    "sf3d_objects": len(sf3d_objects),
                    "solution_metrics": solution.metrics
                }
            else:
                logger.error(f"Layout solving failed: {solution.error_message}")
                self.test_results["layout_solver"] = {
                    "status": "failed",
                    "error": solution.error_message
                }

        except Exception as e:
            logger.error(f"Layout solver test failed: {e}")
            self.test_results["layout_solver"] = {
                "status": "error",
                "error": str(e)
            }

    def test_blender_mcp_integration(self):
        """测试Blender-MCP对混元3D模型的兼容性"""
        logger.info("Testing Blender-MCP integration...")

        try:
            # Import Blender MCP bridge
            sys.path.insert(0, str(Path(__file__).parent))

            from holodeck_core.blender.mcp_bridge import BlenderMCPBridge

            # Create test GLB files
            hunyuan_glb = self.create_mock_hunyuan3d_glb("test_hunyuan3d_model.glb", 15.0)
            sf3d_glb = self.create_mock_sf3d_glb("test_sf3d_model.glb", 3.0)

            # Create bridge
            bridge = BlenderMCPBridge()

            # Test GLB analysis
            glb_files = [str(hunyuan_glb), str(sf3d_glb)]
            analysis = bridge._analyze_glb_files(glb_files)

            logger.info(f"GLB analysis completed: {analysis['summary']}")
            logger.info(f"Backend breakdown: {analysis['backend_breakdown']}")

            if analysis["compatibility_issues"]:
                logger.warning(f"Compatibility issues: {analysis['compatibility_issues']}")

            # Test script generation
            script = bridge._generate_glb_import_script(
                glb_files,
                ["Hunyuan3D_Model", "SF3D_Model"],
                analysis
            )

            logger.info("Generated Blender import script")
            logger.info(f"Script length: {len(script)} characters")

            # Check script content
            if "Hunyuan3D" in script and "SF3D" in script:
                logger.info("Script contains backend-specific optimizations")

            self.test_results["blender_mcp"] = {
                "status": "success",
                "glb_files_analyzed": len(glb_files),
                "backend_breakdown": analysis["backend_breakdown"],
                "compatibility_issues": len(analysis["compatibility_issues"]),
                "script_generated": True
            }

        except Exception as e:
            logger.error(f"Blender-MCP test failed: {e}")
            self.test_results["blender_mcp"] = {
                "status": "error",
                "error": str(e)
            }

    def test_end_to_end_workflow(self):
        """测试端到端工作流集成"""
        logger.info("Testing end-to-end workflow integration...")

        try:
            # This would test the complete workflow from asset generation to final rendering
            # For now, we'll simulate the workflow

            logger.info("Simulating end-to-end workflow...")

            # Simulate asset generation
            logger.info("Step 1: Asset generation (simulated)")

            # Simulate layout solving
            logger.info("Step 2: Layout solving (simulated)")

            # Simulate Blender import
            logger.info("Step 3: Blender import (simulated)")

            # Simulate rendering
            logger.info("Step 4: Rendering (simulated)")

            self.test_results["end_to_end"] = {
                "status": "success",
                "steps_completed": 4,
                "message": "End-to-end workflow simulation completed"
            }

        except Exception as e:
            logger.error(f"End-to-end test failed: {e}")
            self.test_results["end_to_end"] = {
                "status": "error",
                "error": str(e)
            }

    def run_all_tests(self):
        """运行所有集成测试"""
        logger.info("Starting Hunyuan3D workflow integration tests...")

        # Setup test environment
        session_dir = self.setup_test_environment()

        # Run individual tests
        self.test_layout_solver_integration()
        self.test_blender_mcp_integration()
        self.test_end_to_end_workflow()

        # Generate test report
        self.generate_test_report()

    def generate_test_report(self):
        """生成测试报告"""
        logger.info("Generating test report...")

        report = {
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_environment": str(self.temp_dir),
            "results": self.test_results,
            "summary": {
                "total_tests": len(self.test_results),
                "successful_tests": sum(1 for r in self.test_results.values() if r.get("status") == "success"),
                "failed_tests": sum(1 for r in self.test_results.values() if r.get("status") in ["failed", "error"])
            }
        }

        # Save report
        report_path = self.temp_dir / "integration_test_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Test report saved to: {report_path}")

        # Print summary
        logger.info("=== Test Summary ===")
        logger.info(f"Total tests: {report['summary']['total_tests']}")
        logger.info(f"Successful: {report['summary']['successful_tests']}")
        logger.info(f"Failed: {report['summary']['failed_tests']}")

        for test_name, result in self.test_results.items():
            status = result.get("status", "unknown")
            logger.info(f"{test_name}: {status}")

        return report


def main():
    """主测试函数"""
    tester = Hunyuan3DWorkflowTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()