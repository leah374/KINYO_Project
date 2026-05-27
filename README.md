# KINYO AI 视频生成平台

端到端的 AI 驱动短视频广告生成系统：人物生成 → 脚本生成 → 关键帧生成 → 视频生成

## 功能特性

- **👤 人物生成**：生成带网格遮罩的人物图像，支持自定义命名和描述
- **📝 脚本生成**：基于 LangGraph RAG 的智能脚本生成，支持多轮优化
- **🖼️ 关键帧生成**：产品导向的关键帧生成，支持环境参考图片
- **🎬 视频生成**：使用 Doubao Seedance 2.0 API 生成高质量视频
- **💡 提示词优化**：GPT 驱动的提示词优化，支持单独/批量优化
- **📊 历史记录**：完整的项目历史管理和版本跟踪

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository_url>
cd KINYO_Project

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖 (python=3.13)
pip install -r requirements_python313.txt
```

### 2. 配置环境变量

**重要**：在项目根目录创建 `.env` 文件，配置以下 API Keys：

```env
# 文本生成模型（必需）
K_TOKEN_API_KEY=your_ktoken_api_key_here
K_TOKEN_BASE_URL=https://ai.ktokenhub.app/v1

# 向量模型（脚本生成需要）
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 视频生成（必需）
ARK_API_KEY=your_volcano_ark_api_key_here
# 或
SEEDANCE_API_KEY=your_seedance_api_key_here

# 视频转写（可选）
ASR_API_KEY=your_asr_api_key_here
```

#### API Key 获取方式

| API Key | 获取地址 | 用途 |
|---------|---------|------|
| K_TOKEN_API_KEY | [KTokenHub](https://ai.ktokenhub.app) | GPT 文本生成 |
| DASHSCOPE_API_KEY | [阿里云百炼](https://bailian.console.aliyun.com/) | 向量嵌入 |
| ARK_API_KEY | [火山方舟](https://console.volcengine.com/ark) | Seedance 视频生成 |

### 3. 启动应用

```bash
streamlit run streamlit_app/app.py
```

访问 `http://localhost:8501` 打开应用界面。

## 使用流程

### 完整工作流

```
概览 → 人物生成 → 脚本生成 → 关键帧生成 → 视频生成 → 历史记录
```

#### 1. 人物生成（可选）

- 在"人物生成"页面上传人物参考图或使用 AI 生成
- 支持生成两种图像：
  - `front_masked`：面部带网格遮罩（隐私保护）
  - `front_full`：完整面部图像
- 添加人物描述，系统自动保存

#### 2. 脚本生成

- 输入产品 brief、目标、时长
- 系统自动生成四段式脚本：
  - S01: 痛点场景
  - S02: 产品引入
  - S03: 利益展示
  - S04: 行动召唤
- 支持多轮评分和改写优化

#### 3. 关键帧生成

- 基于脚本自动生成关键帧提示词
- 上传产品图片和环境参考图
- 支持图片拼接：产品（左）+ 环境（右）
- 可调节每段关键帧数量

#### 4. 视频生成

**Segment 配置**：
- 为每个 segment 选择人物
- 设置时长（3-15秒）
- 选择产品特写图片（可选）

**提示词优化**：
- 点击"优化此片段"单独优化
- 或点击"AI优化所有提示词"批量优化
- 优化后可直接在文本框编辑
- 显示优化前后对比

**生成模式**：
- **批量生成**：一次性生成所有片段
- **逐个生成**：逐个确认后生成

**输出**：
- 每个片段独立视频文件
- 自动拼接为完整视频
- 生成兼容版本视频

## 项目结构

```
KINYO_Project/
├── .env                          # API Keys 配置（需自行创建）
├── requirements.txt              # Python 依赖
│
├── streamlit_app/               # Streamlit 应用
│   ├── app.py                   # 主应用入口
│   ├── pages/                   # 页面模块
│   │   ├── 1_📋_概览.py
│   │   ├── 2_👤_人物生成.py
│   │   ├── 3_📝_脚本生成.py
│   │   ├── 4_🖼️_关键帧生成.py
│   │   ├── 5_🎬_视频生成.py
│   │   ├── 6_📊_历史记录.py
│   │   └── 7_⚙️_设置.py
│   ├── components/              # UI 组件
│   └── utils/                   # 工具函数
│
├── script_agent/                # 脚本生成 Agent
│   ├── agent/
│   │   ├── script_agent.py     # LangGraph RAG 主 Agent
│   │   └── build_rag_knowledge_base.py
│   ├── knowledge_base/         # 知识库
│   └── vector_db/              # FAISS 向量库
│
├── visual_agent/                # 视觉生成 Agent
│   ├── agent/
│   │   ├── character_generator.py       # 人物生成
│   │   ├── keyframe_storyboard_agent.py # 分镜生成
│   │   └── safe_keyframe_generator.py   # 安全关键帧
│
├── video_agent/                 # 视频生成 Agent
│   └── agent/
│       ├── video_segment_generator.py   # 视频片段生成
│       └── seedance_video_agent.py     # Seedance SDK 示例
│
├── assets/                      # 静态资源
│   ├── characters/             # 人物图像
│   │   └── {character_id}/
│   │       ├── {id}_front_masked.png
│   │       ├── {id}_front_full.png
│   │       └── {id}_desc.json
│   ├── products/               # 产品图片
│   └── environments/           # 环境参考图
│
├── outputs/                     # 输出目录
│   ├── scripts/                # 生成的脚本
│   ├── keyframes/              # 关键帧图像
│   └── videos/                 # 视频输出
│
└── docs/                        # 文档
    ├── seedance_prompt_guide.md    # Seedance 提示词指南
    ├── SCRIPT_GENERATION_README.md
    └── VIDEO_GENERATION_README.md
```

