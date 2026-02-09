"""
Smoke test for Blender integration - basic functionality verification
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest


class BlenderSmokeTest:
    """
    Basic smoke test to verify Blender can execute Python and write files
    """

    def __init__(self):
        self.blender_exe = self._detect_blender()

    def _detect_blender(self) -> Optional[Path]:
        """Detect Blender executable"""
        # Check environment variable first
        env_path = os.environ.get("BLENDER_PATH")
        if env_path:
            blender_path = Path(env_path)
            if blender_path.exists():
                return blender_path

        # Check PATH
        try:
            result = subprocess.run(["blender", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return Path("blender")  # Will be resolved from PATH
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Check common installation paths
        search_paths = [
            Path("C:/Program Files/Blender Foundation/Blender 4.0/blender.exe"),
            Path("C:/Program Files/Blender Foundation/Blender 3.6/blender.exe"),
            Path("C:/Blender/blender-4.0.2/blender.exe"),
            Path("C:/Blender/blender-3.6.0/blender.exe"),
        ]

        for blender_path in search_paths:
            if blender_path.exists():
                return blender_path

        return None

    def run_smoke_test(self) -> dict:
        """Run the complete smoke test"""
        if not self.blender_exe:
            return {
                "status": "FAIL",
                "error": "Blender executable not found",
                "recommendations": [
                    "Install Blender 3.6+ from https://www.blender.org/download/",
                    "Set BLENDER_PATH environment variable",
                    "Add Blender to system PATH"
                ]
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            try:
                # Create a simple test script
                script_content = f'''
import sys
import json
from pathlib import Path

# Basic test - write a simple file
test_dir = Path(r"{test_dir}")
test_file = test_dir / "blender_test.txt"

try:
    import bpy
    blender_available = True
except ImportError:
    blender_available = False

with open(test_file, "w") as f:
    if blender_available:
        f.write(f"Blender version: {{bpy.app.version_string}}\\n")
    else:
        f.write("Blender module not available\\n")
    f.write(f"Python version: {{sys.version}}\\n")

# Write results
results = {{
    "blender_available": blender_available,
    "python_version": sys.version,
    "success": True
}}

if blender_available:
    try:
        # Create a simple object
        bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
        cube = bpy.context.active_object
        results["blender_version"] = bpy.app.version_string
        results["cube_name"] = cube.name if cube else None
    except Exception as e:
        results["blender_error"] = str(e)

with open(test_dir / "smoke_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Smoke test completed successfully!")
'''


                script_path = test_dir / "smoke_test.py"
                with open(script_path, "w") as f:
                    f.write(script_content)

                # Run Blender with test script
                cmd = [str(self.blender_exe), "--background", "--python", str(script_path)]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=str(test_dir)
                )

                # Check results
                results_file = test_dir / "smoke_test_results.json"
                text_file = test_dir / "blender_test.txt"

                if result.returncode == 0 and results_file.exists() and text_file.exists():
                    with open(results_file, "r") as f:
                        test_results = json.load(f)

                    return {
                        "status": "PASS",
                        "blender_executable": str(self.blender_exe),
                        "results": test_results,
                        "stdout": result.stdout
                    }
                else:
                    return {
                        "status": "FAIL",
                        "error": "Blender execution failed or files not created",
                        "return_code": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "files_created": {
                            "results_json": results_file.exists(),
                            "test_txt": text_file.exists()
                        }
                    }

            except subprocess.TimeoutExpired:
                return {
                    "status": "FAIL",
                    "error": "Blender execution timed out (30s)",
                    "blender_executable": str(self.blender_exe)
                }
            except Exception as e:
                return {
                    "status": "FAIL",
                    "error": f"Unexpected error: {str(e)}",
                    "blender_executable": str(self.blender_exe)
                }


@pytest.mark.e2e
@pytest.mark.blender
@pytest.mark.slow
def test_blender_smoke():
    """Smoke test for Blender integration"""
    smoke_test = BlenderSmokeTest()
    results = smoke_test.run_smoke_test()

    # Assertions
    assert results["status"] == "PASS", f"Smoke test failed: {results}"
    assert "results" in results, "No results data returned"
    assert results["results"].get("success") == True, "Blender script reported failure"
    assert results["results"].get("blender_available") == True, "Blender module not available"
    assert results["results"].get("blender_version"), "No Blender version detected"
    assert results["results"].get("cube_name"), "No cube object created"


if __name__ == "__main__":
    # Direct execution for debugging
    smoke_test = BlenderSmokeTest()
    results = smoke_test.run_smoke_test()

    print("\n" + "="*60)
    print("BLENDER SMOKE TEST RESULTS")
    print("="*60)
    print(f"Status: {results['status']}")

    if results["status"] == "PASS":
        print(f"[OK] Blender executable: {results.get('blender_executable')}")
        print(f"[OK] Blender available: {results['results'].get('blender_available')}")
        if results['results'].get('blender_version'):
            print(f"[OK] Blender version: {results['results'].get('blender_version')}")
        print(f"[OK] Python version: {results['results'].get('python_version')}")
        if results['results'].get('cube_name'):
            print(f"[OK] Created object: {results['results'].get('cube_name')}")
        print("\n[SUCCESS] All basic Blender functionality verified!")
    else:
        print(f"[FAIL] Error: {results.get('error')}")
        if "stderr" in results:
            print(f"Stderr: {results['stderr']}")
        if "recommendations" in results:
            print("\nRecommendations:")
            for rec in results["recommendations"]:
                print(f"  - {rec}")
