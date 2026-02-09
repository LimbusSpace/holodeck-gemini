#!/usr/bin/env python3

import os
import sys
import time
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

# 手动加载.env文件
dotenv_path = Path('.env')
if dotenv_path.exists():
    with open(dotenv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

print('环境变量加载完成')

# 导入必要的模块
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

def debug_hunyuan_api():
    """调试混元图像API"""
    print('开始调试混元图像API...')

    # 创建客户端
    cred = credential.Credential(
        os.getenv('HUNYUAN_SECRET_ID'),
        os.getenv('HUNYUAN_SECRET_KEY')
    )

    httpProfile = HttpProfile()
    httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = hunyuan_client.HunyuanClient(cred, "ap-guangzhou", clientProfile)

    # 提交生成任务
    import json
    req_submit = models.SubmitHunyuanImageJobRequest()
    params = {
        "Prompt": "一只可爱的小猫",
        "Resolution": "1024:1024",
        "Model": "hunyuan-pro"
    }
    req_submit.from_json_string(json.dumps(params))

    print('提交生成任务...')
    resp_submit = client.SubmitHunyuanImageJob(req_submit)
    job_id = resp_submit.JobId
    print(f'任务提交成功! JobId: {job_id}')

    # 轮询查询状态
    print('开始轮询任务状态...')
    for i in range(20):  # 最多查询20次
        try:
            req_query = models.QueryHunyuanImageJobRequest()
            req_query.JobId = job_id
            resp_query = client.QueryHunyuanImageJob(req_query)

            # 打印所有属性
            print(f'\n--- 查询 #{i+1} ---')
            print(f'JobId: {job_id}')

            # 检查所有可能的属性
            attrs = ['JobStatusCode', 'JobStatusMsg', 'ResultImage', 'JobErrorCode', 'JobErrorMsg']
            for attr in attrs:
                if hasattr(resp_query, attr):
                    value = getattr(resp_query, attr)
                    print(f'{attr}: {value}')

            # 检查状态码
            if hasattr(resp_query, 'JobStatusCode'):
                status_code = resp_query.JobStatusCode
                print(f'状态码: {status_code} (类型: {type(status_code)})')

                # 根据不同状态码处理
                if status_code == 2:
                    print('✅ 任务完成!')
                    if hasattr(resp_query, 'ResultImage') and resp_query.ResultImage:
                        print(f'图像URL: {resp_query.ResultImage}')
                    break
                elif status_code == 3:
                    print('❌ 任务失败!')
                    if hasattr(resp_query, 'JobErrorMsg'):
                        print(f'错误信息: {resp_query.JobErrorMsg}')
                    break
                else:
                    print(f'任务进行中，状态码: {status_code}')

            time.sleep(3)  # 等待3秒

        except Exception as e:
            print(f'查询错误: {e}')
            time.sleep(3)

if __name__ == "__main__":
    debug_hunyuan_api()