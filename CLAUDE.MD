## 分支同步指南

### 分支结构
- `master`: 主分支，Claude Code 版本
- `feature/gemini-cli-adaptation`: Gemini CLI 适配分支

### 开发工作流

**在 master 上开发后同步到 gemini 分支：**
```bash
# 1. 切换到 gemini 分支
git checkout feature/gemini-cli-adaptation

# 2. 合并 master 的更新
git merge master

# 3. 推送
git push origin feature/gemini-cli-adaptation

# 4. 切回 master 继续开发
git checkout master
```

**在 gemini 分支上开发后同步到 master：**
```bash
# 1. 切换到 master
git checkout master

# 2. 合并 gemini 分支的更新
git merge feature/gemini-cli-adaptation

# 3. 推送
git push origin master
```

**快速同步命令（单行）：**
```bash
# master → gemini
git checkout feature/gemini-cli-adaptation && git merge master && git push && git checkout master
```

---

--until 工作原理

  1. CLI 入口 (holodeck_cli/cli.py:178)

  holodeck-build --text "场景描述" --until extract

  2. 管道阶段定义 (factory.py:43-50)

  stages = [
      ("scene_ref", SceneRefStage(...)),    # 生成参考图
      ("extract", ExtractStage(...)),        # 解析物体属性
      ("cards", CardsStage(...)),            # 生成单物体图像
      ("constraints", ConstraintsStage(...)),# 空间约束生成
      ("layout", LayoutStage(...)),          # DFS 布局求解
      ("assets", AssetsStage(...)),          # 3D 资产生成
  ]

  3. 截断逻辑 (factory.py:52-55)

  for name, stage in stages:
      runner.add_stage(stage)
      if until and name == until:
          break  # 遇到目标阶段后停止添加后续阶段

  可用的 until 值
  ┌─────────────┬────────────────┬────────────────┐
  │     值      │     停止点     │      输出      │
  ├─────────────┼────────────────┼────────────────┤
  │ scene_ref   │ 参考图生成后   │ 参考图像       │
  ├─────────────┼────────────────┼────────────────┤
  │ extract     │ 物体解析后     │ 物体属性 JSON  │
  ├─────────────┼────────────────┼────────────────┤
  │ cards       │ 单物体图生成后 │ 各物体独立图像 │
  ├─────────────┼────────────────┼────────────────┤
  │ constraints │ 约束生成后     │ 空间约束 JSON  │
  ├─────────────┼────────────────┼────────────────┤
  │ layout      │ 布局求解后     │ 物体最终位置   │
  ├─────────────┼────────────────┼────────────────┤
  │ assets      │ 完整流程       │ 3D 资产        │
  └─────────────┴────────────────┴────────────────┘
  使用示例

  # 只生成参考图
  holodeck-build --text "一个现代客厅" --until scene_ref

  # 生成到物体解析
  holodeck-build --text "一个现代客厅" --until extract

  # 生成到约束（不执行 DFS 和 3D 生成）
  holodeck-build --text "一个现代客厅" --until constraints

  这个设计允许调试和验证管道的中间结果，无需等待完整流程完成。



# 论文中的提示词构建体系

## 整体提示词流水线

```
                        提示词流水线全景
                        
Text Input (用户输入)
    │
    ▼
┌─────────────────────┐
│ Prompt 1: 生成参考图 │ → GPT-Image-1 → 参考图像
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 2: 解析物体   │ → GPT-o3 → 物体属性 JSON
│   (文本 + 参考图)     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 3: 生成单物体图│ → GPT-Image-1 → 各物体的独立图像
│   (参考图 + 物体名)   │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 4: 质量控制   │ → GPT-o3 → 冗余图像列表
│   (所有物体图像)      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 5: 背景提取   │ → GPT-Image-1 → 地面纹理
│   (参考图)            │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 6: 空间约束   │ → GPT-o3 → 约束 JSON
│   (文本+参考图+物体)  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Prompt 7: 约束修正   │ → GPT-o3 → 更新的约束 JSON
│   (失败反馈+旧约束)   │ (仅在 DFS 失败时触发)
└─────────────────────┘
```

---

## Prompt 1：生成场景参考图

### 论文原文（补充材料第12页）

