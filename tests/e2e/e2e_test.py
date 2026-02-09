#!/usr/bin/env python3
"""
Holodeck 端到端验收测试脚本

这个脚本验证完整的 build 流程：
1. 运行 holodeck CLI 生成到 layout 阶段
2. 验证标准输出文件格式
3. 模拟 Blender apply 操作
4. 生成测试报告
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class E2ETester:
    def __init__(self, project_root: str ="."):
        self.project_root = Path(project_root)
        self.workspace_dir = self.project_root / "workspace" / "sessions"
        self.test_prompt = "一个空房间，里面有一个立方体桌子"
        self.session_id = None
        self.results = {}

    def run_cli_build(self) -> bool:
        """运行 holodeck build 命令"""
        print("🧪 步骤 1: 运行 holodeck build...")

        cmd = [
            "python", "-m", "holodeck_cli.cli",
            "build", self.test_prompt,
            "--until", "layout",
            "--no-blendermcp",
            "--json"
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                print(f"❌ CLI 执行失败: {result.stderr}")
                return False

            # 解析 JSON 输出
            try:
                cli_output = json.loads(result.stdout)
                self.results["cli_output"] = cli_output

                if not cli_output.get("ok", False):
                    print(f"❌ CLI 返回错误: {cli_output.get('error', 'Unknown error')}")
                    return False

                self.session_id = cli_output.get("session_id")
                print(f"✅ CLI 执行成功，session_id: {self.session_id}")
                return True

            except json.JSONDecodeError as e:
                print(f"❌ 无法解析 CLI JSON 输出: {e}")
                print(f"原始输出: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ CLI 执行超时")
            return False
        except Exception as e:
            print(f"❌ CLI 执行异常: {e}")
            return False

    def verify_session_files(self) -> bool:
        """验证 session 目录和文件"""
        if not self.session_id:
            print("❌ 没有有效的 session_id")
            return False

        print("🧪 步骤 2: 验证 session 文件...")

        session_dir = self.workspace_dir / self.session_id
        if not session_dir.exists():
            print(f"❌ session 目录不存在: {session_dir}")
            return False

        # 检查必需文件
        required_files = [
            "layout_solution_v1.json",
            "asset_manifest.json",
            "blender_object_map.json",
            "objects.json",
            "constraints_v1.json"
        ]

        for filename in required_files:
            filepath = session_dir / filename
            if not filepath.exists():
                print(f"❌ 必需文件不存在: {filename}")
                return False
            print(f"✅ 文件存在: {filename}")

        self.results["session_dir"] = str(session_dir)
        return True

    def verify_layout_solution_format(self) -> bool:
        """验证 layout_solution.json 格式"""
        print("🧪 步骤 3: 验证 layout_solution.json 格式...")

        session_dir = Path(self.results["session_dir"])
        layout_file = session_dir / "layout_solution_v1.json"

        try:
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)

            # 验证必需字段
            required_fields = ["success", "object_placements", "version"]
            for field in required_fields:
                if field not in layout_data:
                    print(f"❌ layout_solution 缺少必需字段: {field}")
                    return False

            # 验证 object_placements 格式
            object_placements = layout_data["object_placements"]
            if not isinstance(object_placements, dict):
                print("❌ object_placements 应该是字典")
                return False

            for obj_id, placement in object_placements.items():
                required_placement_fields = ["pos", "rot_euler", "scale"]
                for field in required_placement_fields:
                    if field not in placement:
                        print(f"❌ 对象 {obj_id} 缺少字段: {field}")
                        return False

                # 验证数值格式
                for field in ["pos", "rot_euler", "scale"]:
                    if not isinstance(placement[field], list) or len(placement[field]) != 3:
                        print(f"❌ 对象 {obj_id} 的 {field} 格式错误")
                        return False

            print(f"✅ layout_solution.json 格式正确，包含 {len(object_placements)} 个对象")
            self.results["layout_data"] = layout_data
            return True

        except Exception as e:
            print(f"❌ 验证 layout_solution.json 失败: {e}")
            return False

    def verify_asset_manifest_format(self) -> bool:
        """验证 asset_manifest.json 格式"""
        print("🧪 步骤 4: 验证 asset_manifest.json 格式...")

        session_dir = Path(self.results["session_dir"])
        manifest_file = session_dir / "asset_manifest.json"

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            # 验证必需字段
            required_fields = ["version", "assets", "total_assets", "total_size_mb"]
            for field in required_fields:
                if field not in manifest_data:
                    print(f"❌ asset_manifest 缺少必需字段: {field}")
                    return False

            # 验证 assets 格式
            assets = manifest_data["assets"]
            if not isinstance(assets, dict):
                print("❌ assets 应该是字典")
                return False

            for asset_id, asset_info in assets.items():
                required_asset_fields = ["asset_path", "format", "size_bytes", "checksum", "metadata"]
                for field in required_asset_fields:
                    if field not in asset_info:
                        print(f"❌ 资产 {asset_id} 缺少字段: {field}")
                        return False

            print(f"✅ asset_manifest.json 格式正确，包含 {len(assets)} 个资产")
            self.results["manifest_data"] = manifest_data
            return True

        except Exception as e:
            print(f"❌ 验证 asset_manifest.json 失败: {e}")
            return False

    def verify_blender_object_map_format(self) -> bool:
        """验证 blender_object_map.json 格式"""
        print("🧪 步骤 5: 验证 blender_object_map.json 格式...")

        session_dir = Path(self.results["session_dir"])
        map_file = session_dir / "blender_object_map.json"

        try:
            with open(map_file, 'r', encoding='utf-8') as f:
                map_data = json.load(f)

            # 验证必需字段
            required_fields = ["naming_convention", "description", "mapping"]
            for field in required_fields:
                if field not in map_data:
                    print(f"❌ blender_object_map 缺少必需字段: {field}")
                    return False

            # 验证命名约定
            if map_data["naming_convention"] != "object_name_equals_id":
                print(f"❌ 不支持的命名约定: {map_data['naming_convention']}")
                return False

            # 验证映射
            mapping = map_data["mapping"]
            if not isinstance(mapping, dict):
                print("❌ mapping 应该是字典")
                return False

            print(f"✅ blender_object_map.json 格式正确")
            self.results["map_data"] = map_data
            return True

        except Exception as e:
            print(f"❌ 验证 blender_object_map.json 失败: {e}")
            return False

    def generate_blender_apply_script(self) -> str:
        """生成 Blender apply 脚本示例"""
        print("🧪 步骤 6: 生成 Blender apply 脚本示例...")

        script_content = '''
# Blender Apply Script (通用脚本)
# 这个脚本可以从任何 Holodeck session 读取标准文件并应用场景

import bpy
import json
import os

def apply_holodeck_session(session_path):
    """应用 Holodeck session 到当前 Blender 场景"""

    # 1. 读取 asset_manifest.json
    manifest_path = os.path.join(session_path, "asset_manifest.json")
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # 2. 读取 layout_solution_v1.json
    layout_path = os.path.join(session_path, "layout_solution_v1.json")
    with open(layout_path, 'r') as f:
        layout = json.load(f)

    # 3. 读取 blender_object_map.json
    map_path = os.path.join(session_path, "blender_object_map.json")
    with open(map_path, 'r') as f:
        obj_map = json.load(f)

    # 4. 导入资产并应用布局
    for object_id, placement in layout["object_placements"].items():
        asset_info = manifest["assets"].get(object_id)
        if asset_info:
            # 导入资产
            asset_path = os.path.join(session_path, asset_info["asset_path"])
            bpy.ops.import_scene.gltf(filepath=asset_path)

            # 获取导入的对象（最新导入的对象）
            imported_obj = bpy.context.selected_objects[-1]

            # 设置对象名称（遵循命名约定）
            imported_obj.name = object_id

            # 应用位置、旋转、缩放
            imported_obj.location = placement["pos"]
            imported_obj.rotation_euler = placement["rot_euler"]
            imported_obj.scale = placement["scale"]

    print(f"✅ 成功应用 {len(layout["object_placements"])} 个对象")

# 使用示例
# session_path = "workspace/sessions/your_session_id"
# apply_holodeck_session(session_path)
'''

        self.results["blender_script"] = script_content
        print("✅ 生成 Blender apply 脚本示例")
        return script_content

    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        print("🧪 步骤 7: 生成测试报告...")

        report = {
            "test_name": "Holodeck E2E Build Test",
            "test_prompt": self.test_prompt,
            "session_id": self.session_id,
            "session_path": self.results.get("session_dir"),
            "timestamp": subprocess.check_output(["date", "-Iseconds"]).decode().strip() if os.name != 'nt' else "N/A",
            "status": "PASSED" if all([
                "cli_output" in self.results,
                "session_dir" in self.results,
                "layout_data" in self.results,
                "manifest_data" in self.results,
                "map_data" in self.results
            ]) else "FAILED",
            "artifacts": {
                "layout_solution": {
                    "file": "layout_solution_v1.json",
                    "objects_count": len(self.results.get("layout_data", {}).get("object_placements", {})),
                    "success": self.results.get("layout_data", {}).get("success", False)
                },
                "asset_manifest": {
                    "file": "asset_manifest.json",
                    "assets_count": len(self.results.get("manifest_data", {}).get("assets", {})),
                    "total_size_mb": self.results.get("manifest_data", {}).get("total_size_mb", 0)
                },
                "blender_object_map": {
                    "file": "blender_object_map.json",
                    "naming_convention": self.results.get("map_data", {}).get("naming_convention", "N/A")
                }
            },
            "cli_output_summary": {
                "ok": self.results.get("cli_output", {}).get("ok", False),
                "stages_completed": self.results.get("cli_output", {}).get("stages_completed", []),
                "message": self.results.get("cli_output", {}).get("message", "N/A")
            }
        }

        # 保存报告
        report_file = self.project_root / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ 测试报告已保存: {report_file}")
        return report

    def run_full_test(self) -> bool:
        """运行完整测试"""
        print("🚀 开始 Holodeck 端到端验收测试")
        print("=" * 50)

        steps = [
            ("CLI Build", self.run_cli_build),
            ("Session Files", self.verify_session_files),
            ("Layout Solution", self.verify_layout_solution_format),
            ("Asset Manifest", self.verify_asset_manifest_format),
            ("Blender Object Map", self.verify_blender_object_map_format),
        ]

        all_passed = True
        for step_name, step_func in steps:
            try:
                if not step_func():
                    print(f"❌ {step_name} 步骤失败")
                    all_passed = False
                    break
                else:
                    print(f"✅ {step_name} 步骤通过")
            except Exception as e:
                print(f"❌ {step_name} 步骤异常: {e}")
                all_passed = False
                break

        # 生成脚本和报告（即使前面步骤失败也尝试生成）
        try:
            self.generate_blender_apply_script()
            report = self.generate_test_report()

            print("=" * 50)
            if all_passed:
                print("🎉 端到端测试通过！")
                print(f"📁 Session: {self.session_id}")
                print(f"📊 对象数量: {report['artifacts']['layout_solution']['objects_count']}")
                print(f"📦 资产数量: {report['artifacts']['asset_manifest']['assets_count']}")
                print(f"📝 报告文件: test_report.json")
            else:
                print("❌ 端到端测试失败")
                print(f"📝 报告文件: test_report.json")

        except Exception as e:
            print(f"❌ 生成报告失败: {e}")
            all_passed = False

        return all_passed


if __name__ == "__main__":
    # 运行测试
    tester = E2ETester()
    success = tester.run_full_test()

    # 退出码
    sys.exit(0 if success else 1)