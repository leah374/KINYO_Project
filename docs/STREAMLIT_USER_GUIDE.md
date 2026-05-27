# KINYO AI 视频生成平台 - Streamlit UI 使用指南

## 简介

KINYO AI 视频生成平台是一个统一的 Streamlit 界面,整合了脚本生成、关键帧生成和视频生成三个 AI Agent,提供端到端的视频创作体验。

## 功能特性

### 🎯 核心功能

1. **📝 脚本生成 (Script Agent)**
   - 基于 RAG 的营销脚本生成
   - 自动评分和改写
   - 四段式结构 (Hook-Setup-Twist-CTA)
   - 知识库检索和证据展示

2. **🖼️ 关键帧生成 (Visual Agent)**
   - 从脚本生成分镜表
   - AI 生成关键帧图片
   - 分镜预览和编辑
   - 批量下载

3. **🎬 视频生成 (Video Agent)**
   - 从关键帧生成视频片段
   - 自动音频生成
   - 实时进度监控
   - 视频拼接和兼容格式输出

4. **⚡ 一键生成**
   - 端到端完整流程
   - 三阶段进度展示
   - 自动传递结果

5. **📚 历史记录**
   - SQLite 数据库存储
   - 搜索和筛选
   - 重新加载和删除

6. **⚙️ 设置管理**
   - API Key 配置和测试
   - 模型参数设置
   - 知识库管理

## 快速开始

### 1. 安装依赖

```bash
pip install -r streamlit_app/requirements.txt
```

### 2. 配置 API Keys

创建 `.env` 文件在项目根目录:

```env
K_TOKEN_API_KEY=your_k_token_key
OPENAI_API_KEY=your_openai_key
DASHSCOPE_API_KEY=your_dashscope_key
ARK_API_KEY=your_ark_key
SEEDANCE_API_KEY=your_seedance_key
```

或者在 Streamlit 界面的 **⚙️ 设置** 页面配置。

### 3. 启动应用

**方式 1: 使用启动脚本 (推荐)**

```bash
python run_streamlit.py
```

**方式 2: 直接运行 Streamlit**

```bash
cd streamlit_app
streamlit run app.py
```

**方式 3: 指定端口**

```bash
streamlit run streamlit_app/app.py --server.port 8502
```

### 4. 访问界面

打开浏览器访问:

```
http://127.0.0.1:8501
```

## 使用流程

### 完整工作流

```
📝 脚本生成 → 🖼️ 关键帧生成 → 🎬 视频生成
```

#### 步骤 1: 配置 API Keys

1. 进入 **⚙️ 设置** 页面
2. 填写所需的 API Keys
3. 点击 **Test** 按钮验证连接
4. 点击 **Save** 保存

#### 步骤 2: 生成脚本

**方式 A: 分步生成**

1. 进入 **📝 脚本生成** 页面
2. 输入营销需求 (Brief)
3. 选择目标 (ROI / 完播率 / 综合)
4. 设置时长
5. 点击 **🚀 Generate Script**
6. 查看结果并编辑
7. 点击 **→ Send to Storyboard Generation**

**方式 B: 一键生成**

1. 进入 **⚡ 一键生成** 页面
2. 输入营销需求和参数
3. 点击 **开始一键生成**
4. 等待三阶段完成
5. 下载最终视频

#### 步骤 3: 生成关键帧

1. 进入 **🖼️ 关键帧生成** 页面
2. 选择输入: **使用脚本生成结果** 或 **上传文件**
3. 设置分镜参数 (最大镜头数等)
4. 勾选 **生成关键帧图片** (可选)
5. 点击 **生成分镜**
6. 预览分镜和图片
7. 点击 **→ 发送到视频生成**

#### 步骤 4: 生成视频

1. 进入 **🎬 视频生成** 页面
2. 选择分镜 JSON 和关键帧目录
3. 设置视频参数
4. 勾选 **生成音频** 和 **拼接视频**
5. 点击 **开始生成**
6. 监控实时进度
7. 下载最终视频

## 页面说明

### 📊 概览页

- 项目状态概览
- API Key 检查
- 最近活动
- 文件管理器

### 📝 脚本生成页

**侧边栏输入:**
- Marketing Brief (营销需求)
- Objective (目标)
- Duration (时长)
- Advanced Options (高级选项)

**主区域输出:**
- 📜 Final Script (最终脚本)
- 📊 Evaluation (评分)
- 🔍 Evidence (证据)
- 📖 Retrieved Cases (检索案例)
- 📝 Editor (编辑器)
- 💾 Export (导出)

### 🖼️ 关键帧生成页

**侧边栏:**
- Input File (输入文件选择)
- Storyboard Settings (分镜设置)
- Image Generation (图片生成选项)

**主区域:**
- Storyboard List (分镜列表)
- Image Preview (图片预览)
- JSON Export (JSON 导出)

### 🎬 视频生成页

**侧边栏:**
- Input File (输入文件)
- Keyframe Directory (关键帧目录)
- Video Settings (视频设置)
- Audio Settings (音频设置)
- Output Settings (输出设置)

**主区域:**
- Generation Progress (生成进度)
- Video Clips (视频片段)
- Final Output (最终输出)

### ⚡ 一键生成页

- 输入营销需求
- 设置参数
- 运行完整流程
- 分阶段进度展示
- 最终视频预览