```python
prompt = (
    f"{description}. Render in {style} style. "
    f"3-D view: x->right, y->backward, z->up. "
    "Well-lit, no extra objects."
)
```

### 解构分析

```
┌──────────────────────────────────────────────────────┐
│                    Prompt 结构                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│  {description}                    ← 用户原始输入      │
│  ──────────────                                      │
│  50-300 词的场景描述                                   │
│  例: "A cozy living room features a plush,            │
│       L-shaped sectional sofa adorned with            │
│       colorful throw pillows..."                      │
│                                                      │
│  Render in {style} style.         ← 风格指定          │
│  ────────────────────────                             │
│  realistic / cartoon / anime / cyberpunk / ...        │
│                                                      │
│  3-D view: x->right, y->backward, z->up.             │
│  ────────────────────────────────────                 │
│  ← 坐标系约束：确保生成的图像视角一致                    │
│     右手坐标系                                        │
│     后续 VLM 解析位置时依赖这个视角                     │
│                                                      │
│  Well-lit, no extra objects.      ← 质量约束          │
│  ───────────────────────                              │
│  ← 确保光照充足（方便后续分析）                         │
│  ← 不要添加描述外的物体（防止幻觉）                     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 设计意图

```
这个 prompt 故意非常简洁，原因：

1. GPT-Image-1 对过长提示词会丢失细节
2. 用户描述本身已经 50-300 词，信息量足够
3. 额外约束只加了三条：风格、视角、光照
4. 视角约束 "3-D view: x->right, y->backward, z->up" 是关键
   → 后续 GPT-o3 解析位置时，需要知道图像的坐标系方向
```

---

## Prompt 2：解析物体属性

### 论文原文（补充材料第12页）

```python
INSTRUCTION = (
    "You will receive a scene description and a style. "
    "Your task is to divide the scene into several objects and "
    "provide their positions, rotations, sizes, and visual "
    "descriptions in JSON format.\n\n"
    
    "Your output must be only valid JSON matching this schema:\n\n"
    f"{json.dumps(SCHEMA_JSON, indent=2)}\n\n"
    
    "Please follow these coordinate system specifications:\n"
    "- Use a right-handed coordinate system\n"
    "- The origin (0,0,0) is at the centre of the floor/ground\n"
    "- +X = right, +Y = backward, +Z = up (metres)\n\n"
    
    "The size values should be in range [0.1, 5] metres.\n\n"
    
    "Focus on the main objects in the scene, "
    "do not include too many small details.\n\n"
    
    "Do not include background elements (e.g., walls, windows, "
    "ceilings, floors, sky, rivers, grass, roads, terrain, "
    "curtains) in the items list.\n\n"
    
    "Each entry in the items list must correspond to a complete "
    "object (e.g. a building, a sculpture)--"
    "do not split out parts or components (e.g., handles, "
    "pillars, windows, knobs, etc.) as separate objects.\n\n"
    
    "_No extra commentary or Markdown--just the JSON text._\n\n"
)
```

### 解构分析

```
┌───────────────────────────────────────────────────────────────┐
│                       Prompt 结构（7 层）                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  Layer 1: 任务定义                                             │
│  ─────────────────                                            │
│  "divide the scene into several objects"                      │
│  "provide positions, rotations, sizes, visual descriptions"   │
│  → 明确输出四个维度                                            │
│                                                               │
│  Layer 2: 输出格式                                             │
│  ─────────────────                                            │
│  "valid JSON matching this schema"                            │
│  → 给出完整的 Pydantic schema                                 │
│  → 结构化输出，避免解析错误                                     │
│                                                               │
│  Layer 3: 坐标系定义                                           │
│  ─────────────────                                            │
│  "right-handed coordinate system"                             │
│  "origin at centre of floor"                                  │
│  "+X = right, +Y = backward, +Z = up"                        │
│  → 与参考图的视角对齐                                          │
│  → 物理世界的真实单位（米）                                     │
│                                                               │
│  Layer 4: 数值约束                                             │
│  ─────────────────                                            │
│  "size values in range [0.1, 5] metres"                       │
│  → 防止生成不合理的尺寸                                        │
│  → 0.1m 以下太小（杯子把手级别）                               │
│  → 5m 以上太大（通常是建筑结构）                                │
│                                                               │
│  Layer 5: 粒度控制                                             │
│  ─────────────────                                            │
│  "Focus on main objects"                                      │
│  "do not include too many small details"                      │
│  → 避免物体数量爆炸                                            │
│  → 一个场景通常 10-15 个主要物体                               │
│                                                               │
│  Layer 6: 排除规则                                             │
│  ─────────────────                                            │
│  排除背景：walls, windows, ceilings, floors, sky,             │
│           rivers, grass, roads, terrain, curtains             │
│  排除零件：handles, pillars, windows, knobs                   │
│  → 背景由单独的 background prompt 处理                        │
│  → 零件应该是完整物体的一部分                                   │
│                                                               │
│  Layer 7: 格式限制                                             │
│  ─────────────────                                            │
│  "No extra commentary or Markdown--just JSON"                 │
│  → 防止模型输出 ```json 包裹或解释文字                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 输入构成

```python
# 这个 prompt 接收两种输入

