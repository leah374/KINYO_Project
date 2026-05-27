# KINYO AI 视频生成平台 - User Guide

## 目录

1. [快速开始](#快速开始)
2. [界面导航](#界面导航)
3. [功能详解](#功能详解)
4. [常见问题](#常见问题)
5. [最佳实践](#最佳实践)

---

## 快速开始

### 第一步：安装和启动

#### 安装依赖

```bash
pip install -r streamlit_app/requirements.txt
```

#### 启动应用

**Windows:**
```powershell
# 方法1: 双击批处理文件
start_streamlit.bat

# 方法2: 命令行启动
python run_streamlit.py

# 方法3: 直接运行
streamlit run streamlit_app/app.py
```

**Mac/Linux:**
```bash
python run_streamlit.py
# 或
streamlit run streamlit_app/app.py
```

#### 访问界面

启动后，浏览器自动打开或手动访问：

```
http://127.0.0.1:8501
```

### 第二步：配置 API Keys

1. 点击侧边栏的 **⚙️ 设置** 页面
2. 填写必需的 API Keys：
   - **K Token API Key** 或 **OpenAI API Key**（脚本生成）
   - **DashScope API Key**（向量嵌入）
   - **ARK API Key** 或 **Seedance API Key**（视频生成）
3. 点击每个 Key 的 **Test** 按钮验证连接
4. 点击 **Save** 保存配置

### 第三步：生成第一个视频

**方法A：一键生成（推荐新手）**

1. 点击侧边栏的 **⚡ 一键生成** 页面
2. 在 **Marketing Brief** 输入框填写你的营销需求
   ```
   示例：
   做一条30秒的家用K歌一体机广告，目标提升转化率，
   突出一根线变KTV、曲库丰富、送麦克风、适合家庭聚会
   ```
3. 选择目标（ROI/完播率/综合）
4. 点击 **开始一键生成**
5. 等待10-15分钟，观看实时进度
6. 点击 **下载最终视频**

**方法B：分步生成（更多控制）**

1. 进入 **📝 脚本生成** 页面
2. 输入营销需求，点击 **🚀 Generate Script**
3. 查看生成的脚本，可在 **Editor** 标签页编辑
4. 点击 **→ Send to Storyboard Generation**
5. 在 **🖼️ 关键帧生成** 页面，设置参数并生成分镜
6. 点击 **→ 发送到视频生成**
7. 在 **🎬 视频生成** 页面，点击 **开始生成**
8. 等待视频生成完成并下载

---

## 界面导航

### 侧边栏

侧边栏显示以下信息：

```
┌─────────────────────┐
│   KINYO AI          │
│   视频生成平台        │
├─────────────────────┤
│ System Status:      │
│ ✓ Script            │
│ ✓ Embedding         │
│ ✓ Video             │
├─────────────────────┤
│ Statistics:         │
│ Scripts: 12         │
│ Storyboards: 8      │
│ Videos: 5           │
├─────────────────────┤
│ Workflow:           │
│ Current: script_    │
│   generated         │
├─────────────────────┤
│ Quick Actions:      │
│ [Clear Session]     │
│ [Go to Script Gen]  │
├─────────────────────┤
│ Pages:              │
│ 📊 概览             │
│ 📝 脚本生成          │
│ 🖼️ 关键帧生成        │
│ 🎬 视频生成          │
│ ⚡ 一键生成          │
│ 📚 历史记录          │
│ ⚙️ 设置             │
└─────────────────────┘
```

### 主要页面说明

#### 📊 概览页

- **Quick Start**: 快速入门指南和常用操作按钮
- **Dashboard**: 系统状态、统计数据、最近活动
- **Workflow**: 当前工作流进度可视化
- **File Manager**: 按类别浏览所有输出文件

#### 📝 脚本生成页

**侧边栏输入**：
- Marketing Brief（营销需求）
- Objective（目标：ROI/完播率/综合）
- Duration（时长：10-120秒）
- Advanced Options（高级选项）

**主区域输出**：
- 📜 Final Script：最终脚本（四段式展示）
- 📊 Evaluation：评分结果和改进建议
- 🔍 Evidence：RAG 检索证据
- 📖 Retrieved Cases：检索到的相似案例
- 📝 Editor：可视化脚本编辑器
- 💾 Export：导出和传递到下一阶段

#### 🖼️ 关键帧生成页

**输入方式**：
- Use Previous Result：使用脚本生成结果
- Select from Project：从项目目录选择
- Upload File：上传新的脚本 JSON

**设置参数**：
- Max Shots：最大镜头数（1-20）
- Generate Images：是否生成关键帧图片
- Image Model：图片生成模型
- Image Size/Quality：图片尺寸和质量

**输出展示**：
- Storyboard List：分镜列表
- Image Preview：图片网格预览
- JSON Export：JSON 导出和下载

#### 🎬 视频生成页

**输入**：
- Storyboard JSON：分镜文件
- Keyframe Directory：关键帧图片目录

**视频参数**：
- Duration per Shot：单个镜头时长
- Aspect Ratio：宽高比（9:16/16:9/1:1）
- Generate Audio：是否生成音频
- Concat Videos：是否拼接视频
- Compatible Output：是否生成兼容格式

**进度监控**：
- 实时进度条
- 当前任务状态
- 日志输出
- 错误提示

#### ⚡ 一键生成页

**三阶段流程**：
```
Stage 1: 脚本生成 (30%)
  ├─ Brief 解析
  ├─ RAG 检索
  ├─ 策划生成
  ├─ 脚本生成
  └─ 评分改写

Stage 2: 关键帧生成 (30%)
  ├─ 分镜拆分
  ├─ 提示词生成
  └─ 图片生成（可选）

Stage 3: 视频生成 (40%)
  ├─ API 提交
  ├─ 异步轮询
  ├─ 下载片段
  └─ FFmpeg 拼接
```

**输出**：
- 最终视频预览
- 完整结果包下载
- 各阶段 JSON 文件

#### 📚 历史记录页

**功能**：
- 按类型筛选（脚本/分镜/视频）
- 搜索功能
- 查看详情
- 删除记录
- 批量导出

**统计信息**：
- 总记录数
- 成功/失败比例
- 存储空间占用

#### ⚙️ 设置页

**API Keys 管理**：
- 各 API Key 的配置状态
- 测试连接功能
- 安全保存到 .env 文件

**模型配置**：
- 脚本生成模型选择
- 图片生成模型选择
- 视频生成模型选择

**知识库管理**：
- 重建向量索引
- 更新知识库
- 查看统计信息

---

## 功能详解

### 1. 营销 Brief 编写指南

**好的 Brief 应包含**：
- 产品/服务名称
- 核心卖点（3-5个）
- 目标受众
- 营销目标（转化/品牌认知/用户教育）
- 视频时长
- 语气风格

**示例对比**：

❌ **不好的 Brief**：
```
做一个K歌产品的广告
```

✅ **好的 Brief**：
```
产品：家用K歌一体机（型号K7）
目标：提升ROI转化，适合电商推广
时长：30秒竖屏短视频
核心卖点：
1. 一根线让普通电视变KTV（核心差异化）
2. 10万+曲库，实时更新
3. 送无线麦克风（价值锚点）
4. 适合全家老少使用

目标受众：30-45岁家庭用户，有老人和小孩
语气：温馨、实用、性价比高
特殊要求：突出家庭聚会场景
```

### 2. 目标选择策略

**ROI（投资回报率）导向**：
- 适合：电商平台、促销活动、转化广告
- 特点：强调价格、优惠、购买引导
- 结构：Hook快节奏 + CTA强烈

**Completion Rate（完播率）导向**：
- 适合：品牌宣传、内容营销、用户教育
- 特点：故事性强、情感共鸣
- 结构：Setup充分 + Twist吸引人

**Balanced（综合）**：
- 适合：品牌+转化兼顾
- 特点：平衡卖点和故事性
- 结构：四段均衡分配

### 3. 脚本编辑技巧

**Editor 标签页功能**：
- **Planning 编辑**：修改目标用户、卖点、创意角度
- **Segments 编辑**：逐段修改画面、口播、字幕
- **Raw JSON 编辑**：直接编辑 JSON 结构

**常见编辑场景**：

1. **修改口播文本**：
   ```json
   {
     "voiceover": "原价399，今天只要99元！"
     // 改为
     "voiceover": "仅限今天，立省300元！"
   }
   ```

2. **调整画面描述**：
   ```json
   {
     "visual": "展示产品外观"
     // 改为
     "visual": "特写产品正面，LED灯亮起，科技感十足"
   }
   ```

3. **修改时间码**：
   ```json
   {
     "time": "0-3秒"
     // 改为
     "time": "0-5秒"  // Hook 可以稍长
   }
   ```

### 4. 关键帧生成参数调优

**Max Shots（最大镜头数）**：
- 15秒视频：5-7个镜头
- 30秒视频：8-12个镜头
- 60秒视频：15-20个镜头

**镜头分配建议**：
```
Hook:    2-3个镜头（快速吸引注意）
Setup:   2-3个镜头（建立信任）
Twist:   4-5个镜头（核心展示）
CTA:     1-2个镜头（行动号召）
```

**Generate Images 选项**：
- ✅ 勾选：AI 自动生成关键帧图片（更专业）
- ⬜ 不勾选：只生成分镜文本（速度快、成本低）

### 5. 视频生成参数优化

**Duration per Shot（单镜头时长）**：
- 快节奏广告：3-5秒/镜头
- 标准节奏：5-8秒/镜头
- 慢节奏品牌片：8-12秒/镜头

**Aspect Ratio（宽高比）**：
- 9:16：竖屏短视频（抖音/快手/视频号）
- 16:9：横屏视频（B站/YouTube/电视广告）
- 1:1：方形视频（Instagram/朋友圈）

**Audio Generation**：
- ✅ 推荐：AI 自动配音和背景音乐
- ⬜ 不勾选：后期手动添加音频

**Compatible Output**：
- ✅ 推荐：生成兼容性更好的 H.264/AAC 格式
- 好处：所有设备都能正常播放

### 6. 历史记录管理和批量操作

**搜索功能**：
- 按关键词搜索脚本内容
- 按文件名搜索输出文件
- 按时间范围筛选

**批量导出**：
1. 勾选多个历史记录
2. 点击 **Export Selected**
3. 下载 ZIP 压缩包

**历史记录详情**：
```
┌─────────────────────────────┐
│ Record ID: 15               │
│ Type: Script Generation     │
│ Timestamp: 2025-05-25 22:30 │
│                             │
│ Summary:                    │
│ - Brief: K7广告...          │
│ - Objective: ROI            │
│ - Duration: 30s             │
│ - Score: 6.8/7.0            │
│ - Status: ✓ Success         │
│                             │
│ Files:                      │
│ - final_script.json         │
│ - final_script.md           │
│                             │
│ [View Full JSON]            │
│ [Re-run] [Delete]           │
└─────────────────────────────┘
```

---

## 常见问题

### Q1: API Key 配置后没有保存？

**原因**：.env 文件权限问题或路径错误

**解决方法**：
1. 确认项目根目录存在 `.env` 文件
2. 如果不存在，手动创建：
   ```bash
   # Windows
   type nul > .env
   
   # Mac/Linux
   touch .env
   ```
3. 再次在设置页面点击 **Save**
4. 检查 .env 文件是否包含：
   ```
   K_TOKEN_API_KEY=sk-xxxxx
   DASHSCOPE_API_KEY=sk-xxxxx
   ARK_API_KEY=sk-xxxxx
   ```

### Q2: 脚本生成失败，提示"Index not found"？

**原因**：向量索引未构建

**解决方法**：
1. 进入 **📝 脚本生成** 页面
2. 点击侧边栏的 **Build Index** 按钮
3. 等待构建完成（约30秒）
4. 重新生成脚本

或者手动构建：
```bash
cd script_agent/agent
python script_agent.py --build-index
```

### Q3: 视频生成长时间无响应？

**可能原因**：
1. API Key 无效或余额不足
2. 网络连接问题
3. 任务队列拥堵

**解决方法**：
1. 在设置页面测试 API Key 连接
2. 检查网络是否正常
3. 查看 **History** 页面的错误日志
4. 尝试减少镜头数量或降低时长

### Q4: 生成的视频审核失败？

**常见原因**：
- 输入图片包含可识别人脸
- 提示词包含版权内容（真实歌曲名、影视名）
- 输出视频包含字幕或文字

**解决方法**：
1. 使用 **safe_keyframe_generator.py** 生成无脸关键帧
2. 在分镜提示词中强调：
   ```
   不出现真实歌名、影视名、平台名、商标
   视频画面中不要出现字幕、促销大字
   电视界面使用虚构分类和抽象图标
   ```

### Q5: 评分过低，脚本需要频繁改写？

**原因**：Brief 描述不够清晰或卖点不明确

**改进建议**：
1. 完善 Brief，增加具体信息和情感描述
2. 明确目标受众和核心卖点
3. 参考历史高分案例改进结构
4. 在 **Editor** 页面手动优化脚本

### Q6: 如何批量生成多个视频？

**当前版本**：暂不支持批量生成

**替代方案**：
1. 准备 Excel 文件，每行一个 Brief
2. 手动逐个输入并生成
3. 在 **History** 页面管理和导出

**未来版本**：将支持批量生成功能

### Q7: 生成的文件保存在哪里？

**输出目录结构**：
```
outputs/
├── final_script/
│   ├── final_script.json        # 最终脚本 JSON
│   └── final_script.md          # 最终脚本 Markdown
│
├── keyframes/
│   ├── storyboard.json          # 分镜表 JSON
│   ├── images/                  # 关键帧图片
│   │   ├── S01.png
│   │   └── S02.png
│   └── image_prompts.jsonl      # 图片提示词
│
├── videos/
│   ├── clips/                   # 单个镜头视频
│   │   ├── S01.mp4
│   │   └── S02.mp4
│   ├── final_seedance_video.mp4 # 拼接后视频
│   └── final_seedance_video_compatible.mp4 # 兼容格式
│
└── script_outputs/
    ├── script_complete_result.json    # 完整生成结果
    └── streamlit_last_result.json     # Streamlit 最后结果
```

### Q8: 如何自定义生成风格？

**方法1：修改评价标准库**
编辑 `script_agent/knowledge_base/evaluation_standard.json`

**方法2：修改分镜提示词模板**
编辑 `visual_agent/agent/keyframe_storyboard_agent.py` 中的 `build_image_prompt()` 函数

**方法3：修改视频提示词模板**
编辑 `video_agent/agent/seedance_video_agent.py` 中的 `build_seedance_prompt()` 函数

---

## 最佳实践

### 1. Brief 编写最佳实践

✅ **DO**:
- 提供具体的产品信息和核心卖点
- 明确目标受众和营销目标
- 包含情感描述和使用场景
- 提及期望的语气和风格

❌ **DON'T**:
- Brief 太简短（少于20字）
- 缺少核心卖点
- 目标不明确
- 期望与时长不匹配（30秒内讲太多内容）

### 2. 工作流优化建议

**开发/调试阶段**：
```
1. 使用较短时长（15-20秒）
2. 减少镜头数（5-8个）
3. 不生成图片（降低成本）
4. 不生成音频（加快速度）
```

**生产环境**：
```
1. 使用标准时长（30秒）
2. 标准镜头数（10个）
3. 生成图片（提升质量）
4. 生成音频（完整体验）
5. 输出兼容格式（确保播放）
```

### 3. 成本控制策略

**脚本生成成本**：
- 单次生成：约 $0.02-0.05（LLM API成本）
- 建议：完善 Brief 后一次性生成，减少重试

**关键帧生成成本**：
- 不生成图片：$0
- 生成图片：约 $0.02-0.05/张
- 建议：先不生成图片，确认分镜满意后再生成

**视频生成成本**：
- 单镜头：约 $0.05-0.10
- 10镜头视频：约 $0.50-1.00
- 建议：先测试1-2个镜头，确认效果后再批量生成

### 4. 质量控制清单

**脚本生成后**：
- [ ] 评分 ≥ 6.0/7.0
- [ ] 四段结构完整
- [ ] 口播文本通顺
- [ ] 核心卖点覆盖

**关键帧生成后**：
- [ ] 分镜数量合理
- [ ] 时间分配合理
- [ ] 画面描述清晰
- [ ] 图片风格一致（如果生成）

**视频生成后**：
- [ ] 所有镜头成功生成
- [ ] 视频拼接流畅
- [ ] 音频清晰
- [ ] 文件可以正常播放

### 5. 常用命令速查

```bash
# 启动应用
python run_streamlit.py

# 构建向量索引
cd script_agent/agent
python script_agent.py --build-index

# 生成单个脚本
python script_agent.py \
  --brief "你的营销需求" \
  --objective roi \
  --duration 30

# 生成分镜（命令行）
cd visual_agent/agent
python keyframe_storyboard_agent.py \
  --input ../../outputs/final_script/final_script.json \
  --output-dir ../../outputs/keyframes

# 生成视频（命令行）
cd video_agent/agent
python seedance_video_agent.py \
  --submit \
  --storyboard ../../outputs/keyframes/storyboard.json \
  --generate-audio \
  --concat
```

---

## 附录

### A. 键盘快捷键

| 快捷键 | 功能 |
|-------|------|
| `Ctrl + Enter` | 在文本框中提交 |
| `Ctrl + S` | 保存当前编辑 |
| `F5` | 刷新页面 |

### B. 支持的文件格式

**输入**：
- 脚本：`.json`, `.md`
- 视频：`.mp4`, `.mov`, `.avi`

**输出**：
- 脚本：`.json`, `.md`
- 图片：`.png`, `.jpg`
- 视频：`.mp4`

### C. 系统要求

**最低配置**：
- CPU: 2核心
- RAM: 4GB
- 磁盘: 10GB
- 网络: 稳定互联网连接

**推荐配置**：
- CPU: 4核心+
- RAM: 8GB+
- 磁盘: 50GB+
- 网络: 高速互联网

### D. 联系支持

**文档**：`docs/STREAMLIT_USER_GUIDE.md`

**GitHub Issues**: https://github.com/your-repo/kinyo/issues

**邮件支持**: support@kinyo.ai

---

*User Guide Version: 1.0.0*  
*Last Updated: 2025-05-25*
