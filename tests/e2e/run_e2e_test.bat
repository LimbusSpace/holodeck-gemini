@echo off

REM Holodeck 端到端验收测试脚本 (Windows版本)
REM 验证完整的 build 流程：CLI → Layout → 标准文件格式

echo 🚀 开始 Holodeck 端到端验收测试
echo ==================================================

REM 检查Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python 未安装
    exit /b 1
)

REM 运行测试
echo 🧪 运行端到端测试...
python tests/e2e_test.py

if %ERRORLEVEL% EQU 0 (
    echo 🎉 端到端测试通过！
    echo.
    echo 📊 测试结果摘要:
    if exist "test_report.json" (
        echo ✅ 测试报告已生成
        echo.
        echo 📋 报告内容:
        python -c "
import json
with open('test_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)
print(f'测试状态: {report["status"]}')
print(f'Session ID: {report["session_id"]}')
print(f'对象数量: {report["artifacts"]["layout_solution"]["objects_count"]}')
print(f'资产数量: {report["artifacts"]["asset_manifest"]["assets_count"]}')
print(f'完成阶段: {",".join(report["cli_output_summary"]["stages_completed"])}')
"
    )
    echo.
    echo 📁 产物文件:
    echo   - layout_solution_v1.json (对象布局)
    echo   - asset_manifest.json (资产清单)
    echo   - blender_object_map.json (对象映射)
    echo   - test_report.json (测试报告)
    exit /b 0
) else (
    echo ❌ 端到端测试失败
    if exist "test_report.json" (
        echo 📝 查看 test_report.json 获取详细信息
    )
    exit /b 1
)