### 📚 历史记录页

- 查看所有历史记录
- 按类型筛选
- 搜索功能
- 查看详情
- 删除记录

### ⚙️ 设置页

**API Keys:**
- K Token API Key
- OpenAI API Key
- DashScope API Key
- ARK API Key
- Seedance API Key

**Model Configuration:**
- 脚本生成模型
- 图片生成模型
- 视频生成模型

**Default Parameters:**
- 默认时长
- 默认分镜数等

**Knowledge Base:**
- 重建向量索引

## 数据管理

### 历史记录数据库

位置: `streamlit_app/database/kinuyo_history.db`

**查看数据库:**

```bash
sqlite3 streamlit_app/database/kinuyo_history.db
```

**表结构:**
- `script_history` - 脚本生成历史
- `storyboard_history` - 分镜生成历史
- `video_history` - 视频生成历史
- `full_pipeline_history` - 完整流程历史

### 输出文件结构

```
outputs/
├── final_script/
│   ├── final_script.json
│   └── final_script.md
├── keyframes/
│   ├── storyboard.json
│   ├── images/
│   │   ├── S01.png
│   │   └── S02.png
│   └── image_prompts.jsonl
├── videos/
│   ├── clips/
│   │   ├── S01.mp4
│   │   └── S02.mp4
│   ├── final_seedance_video.mp4
│   └── final_seedance_video_compatible.mp4
└── script_outputs/
    ├── script_complete_result.json
    └── streamlit_last_result.json
```

## 高级功能

### 1. 脚本编辑器

在脚本生成页的 **Editor** 标签页:
- 可视化编辑 Planning
- 逐段编辑 Segments
- Raw JSON 编辑
- 实时验证

### 2. 批量生成

在关键帧生成页:
- 设置最大镜头数
- 批量生成图片
- 批量下载

### 3. 进度监控

在视频生成页:
- 实时进度条
- 当前任务显示
- 日志流输出

### 4. 文件管理器

在概览页的 **File Manager** 标签:
- 按类型浏览输出文件
- 查看文件信息
- 直接下载视频

## 常见问题

### 1. API Key 配置不成功

**问题**: 提示 "API key not configured"

**解决**:
- 检查 `.env` 文件位置是否正确
- 确认 API Key 格式正确
- 在设置页点击 **Test** 验证连接

### 2. 向量索引未找到

**问题**: 提示 "Index not found"

**解决**:
- 在脚本生成页侧边栏点击 **Build Index**
- 或手动运行: `python script_agent/agent/script_agent.py --build-index`

### 3. 视频生成进度卡住

**问题**: 生成进度长时间无响应

**解决**:
- 检查 ARK API Key 是否有效
- 确认网络连接正常
- 查看日志输出错误信息

### 4. 图片生成失败

**问题**: 关键帧图片生成失败

**解决**:
- 确认 OpenAI API Key 有余额
- 检查图片模型名称是否正确
- 尝试调整图片生成参数

## 性能优化

### 1. 减少检索数量

在脚本生成页的 **Advanced Options**:
- 降低 **Top K Results** 参数

### 2. 批量生成优化

在关键帧生成页:
- 取消勾选 **生成关键帧图片** 以跳过图片生成
- 设置合理的 **最大镜头数**

### 3. 视频生成优化

在视频生成页:
- 勾选 **仅生成部分镜头**
- 降低视频质量设置

## 安全建议

### 1. API Key 保护

- 不要将 `.env` 文件提交到 Git
- 定期更换 API Keys
- 使用环境变量管理敏感信息

### 2. 数据备份

定期备份:

```bash
# 备份数据库
cp streamlit_app/database/kinuyo_history.db backups/

# 备份输出文件
tar -czf outputs_backup.tar.gz outputs/
```

### 3. 访问控制

如需部署到服务器:
- 设置 Streamlit 密码保护
- 使用 HTTPS
- 限制访问 IP

## 开发指南

### 添加新页面

1. 在 `streamlit_app/pages/` 创建新文件
2. 文件命名格式: `数字_图标_名称.py`
3. 实现 `main()` 函数
4. Streamlit 会自动识别为新页面

### 自定义组件

1. 在 `streamlit_app/components/` 创建组件文件
2. 实现 class 或函数
3. 在 `components/__init__.py` 中导出

### 集成新功能

1. 在 `utils/workflow_manager.py` 添加新方法
2. 在对应页面调用新方法
3. 更新 `session_state` 管理逻辑

## 更新日志

### v1.0.0 (2025-05-25)

**新增功能:**
- ✨ 统一 Streamlit 界面
- ✨ 多页面导航
- ✨ API Key 管理组件
- ✨ 文件上传和选择
- ✨ 脚本编辑器
- ✨ 实时进度跟踪
- ✨ 历史记录数据库
- ✨ 一键生成流程

**改进:**
- 🎨 优化 UI 布局
- ⚡ 提升性能
- 🔒 增强 API Key 安全

## 技术支持

**文档**: `docs/STREAMLIT_USER_GUIDE.md`

**GitHub Issues**: https://github.com/your-repo/kinyo/issues

**联系方式**: your-email@example.com

## 许可证

本项目仅供学习和研究使用,请遵守相关 API 服务条款。

---

**祝使用愉快!** 🎉