## 核心模块

### 1. 人物生成模块

**功能**：
- AI 生成人物参考图
- 自动生成面部网格遮罩
- 保存人物描述 JSON
- 支持自定义命名

**输出**：
```
assets/characters/{character_id}/
├── {id}_front_masked.png  # 网格遮罩版本
├── {id}_front_full.png    # 完整版本
└── {id}_desc.json         # 描述文件
```

### 2. 脚本生成模块

**技术栈**：
- LangGraph 状态管理
- FAISS 向量检索
- RAG 知识增强

**流程**：
1. Brief 解析
2. RAG 检索相似案例
3. 策划生成
4. 四段式脚本生成
5. 评分与改写优化

### 3. 关键帧生成模块

**功能**：
- 自动生成关键帧提示词
- 支持产品图片上传
- 支持环境参考图片
- 图片拼接处理

**提示词优化**：
- 参考 `docs/seedance_prompt_guide.md`
- 自动添加图片编号映射
- 优化动作描述、运镜、画质约束

### 4. 视频生成模块

**API**: Doubao Seedance 2.0

**参数**：
- `model`: doubao-seedance-2-0-260128
- `duration`: 3-15 秒
- `generate_audio`: True（默认）
- `ratio`: adaptive（自适应比例）

**图片传递顺序**：
1. 关键帧（图片1）
2. 产品图（图片2，如有）
3. 人物图（图片3+）

**输出**：
```
outputs/videos/{folder_name}/
├── S01.mp4, S02.mp4, ...     # 片段视频
├── prompts.json              # 使用的提示词
├── final_video.mp4           # 拼接视频
└── final_video_compatible.mp4 # 兼容版本
```

## 提示词优化

### GPT 优化模型

- **模型**: gpt-5.4
- **API**: KToken (https://ai.ktokenhub.app/v1)

### 优化内容

1. **图片引用优化**
   - 明确标注图片编号（图片1、图片2...）
   - 人物定义：`将图片N中的[特征]定义为[人物名]`

2. **动作描述优化**
   - 具体到肢体部位
   - 优先低缓连续小动作
   - 情绪外化为动作细节

3. **视频连贯性**
   - 片段间动作衔接
   - 人物位置、姿态连续性
   - 产品位置稳定
   - 光影色调统一

4. **约束添加**
   - 无字幕、无Logo、无水印
   - 人物数量严格匹配
   - 禁止生成额外人物

### 对比显示

优化后显示：
- 优化前提示词
- 优化后提示词
- 可直接编辑

## 常见问题

### Q: 视频生成超时？

A: Seedance API 在高峰期响应较慢。系统已设置超时为 10 分钟。如仍超时，请稍后重试。

### Q: 生成的人物未显示？

A: 请检查 `assets/characters/{character_id}/` 目录下是否有 `*_desc.json` 文件。系统必须找到描述文件才能加载人物。

### Q: 提示词优化无效果？

A: 请确认 `.env` 文件中已正确配置 `K_TOKEN_API_KEY`，且 base_url 包含 `/v1` 后缀。

### Q: 视频中出现额外人物？

A: 在提示词优化时会自动添加人物数量约束，确保只使用提供的人物图片。

## 依赖版本 (Python=3.13)

```
streamlit>=1.28.0
openai>=1.0.0
langchain>=0.1.0
langgraph>=0.0.20
faiss-cpu>=1.7.4
volcengine-python-sdk>=1.0.0
Pillow>=10.0.0
requests>=2.31.0
```

## 许可证

请遵守相关 API 服务条款和数据隐私规定。

## 更新日志

### v1.1.0 (2026-05-27)
- 添加提示词优化功能（GPT 驱动）
- 支持优化前后对比显示
- 优化视频连贯性约束
- 改进人物数量限制
- 提升代码健壮性

### v1.0.0
- 初始版本
- 完整的四段式脚本生成
- 视频生成流程
