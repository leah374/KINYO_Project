# 家庭影音/K 歌产品脚本生成 Agent

主体对应 script_agent 目录，基于爆款视频口播转写、前序视频分析知识库和内容评价标准，生成广告短视频策划和脚本。采用 LangGraph 编排五个节点：

1. Brief 解析
2. RAG 检索
3. 策划生成
4. 四段式脚本生成
5. 按内容标准库评分，针对低分维度调取爆款案例库改写

## 目录结构

```text
.
├── script_agent/
│   ├── app.py                          # Streamlit 交互界面，用于查看脚本生成输出
│   ├── script_agent.py                 # 主 Agent：LangGraph 节点设计 + text-embedding-v4 构建向量知识库 + FAISS RAG
│   ├── build_rag_knowledge_base.py     # LLM 打标，构建两层知识库：结构化案例层 + 原始证据层
│   ├── video_transcription_pipeline.py # 视频转写工作流，ffmpeg 提取音频，qwen3-asr-flash 转写口播文本
│   └── requirements.txt                # 脚本生成部分依赖
├── previous_knowledge_base/            # 前序构建的爆款视频分析知识库和内容评分标准
├── rag_knowledge_base/                 # build_rag_knowledge_base 构建的两层知识库
├── transcription_result/               # 视频口播转写结果
├── vector_db/                          # FAISS 向量索引
├── outputs/                            # 运行结果，final_script 可用于下游输入
└── -- raw_videos/                         # 原始视频文件，交付时不上传
```

## 环境准备

安装依赖：

```bash
pip install -r script_agent/requirements.txt
```

常用环境变量：

- `K_TOKEN_API_KEY` 或 `OPENAI_API_KEY`：文本生成模型，默认接口地址 `https://ai.ktokenhub.app`
- `DASHSCOPE_API_KEY`：向量模型 `text-embedding-v4`
- `ASR_API_KEY`：如需重新转写视频，调用阿里云百炼 ASR

PowerShell 示例：

```powershell
$env:K_TOKEN_API_KEY="你的 Token 工厂 Key"
$env:DASHSCOPE_API_KEY="你的 DashScope Key"
```

如需调用视频生成链路，还需要参考：

```text
VIDEO_GENERATION_README.md
```

## 输入说明

- brief 尽量明确想要的场景、时长、突出产品特性、主要转化目标等要素，便于检索有效参考案例。
- 可以选择倾向的转化目标：`roi`、`completion_rate`、`balanced`。Agent 会针对性检索知识库。
- 如不设置广告时长和转化目标，默认 30 秒左右、`roi`。

## 常用命令

命令行生成一次脚本：

```bash
python script_agent/script_agent.py --brief "面向家庭用户，突出电视连接、K歌和观影一体化" --objective roi --duration 30
```

重新构建向量索引：

```bash
python script_agent/script_agent.py --build-index
```

启动交互界面：

```bash
python -m streamlit run script_agent/app.py --server.address 127.0.0.1 --server.port 8501
```

浏览器打开：

```text
http://127.0.0.1:8501
```

## RAG 实现说明

向量库包含三类集合：

- `video_cases`：完整案例，包含口播、标签、适用目标、高分原因等。
- `script_fragments`：可借鉴的脚本片段，服务 Hook、Setup、Twist、CTA 等局部生成。
- `strategy_rules`：从高分案例标签盘点、评价标准和高分经验中抽取的生成策略。

Agent 先根据 brief 检索相似案例(video_cases)与特征标签（strategy rules），生成策划，再根据策划检索脚本片段（script_fragments），生成四段式脚本。评分节点会读取 `previous_knowledge_base/内容评价标准库_v4.json`，找出不足项，再检索对应的高分案例进行补足改写。

## 输出文件

- `outputs/final_script/final_script.json`：最终脚本专用 JSON，推荐后续 Agent 或程序直接读取。
- `outputs/final_script/final_script.md`：最终脚本 Markdown，方便人工查看和复制。
- `outputs/script_complete_result.json`：命令行完整运行结果，包含检索证据、评分、运行轨迹等调试信息。
- `outputs/streamlit_last_result.json`：Streamlit 最近一次完整运行结果。

`final_script.json` 是下游最稳定的接口，结构只保留最终使用信息：

- `planning`：最终使用的策划方案，包含目标人群、创意角度、核心痛点、核心卖点等。
- `script`：四段式脚本，包含 Hook、Setup、Twist、CTA 的画面、口播、字幕和镜头提示。
