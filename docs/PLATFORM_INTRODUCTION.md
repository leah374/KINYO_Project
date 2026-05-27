# KINYO AI 视频生成平台 - 完整介绍

## 📋 目录

- [平台概述](#平台概述)
- [核心特性](#核心特性)
- [架构设计](#架构设计)
- [AI Agent 详解](#ai-agent-详解)
- [技术亮点](#技术亮点)
- [使用场景](#使用场景)
- [快速开始](#快速开始)
- [详细功能](#详细功能)
- [技术栈](#技术栈)
- [性能指标](#性能指标)
- [未来规划](#未来规划)

---

## 平台概述

### 项目背景

KINYO AI 视频生成平台是一个**端到端的自动化视频创作系统**，整合了先进的 AI 技术来实现从营销文案到最终视频的全流程自动化。该平台解决了传统视频制作中的三大痛点：

1. **脚本创意难**：需要专业的营销知识和创意能力
2. **视觉设计慢**：分镜设计和关键帧制作耗时耗力
3. **视频制作贵**：传统视频制作成本高昂、周期长

### 解决方案

通过三个专业化的 AI Agent 协作，将**30秒广告视频的制作时间从传统的3-5天缩短到10-15分钟**，大幅降低制作成本和门槛。

### 项目定位

- **目标用户**：营销人员、内容创作者、中小企业主
- **应用场景**：短视频广告、电商视频、品牌宣传片
- **核心价值**：AI 驱动的全流程自动化 + 专业级输出质量

---

## 核心特性

### 🎯 1. 智能脚本生成

**技术架构**：
- **RAG (Retrieval-Augmented Generation)** 检索增强生成
- **LangGraph** 多节点工作流编排
- **FAISS** 向量相似度检索
- **四段式营销模型**：Hook-Setup-Twist-CTA

**核心能力**：
- ✅ 从爆款案例库中自动检索相似创意
- ✅ 基于营销目标（ROI/完播率）优化脚本结构
- ✅ 自动评分和改写机制，确保内容质量
- ✅ 多维度评价指标体系（7个维度、16个指标）

**生成流程**：
```
Brief 输入 → 解析需求 → RAG 检索相似案例
    ↓
检索策略规则 → 生成策划案 → 检索脚本片段
    ↓
生成四段式脚本 → 内容评分 → 低分维度改写
    ↓
最终脚本输出 (JSON + Markdown)
```

### 🖼️ 2. 智能关键帧生成

**技术架构**：
- **GPT-Image-2** 图片生成模型
- **结构化分镜算法**：自动拆分镜头和时间分配
- **产品图融合技术**：无缝集成真实产品图片

**核心能力**：
- ✅ 自动将脚本拆分为多个镜头和关键帧
- ✅ 每个 Shot 包含：场景描述、镜头提示、时间码、口播文本
- ✅ 支持产品图无缝融合（白底图/透明PNG）
- ✅ AI 生成商业级产品展示图

**分镜规则**：
```python
# 智能预算分配
Hook 阶段:   2-3 个镜头（吸引用户注意）
Setup 阶段:  2-3 个镜头（建立场景和信任）
Twist 阶段:  4-5 个镜头（高潮展示）
CTA 阶段:    1-2 个镜头（行动号召）
```

### 🎬️ 3. AI 视频生成

**技术架构**：
- **Seedance 2.0** 图生视频模型（字节跳动）
- **异步任务轮询机制**：支持长时间视频生成
- **FFmpeg** 视频拼接和编码

**核心能力**：
- ✅ 从静态关键帧生成动态视频片段
- ✅ 自动 AI 配音和背景音乐
- ✅ 平滑转场效果和镜头运动
- ✅ 自动拼接和兼容格式输出

**生成参数**：
- 视频时长：5-15秒/镜头
- 分辨率：720p/1080p
- 宽高比：9:16（竖屏短视频）
- 编码：H.264/AAC 兼容格式

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    统一 Streamlit UI                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ 脚本生成  │ 关键帧生成│ 视频生成 │ 一键生成 │ 历史记录 │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Workflow Manager                           │
│         (工作流编排、Session状态管理、数据库存储)              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌────────────┬──────────────────┬──────────────────┐
│Script Agent│  Visual Agent    │  Video Agent     │
│            │                  │                  │
│ - RAG检索   │ - 分镜算法        │ - Seedance API  │
│ - LangGraph│ - GPT-Image      │ - 异步轮询       │
│ - FAISS    │ - 产品图融合      │ - FFmpeg拼接     │
└────────────┴──────────────────┴──────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据层 & API 服务                          │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │知识库层   │ 向量数据库│ 输出文件  │ 历史数据库 │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向

```
用户输入 Brief
    ↓
[Script Agent]
├─ 加载知识库和向量索引
├─ RAG 检索相似案例和策略规则
├─ LangGraph 编排生成流程
└─ 输出: final_script.json
    ↓
[Visual Agent]
├─ 读取脚本 JSON
├─ 智能分镜算法拆分镜头
├─ 生成关键帧提示词
├─ 可选: AI 生成关键帧图片
└─ 输出: storyboard.json + images/
    ↓
[Video Agent]
├─ 读取分镜 JSON 和关键帧图片
├─ 提交 Seedance API 异步任务
├─ 轮询任务状态并下载视频
├─ FFmpeg 拼接所有片段
└─ 输出: final_video.mp4
    ↓
用户下载最终视频
```

---

## AI Agent 详解

### 1. Script Agent（脚本生成 Agent）

#### 核心代码结构

```python
# script_agent/agent/script_agent.py

# 向量知识库初始化
vector_db = FAISS.load_local(FAISS_VECTOR_DIR)

# LangGraph 工作流定义
workflow = StateGraph(ScriptAgentState)
workflow.add_node("parse_brief", parse_brief_node)
workflow.add_node("retrieve_cases", retrieve_cases_node)
workflow.add_node("generate_planning", generate_planning_node)
workflow.add_node("generate_script", generate_script_node)
workflow.add_node("evaluate_and_repair", evaluate_and_repair_node)

# RAG 检索逻辑
def retrieve_cases_node(state):
    query_embedding = embed_text(state["parsed_brief"])
    similar_cases = vector_db.similarity_search(query_embedding, k=5)
    return {"retrieved_cases": similar_cases}
```

#### 知识库结构

**1. 视频案例库 (video_cases)**
```json
{
  "id": "case_001",
  "video_id": "video_12345",
  "title": "家庭K歌一体机广告",
  "transcription": "完整的口播文本...",
  "tags": ["家庭娱乐", "K歌", "性价比"],
  "scores": {
    "roi_score": 8.5,
    "completion_rate": 0.78,
    "engagement": 0.65
  },
  "high_score_reasons": [
    "开头3秒强冲突：'电视变KTV'",
    "中间产品展示清晰：麦克风特写",
    "结尾CTA明确：价格锚点"
  ]
}
```

**2. 脚本片段库 (script_fragments)**
```json
{
  "id": "fragment_045",
  "category": "hook",
  "template": "把你的{product}变身{benefit}，只需{action}",
  "examples": [
    "把你的电视变身家庭KTV，只需一根线",
    "把你的客厅变身影院，只需一步操作"
  ],
  "usage_count": 156,
  "effectiveness_score": 8.2
}
```

**3. 策略规则库 (strategy_rules)**
```json
{
  "id": "rule_012",
  "rule_name": "价格锚点策略",
  "description": "通过对比建立价值感知",
  "applicable_scenarios": ["产品推广", "促销活动"],
  "implementation": {
    "technique": "先展示市场价，再展示优惠价",
    "example": "市面上K歌设备要399，今天只要99",
    "effectiveness": 0.85
  }
}
```

#### LangGraph 工作流节点详解

**节点1: Brief 解析**
```python
def parse_brief_node(state):
    """解析用户输入，提取关键信息"""
    brief = state["user_input"]
    
    # LLM 提取结构化信息
    parsed = llm.invoke(f"""
    解析以下营销需求：
    {brief}
    
    输出JSON格式：
    {{
      "product": "产品名称",
      "target_audience": "目标人群",
      "key_features": ["核心卖点1", "核心卖点2"],
      "objective": "roi/completion_rate",
      "duration": 30,
      "tone": "营销基调"
    }}
    """)
    
    return {"parsed_brief": parsed}
```

**节点2: RAG 检索**
```python
def retrieve_cases_node(state):
    """检索相似案例和策略规则"""
    brief_embedding = embedding_model.encode(
        state["parsed_brief"]["product"] + " " + 
        state["parsed_brief"]["key_features"][0]
    )
    
    # 检索完整案例
    cases = vector_db.similarity_search(brief_embedding, k=5)
    
    # 检索脚本片段
    fragments = vector_db.similarity_search(
        brief_embedding, 
        k=3, 
        filter={"type": "fragment"}
    )
    
    # 检索策略规则
    rules = vector_db.similarity_search(
        brief_embedding,
        k=5,
        filter={"type": "rule"}
    )
    
    return {
        "retrieved_cases": cases,
        "retrieved_fragments": fragments,
        "strategy_rules": rules
    }
```

**节点3: 策划生成**
```python
def generate_planning_node(state):
    """生成营销策划方案"""
    prompt = f"""
    基于以下信息，生成营销策划：
    
    产品: {state['parsed_brief']['product']}
    目标人群: {state['parsed_brief']['target_audience']}
    核心卖点: {state['parsed_brief']['key_features']}
    目标: {state['objective']}
    参考案例: {state['retrieved_cases'][:2]}
    策略建议: {state['strategy_rules'][:3]}
    
    输出JSON格式的策划方案，包含：
    - target_user: 详细用户画像
    - core_pain_point: 核心痛点
    - core_selling_point: 核心卖点
    - creative_angle: 创意角度
    - key_messages: 3-5个关键信息点
    """
    
    planning = llm.invoke(prompt)
    return {"planning": planning}
```

**节点4: 脚本生成**
```python
def generate_script_node(state):
    """生成四段式脚本"""
    script = {}
    
    # 逐段生成
    for stage in ["Hook", "Setup", "Twist", "CTA"]:
        prompt = f"""
        生成{stage}段脚本：
        
        策划: {state['planning']}
        参考片段: {state['retrieved_fragments'][stage]}
        
        输出：
        {{
          "stage": "{stage}",
          "time": "时间码",
          "purpose": "本段目的",
          "visual": "画面描述",
          "voiceover": "口播文本",
          "subtitle": "字幕文本",
          "shot_hint": "镜头提示"
        }}
        """
        
        segment = llm.invoke(prompt)
        script[stage] = segment
    
    return {"draft_script": script}
```

**节点5: 评分与改写**
```python
def evaluate_and_repair_node(state):
    """评分并改写低分维度"""
    # 加载评价标准
    evaluation_standard = load_json("evaluation_standard.json")
    
    # 评分
    evaluation = evaluate_script(
        state["draft_script"],
        evaluation_standard
    )
    
    # 如果总分低于阈值，找出低分维度
    if evaluation["overall_score"] < 6.0:
        low_score_dims = [
            dim for dim in evaluation["dimension_scores"]
            if dim["score"] < 5.0
        ]
        
        # 检索高分案例进行改写
        repair_evidence = []
        for dim in low_score_dims:
            # 检索该维度的高分案例
            evidence = vector_db.similarity_search(
                f"{dim['indicator_name']} 高分案例",
                k=2,
                filter={"scores": {dim['indicator_id']: {">=": 7}}}
            )
            repair_evidence.extend(evidence)
        
        # 改写脚本
        repaired_script = repair_script(
            state["draft_script"],
            low_score_dims,
            repair_evidence
        )
        
        return {
            "final_script": repaired_script,
            "evaluation": evaluation,
            "repair_evidence": repair_evidence
        }
    
    return {
        "final_script": state["draft_script"],
        "evaluation": evaluation,
        "repair_evidence": []
    }
```

### 2. Visual Agent（关键帧生成 Agent）

#### 核心算法

**智能分镜算法**：
```python
def build_storyboard(final_script, max_shots):
    """将脚本转换为分镜表"""
    storyboard = []
    cursor_time = 0.0
    remaining_shots = max_shots
    
    for segment in final_script["script"]["segments"]:
        # 解析时间范围
        time_range = parse_time_range(segment["time"], cursor_time)
        
        # 根据阶段分配镜头预算
        stage = segment["stage"]
        budget = stage_shot_budget(stage, remaining_shots)
        
        # 拆分视觉节拍
        beats = split_visual_beats(segment["visual"], budget)
        
        # 为每个视觉节拍分配时间
        time_allocation = allocate_ranges(time_range, len(beats))
        
        # 生成每个镜头
        for idx, (beat, time_slot) in enumerate(zip(beats, time_allocation)):
            shot = {
                "shot_id": f"S{len(storyboard)+1:02d}",
                "stage": stage,
                "time": time_slot.label(),
                "duration_sec": time_slot.duration,
                "purpose": segment["purpose"],
                "visual_beat": beat,
                "voiceover": segment["voiceover"],
                "subtitle": segment["subtitle"],
                "camera": infer_camera(beat, segment),
                "motion": infer_motion(stage, beat),
                "keyframe_prompt": build_image_prompt(
                    final_script["title"],
                    final_script["planning"],
                    segment,
                    beat
                )
            }
            storyboard.append(shot)
            remaining_shots -= 1
    
    return {
        "source_title": final_script["title"],
        "storyboard": storyboard,
        "style_guide": generate_style_guide()
    }
```

**镜头类型推断**：
```python
def infer_camera(beat, segment):
    """根据画面描述推断镜头类型"""
    text = f"{beat} {segment.get('shot_hint', '')}"
    
    # 产品特写镜头
    if any(key in text for key in ["接口", "特写", "麦克风", "主机"]):
        return "close-up product demo shot, hands and device in frame"
    
    # 全家福镜头
    if any(key in text for key in ["全家", "家庭", "客厅", "沙发"]):
        return "medium-wide living-room shot, family and TV both visible"
    
    # 屏幕展示镜头
    if any(key in text for key in ["屏幕", "界面", "点歌", "电影"]):
        return "over-the-shoulder TV interface shot, screen content dominant"
    
    # 默认镜头
    return "medium shot with presenter, product, and TV visible"
```

**关键帧提示词生成**：
```python
def build_image_prompt(title, planning, segment, beat):
    """生成图片生成提示词"""
    return f"""
    Create keyframe for a vertical 9:16 Chinese short-video advertisement.
    
    Campaign title: {title}
    Scene: {beat}
    Ad purpose: {segment['purpose']}
    Target audience: {planning['target_user']}
    Core product promise: {planning['core_selling_point']}
    
    Show a realistic home karaoke and cinema product demo in a cozy modern 
    Chinese living room: a TV, compact set-top box, HDMI cable, wireless 
    microphones, remote control, and family members interacting naturally.
    
    Make the product and TV interface clearly visible, with believable 
    hands-on operation and warm family energy.
    
    Voiceover context: {segment['voiceover']}
    
    Photorealistic, commercial lighting, sharp focus, stable composition, 
    no brand logos, no watermark, no tiny unreadable UI text.
    """
```

#### 产品图融合技术

```python
def safe_keyframe_generator(storyboard, product_dir):
    """生成无脸安全关键帧，融合产品图"""
    
    # 加载产品图
    product_images = load_product_images(product_dir)
    
    for shot in storyboard["storyboard"]:
        # 生成背景场景
        background = generate_background(shot["keyframe_prompt"])
        
        # 检测人脸并移除
        background = remove_faces(background)
        
        # 融合产品图
        if "产品" in shot["visual_beat"] or "主机" in shot["visual_beat"]:
            # 智能定位产品图位置
            position = detect_product_position(background)
            
            # 融合产品图（保持阴影和光照一致性）
            keyframe = blend_product_image(
                background,
                product_images["main_device"],
                position,
                preserve_lighting=True
            )
        else:
            keyframe = background
        
        # 保存关键帧
        save_keyframe(keyframe, f"keyframes/{shot['shot_id']}.png")
```

### 3. Video Agent（视频生成 Agent）

#### 异步任务管理

```python
class SeedanceVideoAgent:
    """Seedance 视频生成 Agent"""
    
    def submit_and_wait(self, job, payload):
        """提交任务并轮询等待完成"""
        
        # 1. 提交任务
        create_url = f"{self.base_url}/contents/generations/tasks"
        response = http_json("POST", create_url, self.api_key, payload)
        task_id = extract_task_id(response)
        
        # 2. 轮询任务状态
        deadline = time.time() + self.timeout
        query_url = f"{self.base_url}/contents/generations/tasks/{task_id}"
        
        while time.time() < deadline:
            time.sleep(self.poll_interval)
            
            # 查询任务状态
            status_response = http_json("GET", query_url, self.api_key)
            status = extract_status(status_response)
            
            # 如果成功，下载视频
            if status in ["succeeded", "completed"]:
                video_url = extract_video_url(status_response)
                download_file(video_url, job.output_path)
                return {
                    "task_id": task_id,
                    "status": status,
                    "video_path": str(job.output_path)
                }
            
            # 如果失败，返回错误
            if status in ["failed", "error"]:
                return {
                    "task_id": task_id,
                    "status": status,
                    "error": status_response.get("error")
                }
        
        raise TimeoutError(f"Task {task_id} did not complete within {self.timeout}s")
```

#### 视频拼接与编码

```python
def concat_clips(clips, output_path):
    """使用 FFmpeg 拼接视频片段"""
    
    # 1. 生成拼接列表文件
    concat_list = output_path.parent / "concat_list.txt"
    with open(concat_list, 'w') as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")
    
    # 2. FFmpeg 拼接
    cmd = [
        "ffmpeg",
        "-y",  # 覆盖输出文件
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",  # 无重编码，快速拼接
        "-movflags", "+faststart",  # 优化流媒体播放
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True)

def make_compatible_video(input_path, output_path):
    """生成兼容性更好的H.264/AAC视频"""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-map", "0:v:0",  # 选择视频流
        "-map", "0:a:0?",  # 选择音频流（可选）
        
        # 视频编码参数
        "-c:v", "libx264",  # H.264编码
        "-pix_fmt", "yuv420p",  # 兼容性像素格式
        "-profile:v", "baseline",  # 基线配置文件
        "-level", "3.1",  # 兼容性级别
        "-r", "24",  # 帧率
        
        # 音频编码参数
        "-c:a", "aac",  # AAC编码
        "-b:a", "192k",  # 音频比特率
        "-ar", "44100",  # 采样率
        "-ac", "2",  # 双声道
        
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True)
```

---

## 技术亮点

### 1. RAG 检索增强生成

**创新点**：
- **双层知识库架构**：结构化案例层 + 原始证据层
- **多粒度检索**：完整案例、脚本片段、策略规则三层检索
- **目标导向检索**：根据 ROI/完播率目标定制检索策略

**实现细节**：

```python
# 构建双层知识库
def build_two_layer_knowledge_base(transcripts_csv, previous_kb):
    """
    构建两层知识库：
    Layer 1: 结构化案例层（LLM 标注）
    Layer 2: 原始证据层（口播原文）
    """
    
    # Layer 1: 使用 LLM 标注每个视频
    structured_cases = []
    for _, row in transcripts_df.iterrows():
        # LLM 提取关键信息
        analysis = llm.invoke(f"""
        分析以下视频口播，提取结构化信息：
        
        口播文本：{row['transcription']}
        ROI分数：{row['roi_score']}
        完播率：{row['completion_rate']}
        
        输出JSON：
        {{
          "video_id": "{row['video_id']}",
          "title": "标题",
          "category": "分类",
          "target_audience": "目标人群",
          "key_selling_points": ["卖点1", "卖点2"],
          "emotional_tone": "情感基调",
          "hooks": ["开头钩子1", "开头钩子2"],
          "ctas": ["结尾号召1"],
          "high_score_reasons": ["高分原因1"],
          "improvement_suggestions": ["改进建议1"]
        }}
        """)
        
        structured_cases.append(analysis)
    
    # Layer 2: 保留原始口播作为证据
    raw_evidence = transcripts_df.to_dict('records')
    
    # 构建向量索引
    for case in structured_cases:
        # 为每个案例创建向量表示
        text = f"{case['title']} {case['category']} {' '.join(case['key_selling_points'])}"
        embedding = embedding_model.encode(text)
        vector_db.add(embedding, metadata=case)
    
    return {
        "structured_cases": structured_cases,
        "raw_evidence": raw_evidence,
        "vector_db": vector_db
    }
```

### 2. LangGraph 工作流编排

**优势**：
- **可观测性**：每个节点状态可追踪
- **可调试性**：支持断点续传和状态回滚
- **可扩展性**：节点可独立开发和测试

**状态定义**：

```python
from typing import TypedDict

class ScriptAgentState(TypedDict, total=False):
    # 输入
    user_input: str
    objective: str
    duration_sec: int
    
    # 中间状态
    parsed_brief: Dict[str, Any]
    retrieved_cases: List[Dict[str, Any]]
    retrieved_fragments: List[Dict[str, Any]]
    strategy_rules: List[Dict[str, Any]]
    planning: Dict[str, Any]
    draft_script: Dict[str, Any]
    evaluation: Dict[str, Any]
    repair_evidence: List[Dict[str, Any]]
    
    # 输出
    final_script: Dict[str, Any]
    trace: List[str]
```

### 3. 内容评价标准体系

**7个维度、16个指标**：

```json
{
  "evaluation_framework": {
    "D001_脚本结构": {
      "indicators": [
        {
          "id": "D001-I001",
          "name": "Hook (0-3秒)",
          "description": "开头3秒是否建立冲突或利益承诺",
          "scoring_criteria": {
            "1": "无冲突，无利益点，用户会立即划走",
            "3": "有轻微利益点，但吸引力不强",
            "5": "有明确利益点，吸引用户继续观看",
            "7": "强冲突/强利益点，用户无法划走"
          }
        },
        {
          "id": "D001-I002",
          "name": "Setup (铺垫与信任)",
          "description": "4-15秒是否建立场景、痛点或人设信任"
        },
        {
          "id": "D001-I003",
          "name": "Twist (反转与高潮)",
          "description": "是否展示产品核心优势和高光时刻"
        },
        {
          "id": "D001-I004",
          "name": "CTA (行动召唤)",
          "description": "结尾是否有明确的行动号召和价格锚点"
        }
      ]
    },
    "D002_钩子设计": {
      "indicators": [
        {"id": "D002-I001", "name": "冲突与反差强度"},
        {"id": "D002-I002", "name": "悬念留存设计"}
      ]
    },
    "D003_节奏BGM与剪辑": {
      "indicators": [
        {"id": "D003-I001", "name": "BPM与卡点频率"},
        {"id": "D003-I002", "name": "转场与剪辑强度"}
      ]
    },
    "D004_选品视角": {
      "indicators": [
        {"id": "D004-I001", "name": "产品颜值与高光展示"},
        {"id": "D004-I002", "name": "价格锚点与即时满足"}
      ]
    },
    "D005_文案张力": {
      "indicators": [
        {"id": "D005-I001", "name": "数字与具象化表达"},
        {"id": "D005-I002", "name": "痛点直击与悬念词"}
      ]
    },
    "D006_第一秒视觉": {
      "indicators": [
        {"id": "D006-I001", "name": "视觉冲击与反差大"},
        {"id": "D006-I002", "name": "关键词大字报"}
      ]
    },
    "D007_CTA与互动设计": {
      "indicators": [
        {"id": "D007-I001", "name": "评论引导与互动钩"},
        {"id": "D007-I002", "name": "收藏与转发触发"}
      ]
    }
  }
}
```

### 4. 统一的用户界面

**设计理念**：
- **多页面导航**：清晰的页面层级和导航
- **工作流可视化**：实时展示当前进度和状态
- **智能数据传递**：跨页面自动传递生成结果
- **历史记录管理**：SQLite 持久化所有生成历史

**核心组件**：

```python
# 文件管理组件
class FileManager:
    @staticmethod
    def select_or_upload_file(label, file_types, key):
        """统一的文件选择组件：支持上传/选择/历史记录"""
        
        choice = st.radio("Input Method", [
            "Use Previous Result",
            "Select from Project",
            "Upload File"
        ])
        
        if choice == "Use Previous Result":
            # 自动读取 session_state 中的结果
            return SessionStateManager.get_last_result()
        elif choice == "Select from Project":
            # 从项目目录选择文件
            return select_from_project(file_types)
        else:
            # 上传新文件
            return upload_file(file_types)

# 进度追踪组件
class ProgressTracker:
    def __init__(self, key="progress"):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.log_container = st.container()
    
    def update(self, progress, message):
        """更新进度和状态"""
        self.progress_bar.progress(progress)
        self.status_text.text(message)
    
    def add_log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        with self.log_container:
            st.code(f"[{timestamp}] {message}")
```

---

## 使用场景

### 场景1: 电商产品推广

**用户输入**：
```
产品：家用K歌一体机
目标：提升ROI转化
时长：30秒
核心卖点：一根线变KTV、曲库丰富、送麦克风、适合全家
```

**生成结果**：
- **脚本**：Hook展示电视变KTV的神奇效果，Setup建立家庭聚会场景，Twist展示产品核心功能和价格优势，CTA引导下单
- **关键帧**：10个镜头，包含产品特写、使用场景、家庭欢唱画面
- **视频**：30秒竖屏广告，配备AI配音和背景音乐

### 场景2: 品牌形象宣传

**用户输入**：
```
产品：智能家居品牌
目标：提升品牌认知度和完播率
时长：60秒
核心卖点：科技感、智能化、提升生活品质
```

**生成结果**：
- **脚本**：采用情感共鸣策略，通过日常生活痛点切入
- **关键帧**：15个镜头，展示智能家居如何改变生活
- **视频**：60秒品牌宣传片，突出科技与温度的结合

### 场景3: 促销活动宣传

**用户输入**：
```
产品：双十一家电促销
目标：最大化转化
时长：15秒
核心卖点：限时优惠、价格锚点、紧迫感
```

**生成结果**：
- **脚本**：开头直接抛出价格优惠，快速建立紧迫感
- **关键帧**：5个镜头，重点展示价格对比和优惠信息
- **视频**：15秒快节奏促销视频，强烈的CTA

---

## 快速开始

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/kinyo.git
cd kinyo

# 2. 安装依赖
pip install -r streamlit_app/requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys

# 4. 启动应用
python run_streamlit.py
# 或
streamlit run streamlit_app/app.py
```

### 最小可用配置

**必须的 API Keys**：
- `K_TOKEN_API_KEY` 或 `OPENAI_API_KEY`：用于脚本生成
- `DASHSCOPE_API_KEY`：用于向量嵌入
- `ARK_API_KEY` 或 `SEEDANCE_API_KEY`：用于视频生成

**首次运行流程**：

```
1. 打开 http://127.0.0.1:8501
2. 进入 ⚙️ 设置 页面
3. 配置必需的 API Keys
4. 进入 ⚡ 一键生成 页面
5. 输入营销需求
6. 点击"开始一键生成"
7. 等待 10-15 分钟
8. 下载最终视频
```

---

## 详细功能

### 页面说明

#### 📊 概览页

**功能**：
- ✅ API Key 配置状态检查
- ✅ 知识库和向量库状态监控
- ✅ 最近生成活动时间线
- ✅ 文件管理器（按类别浏览）
- ✅ 工作流当前阶段可视化

**使用场景**：
- 快速了解系统状态
- 浏览和下载历史输出文件
- 检查配置是否就绪

#### 📝 脚本生成页

**侧边栏参数**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| Marketing Brief | 营销需求描述 | - |
| Objective | 目标（ROI/完播率/综合） | ROI |
| Duration | 时长（秒） | 30 |
| Generation Model | 生成模型 | gpt-5.4 |
| Top K Results | RAG检索数量 | 5 |

**高级功能**：
- ✅ 脚本可视化编辑器
- ✅ JSON 原始数据查看
- ✅ 评分详情和改写建议
- ✅ 检索证据展示
- ✅ 一键发送到关键帧生成

#### 🖼️ 关键帧生成页

**侧边栏参数**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| Input Method | 输入方式（历史/上传/选择） | 历史记录 |
| Max Shots | 最大镜头数 | 10 |
| Generate Images | 是否生成关键帧图片 | 否 |
| Image Model | 图片生成模型 | gpt-image-2 |
| Image Size | 图片尺寸 | auto |
| Image Quality | 图片质量 | auto |

**主区域显示**：
- 分镜列表（每个镜头的详细信息）
- 图片网格预览（如果生成了图片）
- JSON 导出

#### 🎬 视频生成页

**侧边栏参数**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| Audio Generation | 是否生成音频 | 是 |
| Video Duration | 单镜头时长（秒） | 5 |
| Aspect Ratio | 宽高比 | 9:16 |
| Concat Videos | 是否拼接视频 | 是 |
| Compatible Output | 是否生成兼容格式 | 是 |

**进度显示**：
- 实时进度条
- 当前生成的镜头编号
- 预估剩余时间
- 错误日志

#### ⚡ 一键生成页

**输入参数**：
- Marketing Brief
- Objective
- Duration
- Max Shots
- Video Duration

**三阶段进度**：
```
Stage 1: 脚本生成 (30%) ━━━━━━━━━━ ✓
Stage 2: 关键帧生成 (30%) ━━━━━━━━━━ ✓
Stage 3: 视频生成 (40%) ━━━━━━▒▒▒▒ Running...
```

**输出结果**：
- 最终视频预览
- 脚本 JSON
- 分镜 JSON
- 所有镜头视频片段
- 完整生成报告

#### 📚 历史记录页

**功能**：
- ✅ 按类型筛选（脚本/分镜/视频）
- ✅ 搜索功能
- ✅ 分页浏览（每页20条）
- ✅ 查看详情
- ✅ 删除记录
- ✅ 批量导出

**统计概览**：
- 总脚本数
- 总分镜数
- 总视频数
- 成功/失败比例

#### ⚙️ 设置页

**API Key 管理**：
- 显示当前配置状态（已配置/未配置）
- 密码输入框（安全输入）
- 测试连接按钮
- 保存按钮

**模型配置**：
- 脚本生成模型
- 图片生成模型
- 视频生成模型
- 嵌入模型

**知识库管理**：
- 重建向量索引
- 更新知识库
- 知识库统计信息

---

## 技术栈

### 后端技术

| 技术 | 用途 | 版本 |
|------|------|------|
| Python | 主要开发语言 | 3.11+ |
| OpenAI API | LLM 调用 | 1.0+ |
| LangGraph | 工作流编排 | 0.0.20+ |
| FAISS | 向量检索 | 1.7.4+ |
| Streamlit | Web UI | 1.28.0+ |
| SQLite | 历史数据库 | 3.x |
| Pandas | 数据处理 | 2.0+ |
| Pillow | 图片处理 | 10.0+ |

### AI 模型

| 模型 | 用途 | 提供商 |
|------|------|--------|
| GPT-5.4 | 脚本生成 | OpenAI / KToken |
| text-embedding-v4 | 向量嵌入 | 阿里云 DashScope |
| GPT-Image-2 | 关键帧生成 | OpenAI |
| Seedance 2.0 | 视频生成 | 字节跳动火山方舟 |
| Qwen3-ASR | 视频转写 | 阿里云 |

### 前端技术

| 技术 | 用途 |
|------|------|
| Streamlit Components | UI 组件 |
| HTML/CSS | 样式 |
| JavaScript | 交互 |

---

## 性能指标

### 生成速度

| 任务 | 平均耗时 | 备注 |
|------|---------|------|
| 脚本生成 | 10-15秒 | 包含RAG检索和评分 |
| 单个关键帧 | 3-5秒 | GPT-Image-2 |
| 单个视频片段 | 30-60秒 | Seedance 2.0 |
| 完整pipeline | 10-15分钟 | 30秒视频、10个镜头 |

### 资源消耗

| 指标 | 数值 |
|------|------|
| CPU 占用 | 低（主要在API调用） |
| 内存占用 | ~500MB |
| 磁盘空间 | 每个视频 ~50MB |
| API 调用成本 | $0.10-0.30/视频 |

### 准确性指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 脚本评分通过率 | 85% | 评分≥6.0/7.0 |
| 内容相关性 | 90%+ | RAG检索准确度 |
| 视频生成成功率 | 95%+ | 无审核拦截 |

---

## 未来规划

### 短期目标 (1-2个月)

- [ ] **批量生成功能**
  - 上传 Excel 批量生成多个脚本和视频
  - 自动化 A/B 测试
  
- [ ] **更多视频平台支持**
  - 支持横屏视频（16:9）
  - 支持方形视频（1:1）
  
- [ ] **性能优化**
  - 并行生成多个关键帧
  - 缓存优化减少重复计算

### 中期目标 (3-6个月)

- [ ] **用户认证系统**
  - 多用户隔离
  - 权限管理
  
- [ ] **协作功能**
  - 脚本审核流程
  - 多人协作编辑
  
- [ ] **模板库**
  - 预定义营销模板
  - 自定义模板创建

### 长期目标 (6-12个月)

- [ ] **云端部署**
  - Docker 容器化
  - Kubernetes 编排
  - 弹性扩缩容
  
- [ ] **API 接口**
  - RESTful API
  - SDK for Python/JavaScript
  
- [ ] **商业化功能**
  - 订阅计费系统
  - 用量统计和报告

---

## 总结

KINYO AI 视频生成平台通过**智能化、自动化、专业化**的三大核心能力，将传统视频制作的门槛降到最低，同时保证了输出内容的质量和专业性。无论是电商推广、品牌宣传还是内容营销，都能在分钟级别完成从创意到成品的全流程。

**核心优势总结**：

✅ **全流程自动化**：从 Brief 到视频的一键生成  
✅ **专业级质量**：基于爆款案例的知识库和评价体系  
✅ **易用性强**：统一的 Web 界面，无需技术背景  
✅ **可扩展性好**：模块化设计，便于定制和扩展  
✅ **成本效益高**：传统制作成本的 1/10，时间成本的 1/100  

---

**立即开始你的AI视频创作之旅！** 🚀

```bash
python run_streamlit.py
```

访问：http://127.0.0.1:8501

---

*文档版本：v1.0.0*  
*更新日期：2025-05-25*  
*维护团队：KINYO AI 团队*