messages = [
    {
        "role": "system",
        "content": INSTRUCTION        # 上面的 prompt
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": description    # 用户的场景描述文本
            },
            {
                "type": "image",
                "image": reference_image  # Prompt 1 生成的参考图
            }
        ]
    }
]

# 关键：文本 + 图像 双输入
# 文本提供语义信息
# 图像提供空间位置信息
# GPT-o3 综合两者推断每个物体的 3D 位置
```

### 输出示例

```json
{
    "items": [
        {
            "id": "bed1",
            "name": "King Bed",
            "position": {"x": 0.0, "y": 1.0, "z": 0.4},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            "size": {"x": 1.92, "y": 1.94, "z": 1.2},
            "visual_description": "A king-sized bed with a light-beige upholstered headboard, dressed in a white duvet and multiple decorative pillows."
        },
        {
            "id": "nightstand_right",
            "name": "Right Nightstand",
            "position": {"x": 1.2, "y": 1.0, "z": 0.35},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            "size": {"x": 0.52, "y": 0.95, "z": 0.6},
            "visual_description": "A matching light-wood minimalist nightstand with one drawer and open lower shelf."
        }
    ]
}
```

---

## Prompt 3：生成单物体图像

### 论文原文（补充材料第13页）

```python
prompt = (
    f"Please generate ONE PNG image of an isolated front-view {obj_name} "
    f"with a transparent background, in {style} style, "
    f"with shapes and style similar to the reference scene. "
)
```

### 解构分析

```
┌───────────────────────────────────────────────────────────┐
│                    Prompt 结构（5 个约束）                  │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  "ONE PNG image"                                          │
│  ────────────────                                         │
│  ← 数量约束：只生成一张图                                  │
│  ← 格式约束：PNG（支持透明通道）                            │
│                                                           │
│  "isolated front-view {obj_name}"                         │
│  ────────────────────────────────                          │
│  ← 隔离约束：只有这一个物体，没有其他东西                    │
│  ← 视角约束：正面视图                                      │
│     Hunyuan3D 对正面视图的重建质量最好                      │
│  ← 物体名称：从 Prompt 2 的 JSON 中提取                    │
│                                                           │
│  "transparent background"                                 │
│  ──────────────────────                                    │
│  ← 背景约束：透明背景                                      │
│     这对 Image-to-3D 至关重要                              │
│     Hunyuan3D 会把背景当作物体的一部分来重建                 │
│                                                           │
│  "in {style} style"                                       │
│  ──────────────────                                        │
│  ← 风格约束：与场景整体风格一致                             │
│     这是论文的核心创新之一                                  │
│     所有物体图像用同一个 style 生成                         │
│     → 3D 资产风格自然一致                                  │
│                                                           │
│  "with shapes and style similar to the reference scene"   │
│  ──────────────────────────────────────────────────        │
│  ← 一致性约束：形状和风格要与参考图中的对应物体一致          │
│     GPT-Image-1 会参考输入的参考图                          │
│     确保单物体图与参考图中同一物体的外观匹配                 │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 输入构成

```python
# 输入：参考图像 + 物体名称

response = client.images.generate(
    model="gpt-image-1",
    prompt=prompt,                  # 上面的 prompt
    image=reference_image,          # Prompt 1 生成的参考图
    size="1024x1024",
    quality="high"
)

# 关键：参考图作为 image 输入
# GPT-Image-1 会从参考图中理解该物体长什么样
# 然后生成一个隔离的、透明背景的版本
```

