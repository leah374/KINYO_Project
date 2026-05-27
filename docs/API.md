# KINYO AI 视频生成平台 - API Reference

## 目录

- [概述](#概述)
- [核心模块](#核心模块)
- [Workflow Manager API](#workflow-manager-api)
- [Config Manager API](#config-manager-api)
- [Database API](#database-api)
- [Component API](#component-api)
- [Script Agent API](#script-agent-api)
- [Visual Agent API](#visual-agent-api)
- [Video Agent API](#video-agent-api)

---

## 概述

KINYO AI 视频生成平台采用模块化架构，主要API分为以下几个层次：

```
┌─────────────────────────────────────┐
│       Streamlit UI Layer            │
├─────────────────────────────────────┤
│    Component Layer (UI Components)  │
├─────────────────────────────────────┤
│    Utility Layer (Core Utilities)   │
├─────────────────────────────────────┤
│    Agent Layer (AI Agents)          │
└─────────────────────────────────────┘
```

---

## 核心模块

### 导入方式

```python
# 工具模块
from streamlit_app.utils.config import ConfigManager
from streamlit_app.utils.session_state import SessionStateManager
from streamlit_app.utils.database import HistoryDatabase
from streamlit_app.utils.workflow_manager import WorkflowManager

# 组件模块
from streamlit_app.components.file_manager import FileManager
from streamlit_app.components.api_key_manager import APIKeyManager
from streamlit_app.components.script_editor import ScriptEditor
from streamlit_app.components.progress_tracker import ProgressTracker

# Agent 模块
from script_agent.agent.script_agent import run_agent, save_final_script
from visual_agent.agent.keyframe_storyboard_agent import run as run_storyboard
from video_agent.agent.seedance_video_agent import run as run_video
```

---

## Workflow Manager API

### 类：`WorkflowManager`

端到端工作流管理器，协调三个 Agent 的执行。

#### 初始化

```python
from streamlit_app.utils.workflow_manager import WorkflowManager

workflow = WorkflowManager()
```

#### 方法

##### `run_script_generation()`

运行脚本生成阶段。

**签名**：
```python
def run_script_generation(
    self,
    brief: str,
    objective: str = "roi",
    duration: int = 30,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]
```

**参数**：
- `brief` (str): 营销需求描述
- `objective` (str): 目标类型，可选值：`"roi"`, `"completion_rate"`, `"balanced"`
- `duration` (int): 视频时长（秒）
- `progress_callback` (Callable, optional): 进度回调函数 `(progress: int, message: str) -> None`

**返回**：
```python
{
    "success": bool,           # 是否成功
    "result": Dict,            # 完整生成结果
    "file_path": str,          # 输出文件路径
    "record_id": int,          # 数据库记录ID
    "error": str               # 错误信息（如果失败）
}
```

**示例**：
```python
# 基本用法
result = workflow.run_script_generation(
    brief="做一条30秒K歌产品广告",
    objective="roi",
    duration=30
)

# 带进度回调
def progress_callback(progress: int, message: str):
    print(f"[{progress}%] {message}")

result = workflow.run_script_generation(
    brief="做一条30秒K歌产品广告",
    objective="roi",
    duration=30,
    progress_callback=progress_callback
)

if result["success"]:
    print(f"脚本已保存到: {result['file_path']}")
else:
    print(f"生成失败: {result['error']}")
```

---

##### `run_storyboard_generation()`

运行关键帧生成阶段。

**签名**：
```python
def run_storyboard_generation(
    self,
    script_data: Optional[Dict] = None,
    script_file_path: Optional[str] = None,
    max_shots: int = 10,
    generate_images: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]
```

**参数**：
- `script_data` (Dict, optional): 脚本数据对象
- `script_file_path` (str, optional): 脚本文件路径
- `max_shots` (int): 最大镜头数
- `generate_images` (bool): 是否生成关键帧图片
- `progress_callback` (Callable, optional): 进度回调函数

**返回**：
```python
{
    "success": bool,
    "result": Dict,            # 分镜结果
    "file_path": str,          # storyboard.json 路径
    "record_id": int,
    "error": str
}
```

**示例**：
```python
# 从文件生成
result = workflow.run_storyboard_generation(
    script_file_path="outputs/final_script/final_script.json",
    max_shots=10,
    generate_images=False
)

# 从数据对象生成
script_data = {...}  # 从上次脚本生成结果获取
result = workflow.run_storyboard_generation(
    script_data=script_data,
    max_shots=10,
    generate_images=True
)
```

---

##### `run_video_generation()`

运行视频生成阶段。

**签名**：
```python
def run_video_generation(
    self,
    storyboard_data: Optional[Dict] = None,
    storyboard_file_path: Optional[str] = None,
    keyframe_dir: Optional[str] = None,
    generate_audio: bool = True,
    concat: bool = True,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]
```

**参数**：
- `storyboard_data` (Dict, optional): 分镜数据对象
- `storyboard_file_path` (str, optional): storyboard.json 文件路径
- `keyframe_dir` (str, optional): 关键帧图片目录
- `generate_audio` (bool): 是否生成音频
- `concat` (bool): 是否拼接视频片段
- `progress_callback` (Callable, optional): 进度回调函数

**返回**：
```python
{
    "success": bool,
    "result": Dict,            # 视频生成结果
    "file_path": str,          # 最终视频路径
    "record_id": int,
    "error": str
}
```

**示例**：
```python
result = workflow.run_video_generation(
    storyboard_file_path="outputs/keyframes/storyboard.json",
    keyframe_dir="outputs/keyframes/images",
    generate_audio=True,
    concat=True
)
```

---

##### `run_full_pipeline()`

一键运行完整流程。

**签名**：
```python
def run_full_pipeline(
    self,
    brief: str,
    objective: str = "roi",
    duration: int = 30,
    max_shots: int = 10,
    generate_audio: bool = True,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]
```

**参数**：
- `brief` (str): 营销需求描述
- `objective` (str): 目标类型
- `duration` (int): 视频时长
- `max_shots` (int): 最大镜头数
- `generate_audio` (bool): 是否生成音频
- `progress_callback` (Callable, optional): 进度回调函数

**返回**：
```python
{
    "success": bool,
    "results": {
        "script": {...},
        "storyboard": {...},
        "video": {...}
    },
    "total_duration": float,    # 总耗时（秒）
    "full_pipeline_id": int     # 完整流程记录ID
}
```

**示例**：
```python
def progress_callback(progress: int, message: str):
    print(f"[{progress}%] {message}")

result = workflow.run_full_pipeline(
    brief="做一条30秒K歌产品广告",
    objective="roi",
    duration=30,
    max_shots=10,
    generate_audio=True,
    progress_callback=progress_callback
)

if result["success"]:
    print(f"完成！总耗时: {result['total_duration']:.1f}秒")
    print(f"最终视频: {result['results']['video']['file_path']}")
```

---

##### `pause()`, `resume()`, `cancel()`

工作流控制方法。

```python
# 暂停工作流
workflow.pause()

# 恢复工作流
workflow.resume()

# 取消工作流
workflow.cancel()

# 重置状态
workflow.reset()
```

---

## Config Manager API

### 类：`ConfigManager` (单例)

配置管理器，管理 API Keys、模型参数、路径设置。

#### 初始化

```python
from streamlit_app.utils.config import ConfigManager

config = ConfigManager()  # 单例模式
```

#### 方法

##### `get_api_key()`

获取 API Key。

**签名**：
```python
def get_api_key(self, key_name: str) -> Optional[str]
```

**参数**：
- `key_name` (str): Key 名称，可选值：
  - `"k_token"`
  - `"openai"`
  - `"dashscope"`
  - `"ark"`
  - `"seedance"`

**示例**：
```python
api_key = config.get_api_key("k_token")
if api_key:
    print(f"K Token已配置: {api_key[:8]}***")
else:
    print("K Token未配置")
```

---

##### `set_api_key()`

设置 API Key。

**签名**：
```python
def set_api_key(
    self,
    key_name: str,
    value: str,
    save_to_env: bool = False
) -> None
```

**参数**：
- `key_name` (str): Key 名称
- `value` (str): API Key 值
- `save_to_env` (bool): 是否保存到 .env 文件

**示例**：
```python
# 设置到内存（临时）
config.set_api_key("k_token", "sk-xxxxx")

# 设置并保存到 .env 文件（持久化）
config.set_api_key("k_token", "sk-xxxxx", save_to_env=True)
```

---

##### `get_model()`, `set_model()`

获取/设置模型名称。

```python
# 获取模型
model = config.get_model("script_generation")  # "gpt-5.4"

# 设置模型
config.set_model("script_generation", "gpt-4")
```

**模型类型**：
- `"script_generation"`: 脚本生成模型
- `"embedding"`: 向量嵌入模型
- `"image_generation"`: 图片生成模型
- `"video_generation"`: 视频生成模型

---

##### `get_path()`

获取项目路径。

```python
# 获取路径
outputs_path = config.get_path("outputs")
script_agent_path = config.get_path("script_agent")
```

**路径类型**：
- `"script_agent"`: 脚本 Agent 目录
- `"visual_agent"`: 视觉 Agent 目录
- `"video_agent"`: 视频 Agent 目录
- `"outputs"`: 输出目录
- `"database"`: 数据库目录
- `"knowledge_base"`: 知识库目录

---

##### `get_default()`, `set_default()`

获取/设置默认参数。

```python
# 获取默认值
duration = config.get_default("script_duration")  # 30
objective = config.get_default("script_objective")  # "roi"

# 设置默认值
config.set_default("script_duration", 45)
```

---

##### `test_api_connection()`

测试 API 连接。

**签名**：
```python
def test_api_connection(self, key_name: str) -> Tuple[bool, str]
```

**返回**：
```python
(True, "Connection successful")  # 成功
(False, "API key not configured")  # 失败
```

**示例**：
```python
success, message = config.test_api_connection("k_token")
if success:
    print("连接成功")
else:
    print(f"连接失败: {message}")
```

---

## Database API

### 类：`HistoryDatabase`

历史记录数据库管理器。

#### 初始化

```python
from streamlit_app.utils.database import HistoryDatabase

db = HistoryDatabase()
# 数据库位置: streamlit_app/database/kinuyo_history.db
```

#### 方法

##### `save_script_generation()`

保存脚本生成记录。

**签名**：
```python
def save_script_generation(
    self,
    brief: str,
    result: Dict[str, Any],
    objective: Optional[str] = None,
    duration: Optional[int] = None,
    metadata: Optional[Dict] = None,
    file_path: Optional[str] = None
) -> int  # 返回记录ID
```

**示例**：
```python
record_id = db.save_script_generation(
    brief="做一条K歌产品广告",
    result={"script": {...}, "evaluation": {...}},
    objective="roi",
    duration=30,
    file_path="outputs/final_script/final_script.json"
)
```

---

##### `save_storyboard_generation()`

保存分镜生成记录。

```python
record_id = db.save_storyboard_generation(
    result={"storyboard": [...]},
    script_id=previous_script_id,  # 关联的脚本记录ID
    source_file="outputs/final_script/final_script.json",
    file_path="outputs/keyframes/storyboard.json"
)
```

---

##### `save_video_generation()`

保存视频生成记录。

```python
record_id = db.save_video_generation(
    result={"clips": [...]},
    storyboard_id=previous_storyboard_id,
    source_file="outputs/keyframes/storyboard.json",
    metadata={
        "duration_seconds": 50.0,
        "file_size_mb": 45.2
    },
    file_path="outputs/videos/final_video.mp4"
)
```

---

##### `get_all_history()`

获取所有历史记录。

**签名**：
```python
def get_all_history(
    self,
    limit: int = 50,
    offset: int = 0,
    history_type: Optional[str] = None
) -> List[Dict]
```

**参数**：
- `limit`: 返回数量
- `offset`: 偏移量（分页）
- `history_type`: 类型筛选，可选值：`"script"`, `"storyboard"`, `"video"`

**示例**：
```python
# 获取所有类型
history = db.get_all_history(limit=20, offset=0)

# 只要脚本生成记录
scripts = db.get_all_history(limit=20, history_type="script")

for record in scripts:
    print(f"{record['timestamp']}: {record['brief'][:50]}")
```

---

##### `search_history()`

搜索历史记录。

```python
results = db.search_history("K歌", history_type="script")
```

---

##### `delete_record()`

删除记录。

```python
success = db.delete_record("script", record_id=15)
if success:
    print("删除成功")
```

---

##### `get_statistics()`

获取统计信息。

```python
stats = db.get_statistics()
# 返回：
{
    "script_count": 12,
    "storyboard_count": 8,
    "video_count": 5,
    "full_pipeline_count": 3
}
```

---

## Component API

### 类：`FileManager`

文件管理组件。

#### 方法

##### `select_or_upload_file()`

创建文件选择/上传组件。

**签名**：
```python
@staticmethod
def select_or_upload_file(
    label: str,
    file_types: List[str],
    key: str,
    default_dir: Optional[Path] = None,
    allow_upload: bool = True,
    allow_select: bool = True
) -> Tuple[Optional[Path], Optional[Any]]
```

**返回**：
- `(file_path, None)`: 从项目选择
- `(None, uploaded_file)`: 上传文件
- `(None, None)`: 使用历史记录

**示例**：
```python
file_path, uploaded = FileManager.select_or_upload_file(
    label="Select Script JSON",
    file_types=[".json"],
    key="script_file",
    default_dir=Path("outputs/final_script")
)

if file_path:
    print(f"选中文件: {file_path}")
elif uploaded:
    print(f"上传文件: {uploaded.name}")
```

---

##### `load_json_file()`

加载 JSON 文件。

```python
data = FileManager.load_json_file(
    file_path=file_path,
    uploaded_file=uploaded
)
```

---

##### `download_button()`

创建下载按钮。

```python
FileManager.download_button(
    data={"script": {...}},
    filename="final_script.json",
    label="Download Script",
    key="download_script"
)
```

---

### 类：`APIKeyManager`

API Key 管理组件。

#### 方法

##### `render_api_key_input()`

渲染 API Key 输入框。

```python
success, error = APIKeyManager.render_api_key_input(
    key_name="k_token",
    display_name="K Token API Key",
    help_text="Required for script generation",
    test_on_save=True
)
```

---

##### `validate_required_keys()`

验证必需的 API Keys。

```python
validation = APIKeyManager.validate_required_keys()
# 返回：
{
    "Script Generation": True,
    "Embedding": True,
    "Video Generation": False
}
```

---

### 类：`ScriptEditor`

脚本编辑器组件。

#### 方法

##### `render_editor()`

渲染脚本编辑器。

```python
edited_script = ScriptEditor.render_editor(
    script_data={"script": {...}, "planning": {...}},
    key="script_editor"
)
```

---

##### `validate_script()`

验证脚本结构。

```python
is_valid, errors = ScriptEditor.validate_script(script_data)
if not is_valid:
    for error in errors:
        print(f"错误: {error}")
```

---

### 类：`ProgressTracker`

进度追踪组件。

#### 使用方式

```python
tracker = ProgressTracker(key="my_progress")
tracker.init()

# 更新进度
tracker.update(progress=50, message="Processing...")

# 添加日志
tracker.add_log("Starting task 1")
tracker.add_log("Task 1 completed")

# 清除
tracker.clear()
```

---

## Script Agent API

### 函数：`run_agent()`

运行脚本生成 Agent。

**签名**：
```python
def run_agent(
    brief: str,
    objective: str = "roi",
    duration: int = 30
) -> Dict[str, Any]
```

**返回结构**：
```python
{
    "final_output": {
        "script": {
            "title": "...",
            "objective": "...",
            "segments": [
                {
                    "stage": "Hook",
                    "time": "0-3秒",
                    "purpose": "...",
                    "visual": "...",
                    "voiceover": "...",
                    "subtitle": "...",
                    "shot_hint": "..."
                },
                # ... 其他段
            ]
        },
        "planning": {
            "target_user": "...",
            "core_selling_point": "...",
            "creative_angle": "...",
            "core_pain_point": "..."
        },
        "evaluation": {
            "overall_score": 6.8,
            "passed": True,
            "dimension_scores": [...]
        },
        "repair_evidence": [...]
    },
    "retrieved_cases": [...],
    "retrieved_fragments": [...],
    "strategy_rules": [...],
    "trace": [...]
}
```

**示例**：
```python
from script_agent.agent.script_agent import run_agent

result = run_agent(
    brief="做一条30秒K歌产品广告，突出一根线变KTV",
    objective="roi",
    duration=30
)

# 提取脚本
script = result["final_output"]["script"]
for segment in script["segments"]:
    print(f"{segment['stage']}: {segment['voiceover']}")

# 提取评分
evaluation = result["final_output"]["evaluation"]
print(f"总分: {evaluation['overall_score']}/7.0")
```

---

### 函数：`save_final_script()`

保存最终脚本到文件。

```python
from script_agent.agent.script_agent import save_final_script

save_final_script(result)
# 输出:
# - outputs/final_script/final_script.json
# - outputs/final_script/final_script.md
```

---

## Visual Agent API

### 函数：`run()`

运行关键帧生成。

**签名**：
```python
def run(args: argparse.Namespace) -> Dict[str, Path]
```

**args 参数**：
```python
args = argparse.Namespace(
    input="outputs/final_script/final_script.json",
    output_dir="outputs/keyframes",
    max_shots=10,
    generate_images=False,
    base_url="https://ai.ktokenhub.app",
    image_model="gpt-image-2",
    size="auto",
    quality="auto",
    sleep=0.2,
    retries=2,
    overwrite=False,
    skip_shots=[]
)
```

**返回**：
```python
{
    "storyboard_json": Path("outputs/keyframes/storyboard.json"),
    "storyboard_md": Path("outputs/keyframes/storyboard.md"),
    "prompts_jsonl": Path("outputs/keyframes/image_prompts.jsonl"),
    "generated_images_json": Path("outputs/keyframes/generated_images.json")
}
```

**示例**：
```python
from visual_agent.agent.keyframe_storyboard_agent import run
import argparse

args = argparse.Namespace(
    input="outputs/final_script/final_script.json",
    output_dir="outputs/keyframes",
    max_shots=10,
    generate_images=False
)

paths = run(args)
print(f"分镜表已保存到: {paths['storyboard_json']}")
```

---

## Video Agent API

### 函数：`run()`

运行视频生成。

**签名**：
```python
def run(args: argparse.Namespace) -> Dict[str, Any]
```

**args 参数**：
```python
args = argparse.Namespace(
    storyboard="outputs/keyframes/storyboard.json",
    keyframe_dir="outputs/keyframes/images",
    output_dir="outputs/videos",
    submit=True,  # 是否提交API
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    model="doubao-seedance-2-0-260128",
    ratio="9:16",
    resolution="",
    duration=5,
    image_mode="base64",
    generate_audio=True,
    watermark=False,
    camera_fixed=False,
    use_last_frame=False,
    only_shots="",
    skip_shots="",
    callback_url="",
    overwrite=False,
    poll_interval=10,
    timeout=900,
    concat=True,
    compatible_output=True
)
```

**返回**：
```python
{
    "plan_path": "outputs/videos/seedance_request_plan.json",
    "results_path": "outputs/videos/seedance_results.json",
    "final_video_path": "outputs/videos/final_seedance_video_compatible.mp4",
    "compatible_video_path": "outputs/videos/final_seedance_video_compatible.mp4",
    "job_count": 10,
    "skipped_count": 0
}
```

**示例**：
```python
from video_agent.agent.seedance_video_agent import run
import argparse

args = argparse.Namespace(
    storyboard="outputs/keyframes/storyboard.json",
    keyframe_dir="outputs/keyframes/images",
    output_dir="outputs/videos",
    submit=True,
    generate_audio=True,
    concat=True,
    compatible_output=True
)

result = run(args)
if result["final_video_path"]:
    print(f"视频已生成: {result['final_video_path']}")
```

---

## 完整示例

### 示例1: 命令行完整流程

```python
from streamlit_app.utils.workflow_manager import WorkflowManager

def progress_callback(progress, message):
    print(f"[{progress}%] {message}")

workflow = WorkflowManager()

# 一键生成
result = workflow.run_full_pipeline(
    brief="做一条30秒家用K歌一体机广告",
    objective="roi",
    duration=30,
    max_shots=10,
    generate_audio=True,
    progress_callback=progress_callback
)

if result["success"]:
    print(f"完成！耗时: {result['total_duration']:.1f}秒")
    print(f"视频路径: {result['results']['video']['file_path']}")
else:
    print("生成失败")
```

### 示例2: 分步控制

```python
from streamlit_app.utils.workflow_manager import WorkflowManager
from streamlit_app.utils.config import ConfigManager
import json

# 配置
config = ConfigManager()
config.set_api_key("k_token", "sk-xxxxx", save_to_env=True)

workflow = WorkflowManager()

# Step 1: 生成脚本
print("Step 1: 生成脚本...")
script_result = workflow.run_script_generation(
    brief="做一条30秒K歌广告",
    objective="roi",
    duration=30
)

if not script_result["success"]:
    print("脚本生成失败")
    exit(1)

# 查看评分
script_data = script_result["result"]["final_output"]
print(f"脚本评分: {script_data['evaluation']['overall_score']}/7.0")

# Step 2: 生成分镜
print("\nStep 2: 生成分镜...")
storyboard_result = workflow.run_storyboard_generation(
    script_file_path=script_result["file_path"],
    max_shots=10,
    generate_images=False  # 先不生成图片
)

if not storyboard_result["success"]:
    print("分镜生成失败")
    exit(1)

# 查看分镜
storyboard = json.load(open(storyboard_result["file_path"]))
print(f"分镜数量: {len(storyboard['storyboard'])}")

# Step 3: 生成视频
print("\nStep 3: 生成视频...")
video_result = workflow.run_video_generation(
    storyboard_file_path=storyboard_result["file_path"],
    keyframe_dir=None,  # 可能需要先生成关键帧
    generate_audio=True,
    concat=True
)

if video_result["success"]:
    print(f"完成！视频路径: {video_result['file_path']}")
```

---

## 错误处理

### 常见错误码

| 错误 | 描述 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError` | 模块未找到 | `pip install -r requirements.txt` |
| `FileNotFoundError` | 文件不存在 | 检查路径配置 |
| `APIError` | API 调用失败 | 检查 API Key 和网络 |
| `TimeoutError` | 超时 | 增加timeout参数 |
| `ValueError` | 参数错误 | 检查输入参数格式 |

### 异常处理示例

```python
from streamlit_app.utils.workflow_manager import WorkflowManager

workflow = WorkflowManager()

try:
    result = workflow.run_script_generation(
        brief="...",
        objective="roi"
    )
except ValueError as e:
    print(f"参数错误: {e}")
except TimeoutError as e:
    print(f"超时: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 版本信息

**API Version**: 1.0.0  
**Last Updated**: 2025-05-25  
**Compatibility**: Python 3.11+

---

## 更新日志

### v1.0.0 (2025-05-25)
- 初始版本发布
- 完整的三个 Agent API
- 统一的 Workflow Manager
- 组件化和模块化架构
