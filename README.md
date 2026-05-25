# 家庭影音/K 歌产品脚本生成 Agent

基于爆款视频口播转写、前序视频分析知识库和内容评价标准，生成广告短视频脚本。采用 LangGraph 编排五个节点：

1. Brief 解析
2. RAG 检索
3. 策划生成
4. 四段式脚本生成
5. 按内容标准库评分，并调取高分案例（归因）改写

## 目录结构

```text
.
├── app.py                              # Streamlit 交互界面,便于查看脚本部分输出，后续可重建最终的视频生成agent交互
├── script_agent_langgraph_rag.py       # 主 Agent：LangGraph节点设计 + text-embedding-v4构建向量知识库 + FAISS RAG
├── build_two_layer_knowledge_base.py   # llm打标，构建两层知识库：结构化案例层（多重标签标识特征） + 原始证据层（口播文本merge评分知识库）
├── video_transcription_pipeline.py     # 视频转写工作流，ffmpeg提取音频，qwen3-asr-flash转写口播文本
├── visual_agent/                       # 第4步：分镜、关键帧提示词、OpenAI 图片生成
├── video_agent/                        # 第5步：读取关键帧，用 Seedance 生成视频片段并可选拼接
├── previous_knowledge_base/            # 前序构建的爆款视频分析知识库和内容评分标准
├── processed_knowledge_base/           # build_two_layer_knowledge_base构建的两层知识库
├── transcription_result/               # 视频口播转写结果
├── vector_db/faiss_processed_v1/       # FAISS 向量索引
├── outputs/                            # 运行结果，final_script只包含终版脚本和策划，可以用于下游输入，完整输出包含改写原因、评分等trace信息
└── -- raw_videos/                      # 原始视频文件，交付时不上传
```

## 环境准备

安装依赖：

```bash
pip install -r requirements.txt
```

API Key 使用环境变量配置，不要把 key 写进代码或提交到 GitHub。

常用环境变量：

- `K_TOKEN_API_KEY` 或 `OPENAI_API_KEY`：文本生成模型，默认接口地址 `https://ai.ktokenhub.app`
- `DASHSCOPE_API_KEY`：向量模型 `text-embedding-v4`
- `ASR_API_KEY`：如需重新转写视频，调用阿里云百炼 ASR

示例：

```bash
export OPENAI_API_KEY="你的 Token 工厂 Key"
export DASHSCOPE_API_KEY="你的 DashScope Key"
```

如果要调用 Seedance 生成视频，还需要设置：

```bash
export SEEDANCE_API_KEY="你的 Seedance/LAS/Ark API Key"
```


## 输入说明

- brief尽量明确想要的场景、时长、突出产品特性、主要转化目标等要素，便于检索有效的参考案例。
- 可以选择倾向的转化目标：roi、完播率、综合。Agent会针对性检索知识库。
- 如不设置广告时长和转化目标，默认30s左右、roi。

## 常用命令

命令行生成一次脚本：

```bash
python script_agent_langgraph_rag.py --brief "面向家庭用户，突出电视连接、K歌和观影一体化" --objective roi --duration 30
```

启动交互界面：

```bash
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

浏览器打开：

```text
http://127.0.0.1:8501
```

第 4 步生成分镜和关键帧：

```bash
python visual_agent/keyframe_storyboard_agent.py --generate-images
```

第 5 步生成 Seedance 视频请求计划：

```bash
python video_agent/seedance_video_agent.py
```

真正提交 Seedance 图生视频任务：

```bash
python video_agent/seedance_video_agent.py --submit
```

当前最终版视频生成流程、如何替换产品图、如何修改画面要求和念白，见：

```text
VIDEO_GENERATION_README.md
```

## RAG 实现说明

向量库包含三类集合：

- `video_cases`：完整案例，包含口播、标签、适用目标、高分原因等。
- `script_fragments`：可借鉴的脚本片段，服务 Hook、Setup、Twist、CTA 等局部生成。
- `strategy_rules`：从评价标准和高分经验中抽取的生成策略。

Agent 先根据 brief 检索相似案例与片段，再生成策划和四段式脚本。评分节点会读取 `内容评价标准库_v4.json`，找出不足项，再检索高分案例进行补足改写。

## 输出文件

- `outputs/final_script/final_script.json`：最终脚本专用 JSON，推荐后续 Agent 或程序直接读取。
- `outputs/final_script/final_script.md`：最终脚本 Markdown，方便人工查看和复制。
- `outputs/langgraph_real_rag_result.json`：命令行完整运行结果，包含检索证据、评分、运行轨迹等调试信息。
- `outputs/streamlit_last_result.json`：Streamlit 最近一次完整运行结果。
- `outputs/keyframes/`：分镜、关键帧提示词和关键帧图片。
- `outputs/videos/`：Seedance 请求计划、任务结果、视频片段和拼接结果。

`final_script.json` 是下游最稳定的接口，结构只保留最终使用信息：

- `planning`：最终使用的策划方案，包括目标人群、创意角度、核心痛点、核心卖点等。
- `script`：四段式脚本，包含 Hook、Setup、Twist、CTA 的画面、口播、字幕和镜头提示。