### 为什么不用图像分割

```
论文第4页的解释：

方案 A（分割）: 参考图 → SAM/Grounded-SAM → 裁剪出每个物体
  问题：
  - 分割不准确（边界模糊）
  - 被遮挡的物体无法完整提取
  - 裁剪后的图像背景杂乱

方案 B（重新生成）: 参考图 + 物体名 → GPT-Image-1 → 全新的单物体图
  优势：
  - 完整的正面视图（无遮挡）
  - 干净的透明背景
  - 风格与参考图一致
  - 质量稳定可控
```

---

## Prompt 4：质量控制（去重）

### 论文原文（补充材料第13页）

```python
system_msg = {
    "role": "system",
    "content": "You are a helpful assistant that identifies "
               "redundant sub-components in a set of images."
}

instruction = (
    f"I have the following list of image filenames:\n"
    f"{json.dumps(png_files, indent=2)}\n"
    "Here are all images in the current scene. "
    "Some represent smaller parts already "
    "contained within larger assemblies. "
    "Return a JSON list of filenames (with '.png') "
    "that should be deleted as redundant sub-components, "
    f"matching this schema:\n"
    f"{json.dumps(SCHEMA_JSON, indent=2)}\n\n"
)
```

### 解构分析

```
┌───────────────────────────────────────────────────────────┐
│                    解决什么问题？                           │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  场景描述："A bathtub with a faucet and a towel rack"      │
│                                                           │
│  Prompt 2 解析出：                                         │
│    - bathtub (浴缸)                                       │
│    - faucet (水龙头)                                      │
│    - towel_rack (毛巾架)                                  │
│                                                           │
│  Prompt 3 为每个物体生成图像：                              │
│    - bathtub.png  ← 浴缸图像中已经包含了水龙头              │
│    - faucet.png   ← 单独的水龙头图像（冗余！）             │
│    - towel_rack.png                                       │
│                                                           │
│  如果不去重：                                              │
│    Hunyuan3D 会生成两个水龙头                              │
│    场景中出现一个浴缸（带水龙头）+ 一个独立水龙头           │
│                                                           │
│  Prompt 4 的任务：                                         │
│    输入所有物体图像 → 识别冗余 → 返回要删除的文件名         │
│    输出：{"filenames": ["faucet.png"]}                     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 输入构成

```python
messages = [
    system_msg,          # 角色定义
    {
        "role": "user",
        "content": [
            {"type": "text", "text": instruction},
            # 所有物体图像作为视觉输入
            {"type": "image", "path": "bathtub.png"},
            {"type": "image", "path": "faucet.png"},
            {"type": "image", "path": "towel_rack.png"},
            # ...
        ]
    }
]

# GPT-o3 会看所有图像
# 判断哪些小物体已经包含在大物体图像中
# 返回应该删除的文件列表
```

---

## Prompt 5：背景提取

### 论文原文（补充材料第13页）

```python
prompt = (
    "Replace the entire image with ONE seamless, tileable PNG "
    "of the main floor for indoor scenes, and the main ground "
    "for outdoor scenes. "
    "Using the material and pattern seen in the input photo. "
    "Ignore walls, ceiling and decorations. "
    "The texture must be homogeneous, repeating smoothly, "
    "and produced at a scale large enough to cover an "
    "expansive floor area. Do not add transparency."
)
```

### 解构分析

```
┌───────────────────────────────────────────────────────────┐
│                    Prompt 结构                             │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  "ONE seamless, tileable PNG"                             │
│  ──────────────────────────                               │
│  ← 无缝可平铺：作为地面纹理需要能无限重复                   │
│                                                           │
│  "main floor for indoor / main ground for outdoor"        │
│  ──────────────────────────────────────────────            │
│  ← 区分室内（地板）和室外（地面）                           │
│                                                           │
│  "Using the material and pattern seen in the input"       │
│  ──────────────────────────────────────────────────        │
│  ← 从参考图中提取材质和图案                                │
│     木地板 → 木纹纹理                                     │
│     鹅卵石 → 石头纹理                                     │
│     草地 → 草地纹理                                       │
│                                                           │
│  "Ignore walls, ceiling and decorations"                  │
│  ──────────────────────────────────────                    │
│  ← 只关注地面，忽略其他元素                                │
│                                                           │
│  "homogeneous, repeating smoothly"                        │
│  ──────────────────────────────                            │
│  ← 均匀一致：不要有明显的物体或阴影                        │
│                                                           │
│  "Do not add transparency"                                │
│  ──────────────────────                                    │
│  ← 与物体图像相反：背景不需要透明                          │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Prompt 6：空间约束生成

### 论文原文（补充材料第14页）

```python
system_prompt = (
    "You are a spatial relationship analyzer. "
    "Generate valid JSON constraints based on scene descriptions, "
    "object information and the reference image."
    
    "Output the constraints in a strict sequence: "
    "once an object has appeared as a target, "
    "it must not later appear as a source."
    
    "For each object, output all of its source-type constraints "
    "in true consecutive order in the list - they must be "
    "physically adjacent without any other constraints interleaved."
)

user_prompt = f"""
You are a spatial relationship analyzer. Given a scene description 
and a list of objects with their IDs, generate spatial constraints 
between the objects.

Scene Description:
{description}

Available Objects:
{objects_text}

Generate spatial constraints in the following JSON format:
[
    {{
        "type": "relative",
        "relation": "right of|left of|in front of|behind|side of|on|above",
        "source": "object_id",
        "target": "object_id"
    }},
    {{
        "type": "distance",
        "relation": "near|far",
        "source": "object_id",
        "target": "object_id"
    }},
    {{
        "type": "rotation",
        "relation": "face to",
        "source": "object_id",
        "target": "object_id"
    }}
]

Guidelines:
1. Only include meaningful spatial relationships that match the description
2. Use the exact object IDs from the available objects list
3. Focus on the most important spatial relationships
4. Avoid redundant relationships
5. Return only valid JSON, no additional text
6. For example, if "a chair to the right of a table", 
   relation = right of, source = chair, target = table
7. An object should either be on the ground (default) 
   or on/above another object
8. Use "on" for resting on surface. 
   Use "above" for floating/suspended.
"""
```

### 解构分析

```
┌───────────────────────────────────────────────────────────────────┐
│                System Prompt 的三个关键约束                        │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  约束 1："once a target, never a source"                           │
│  ────────────────────────────────────                              │
│  这是为 DFS 求解器设计的！                                         │
│                                                                   │
│  DFS 按拓扑序放置物体：                                            │
│  先放 target（被依赖的物体），再放 source（依赖它的物体）            │
│                                                                   │
│  如果 A 是 B 的 target，又是 C 的 source：                          │
│  → A 必须同时先于 B 和后于 C 放置                                  │
│  → 可能产生循环依赖                                                │
│  → DFS 无法求解                                                   │
│                                                                   │
│  所以强制：target 不能再变成 source                                │
│  → 保证拓扑排序一定存在                                            │
│  → DFS 不会死循环                                                  │
│                                                                   │
│  约束 2："same source constraints must be consecutive"             │
│  ────────────────────────────────────────────────                   │
│  DFS 处理一个物体时，需要同时满足它的所有约束                        │
│  如果约束分散在列表中，解析和处理更复杂                              │
│  连续排列 → 直接按 source 分组                                     │
│                                                                   │
│  约束 3："physically adjacent"                                     │
│  ────────────────────────────                                      │
│  不仅逻辑上连续，物理上也要相邻                                     │
│  → 避免生成跨越场景的不合理约束                                     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                User Prompt 的 8 条 Guidelines                     │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  G1: "meaningful relationships that match the description"        │
│  → 不要编造描述中没有的关系                                        │
│  → 防止 VLM 过度推理                                              │
│                                                                   │
│  G2: "exact object IDs from the available objects list"           │
│  → 用 Prompt 2 输出的 JSON 中的 ID                                │
│  → 防止 VLM 使用别名或编造新 ID                                   │
│                                                                   │
│  G3: "most important spatial relationships"                       │
│  → 不需要穷举所有物体对之间的关系                                  │
│  → N 个物体有 N(N-1)/2 种对，但大部分不需要约束                    │
│                                                                   │
│  G4: "Avoid redundant relationships"                              │
│  → 如果 A right of B 且 B left of A，只需一个                     │
│                                                                   │
│  G5: "Return only valid JSON"                                     │
│  → 格式硬约束                                                     │
│                                                                   │
│  G6: 举例说明 source/target 的方向                                 │
│  → "chair to the right of table"                                  │
│  → source=chair, target=table, relation=right of                  │
│  → 这个方向容易搞混，必须举例                                      │
│                                                                   │
│  G7: "on ground (default) or on/above another object"             │
│  → 默认所有物体在地面上                                            │
│  → 只有明确堆叠/悬浮才用 on/above                                  │
│  → 减少不必要的垂直约束                                            │
│                                                                   │
│  G8: "on" vs "above" 的区分                                       │
│  → on: 物理接触（台灯放在桌上）                                    │
│  → above: 悬浮/悬挂（吊灯在桌子上方）                              │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 输入构成

```python
messages = [
    {"role": "system", "content": system_prompt},
    {
        "role": "user",
        "content": [
            {"type": "text", "text": user_prompt},
            {"type": "image", "path": reference_image}  # 参考图像
        ]
    }
]

# 三重输入：
# 1. 场景描述文本 → 语义信息
# 2. 物体列表（ID+名称+描述） → 结构信息
# 3. 参考图像 → 空间信息
#
# VLM 综合三者推断物体间的空间关系
```

### 输出示例

```json
[
    {"type": "relative", "relation": "left of",
     "source": "nightstand_left", "target": "bed1"},
     
    {"type": "relative", "relation": "right of",
     "source": "nightstand_right", "target": "bed1"},
     
    {"type": "relative", "relation": "on",
     "source": "lamp_left", "target": "nightstand_left"},
     
    {"type": "distance", "relation": "near",
     "source": "lamp_left", "target": "bed1"},
     
    {"type": "relative", "relation": "on",
     "source": "photo_frames1", "target": "dresser1"}
]
```

---

## Prompt 7：约束修正（迭代）

### 论文原文（补充材料第15页）

```python
prompt = f"""
You are a spatial relationship analyzer. Given a scene description 
and a list of objects with their IDs, generate spatial constraints 
between the objects.

Scene Description:
{description}

Available Objects:
{objects_text}

Last time, the following constraints were generated:
{last_constraint_content}

Edit Instructions:
{edit_instructions}

Generate spatial constraints in the following JSON format:
[...]

Guidelines:
1-8. (与 Prompt 6 相同)

Generate the constraints:
"""
```

### 解构分析

```
┌───────────────────────────────────────────────────────────────────┐
│                    迭代修正的触发条件                               │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  DFS 求解器返回失败：                                              │
│  {                                                                │
│    "success": false,                                              │
│    "failed_objects": ["lamp_left"],                                │
│    "failure_reasons": {                                           │
│      "lamp_left": "cannot satisfy 'on' with 'nightstand_left'"   │
│    }                                                              │
│  }                                                                │
│                                                                   │
│  失败原因被转化为 edit_instructions：                               │
│  "Object 'lamp_left' could not be placed because                  │
│   the 'on' constraint with 'nightstand_left' conflicts            │
│   with other constraints. Please revise the constraints           │
│   for 'lamp_left'."                                               │
│                                                                   │
│  新的 Prompt 包含：                                                │
│  ├── 原始场景描述（不变）                                          │
│  ├── 物体列表（不变）                                              │
│  ├── 上次生成的约束（last_constraint_content）                     │
│  ├── 失败反馈（edit_instructions）                                 │
│  └── 参考图像（不变）                                              │
│                                                                   │
│  GPT-o3 会：                                                      │
│  1. 分析哪些约束导致了冲突                                         │
│  2. 调整或移除冲突的约束                                           │
│  3. 生成新的约束集                                                 │
│                                                                   │
│  然后再次运行 DFS 求解器                                           │
│  如果仍失败，继续迭代                                              │
│  论文没有明确说最大迭代次数                                         │
│  但实际上 2-3 次通常就够了                                          │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

```
迭代循环：

        ┌──────────────────────┐
        │  Prompt 6: 初始约束   │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │    DFS 求解器         │
        └──────────┬───────────┘
                   │
              ┌────┴────┐
              │ 成功?   │
              └────┬────┘
                   │
         Yes ◄─────┴─────► No
          │                 │
          ▼                 ▼
    ┌──────────┐   ┌──────────────────────┐
    │ 最终布局  │   │  Prompt 7: 修正约束   │
    └──────────┘   │  (上次约束 + 失败反馈) │
                   └──────────┬───────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │    DFS 求解器         │
                   └──────────┬───────────┘
                              │
                         ┌────┴────┐
                         │ 成功?   │
                         └────┬────┘
                              │
                    Yes ◄─────┴─────► No → 继续迭代...
                     │
                     ▼
               ┌──────────┐
               │ 最终布局  │
               └──────────┘
```

---

## 编辑场景的 Prompt

### Prompt 8：场景编辑（补充材料第17页）

```python
prompt = f"""
You are a spatial relationship analyzer. Given a list of objects 
with their IDs and a human feedback text, extract spatial constraints.

Your first task is to identify exactly one focus object from the 
feedback (the only object to be modified). Map this focus object 
to its exact ID from the Available Objects list.

Available Objects:
{objects_text}

Human Feedback:
{feedback}

Generate spatial constraints in the following JSON format:
[...]

Guidelines:
1. Identify exactly one focus object from the feedback; 
   it must be the only "source" in all constraints. 
   Never use the focus object as a "target".
2. Generate constraints only if they are explicitly 
   supported by the feedback.
3. Use the exact object IDs from the Available Objects list. 
   Ignore unknown objects.
4. Avoid redundant or contradictory relationships. 
   If conflicts arise, choose the most specific interpretation.
5-7. (类似之前)
"""
```

### 解构分析

```
┌───────────────────────────────────────────────────────────────────┐
│                    编辑 Prompt 的特殊设计                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  与生成 Prompt 的核心区别：                                        │
│                                                                   │
│  1. "identify exactly one focus object"                           │
│     → 编辑只动一个物体                                             │
│     → 其他所有物体位置不变                                         │
│     → DFS 只需搜索一个物体的位置                                   │
│                                                                   │
│  2. "only source in all constraints"                              │
│     → 被编辑的物体永远是 source                                    │
│     → 永远不是 target                                              │
│     → 因为它是要移动的，不是参照物                                  │
│                                                                   │
│  3. "only if explicitly supported by the feedback"                │
│     → 不要推理用户没说的                                           │
│     → "把椅子移到桌子右边" → 只生成 right_of 约束                  │
│     → 不要额外添加 near、face_to 等                                │
│                                                                   │
│  4. 没有参考图像输入                                               │
│     → 编辑时不需要参考图                                           │
│     → 只需要文本反馈和当前物体列表                                  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Prompt 设计的核心原则总结

```
┌───────────────────────────────────────────────────────────────┐
│              论文 Prompt 设计的 8 个核心原则                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  1. 输出格式硬约束                                             │
│     每个 Prompt 都明确指定 JSON schema                         │
│     "No extra commentary or Markdown"                         │
│                                                               │
│  2. 坐标系贯穿始终                                             │
│     从参考图生成到物体解析到约束生成                             │
│     统一使用 +X=right, +Y=backward, +Z=up                     │
│                                                               │
│  3. 粒度控制                                                   │
│     排除背景元素、排除零件                                     │
│     控制物体数量在 10-15 个                                    │
│                                                               │
│  4. 为下游设计上游                                             │
│     Prompt 1 的视角约束 → 为 Prompt 2 的位置解析服务            │
│     Prompt 3 的透明背景 → 为 Hunyuan3D 服务                    │
│     Prompt 6 的拓扑约束 → 为 DFS 求解器服务                    │
│                                                               │
│  5. 多模态输入                                                 │
│     文本 + 图像 双输入                                         │
│     文本提供语义，图像提供空间                                  │
│                                                               │
│  6. 防御性设计                                                 │
│     数值范围 [0.1, 5]                                          │
│     "Use exact object IDs"                                    │
│     "Avoid redundant relationships"                           │
│                                                               │
│  7. 少样本引导                                                 │
│     Guideline 6 用具体例子说明 source/target 方向              │
│     减少理解歧义                                               │
│                                                               │
│  8. 迭代友好                                                   │
│     Prompt 7 设计为可以接收上一次的输出和失败反馈               │
│     形成闭环                                                   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```