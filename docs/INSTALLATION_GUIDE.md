# Python 3.13 环境安装指南

## 问题背景

之前的 Python 3.11 环境存在 TypedDict 兼容性问题：
- `langchain-core==1.4+` 使用了 `extra_items` 参数
- 该参数仅在 Python 3.15+ 支持
- 导致运行时错误：`_TypedDictMeta.new() got an unexpected keyword argument 'extra_items'`

## 解决方案

升级到 **Python 3.13** 环境，使用兼容的依赖版本。

---

## 安装步骤

### 方法 1：使用自动安装脚本（推荐）

```powershell
# 双击运行或命令行执行
setup_python313_env.bat
```

### 方法 2：手动安装

```powershell
# 1. 创建新的 conda 环境
conda create -n kinuyo python=3.13 -y

# 2. 激活环境
conda activate kinuyo

# 3. 安装依赖
pip install -r requirements_python313.txt

# 4. 验证安装
python -c "import langgraph; print('LangGraph:', langgraph.__version__)"
python -c "from langgraph.graph import StateGraph, END; print('OK')"
```

---

## 版本说明

### 核心 AI 框架
- **langgraph**: 1.2.1 - 工作流编排
- **langchain-core**: 1.3.1 - LangChain 核心
- **pydantic**: 2.12.3 - 数据验证

### UI 框架
- **streamlit**: 1.45.1 - Web 界面
- **pandas**: 2.2.3 - 数据处理
- **numpy**: 2.2.6 - 数值计算

### 向量检索
- **faiss-cpu**: 1.11.0 - 向量检索

### API 客户端
- **openai**: 1.84.0 - OpenAI API

---

## 启动应用

```powershell
# 激活环境
conda activate kinuyo

# 启动 Streamlit 应用
streamlit run streamlit_app/app.py

# 或者使用快捷脚本
start_streamlit.bat
```

---

## 常见问题

### Q1: 如果提示 conda 未找到？
**A:** 需要先安装 Anaconda 或 Miniconda：
- Anaconda: https://www.anaconda.com/download
- Miniconda: https://docs.conda.io/en/latest/miniconda.html

### Q2: 旧环境需要删除吗？
**A:** 建议：
```powershell
# 删除旧的 python311 环境
conda env remove -n python311 -y

# 或者重命名保留
conda rename -n python311 python311_backup
```

### Q3: 如何验证安装成功？
**A:** 运行测试脚本：
```powershell
python test_typeddict_fix.py
```
应该看到所有 [OK] 提示。

### Q4: API Keys 如何配置？
**A:** 在项目根目录创建 `.env` 文件：
```env
K_TOKEN_API_KEY=sk-xxxxx
OPENAI_API_KEY=sk-xxxxx
DASHSCOPE_API_KEY=sk-xxxxx  # 阿里云 Embedding
ARK_API_KEY=sk-xxxxx
SEEDANCE_API_KEY=sk-xxxxx
```

---

## 与 Python 3.11 的差异

| 特性 | Python 3.11 | Python 3.13 |
|------|-------------|-------------|
| TypedDict extra_items | ❌ 不支持 | ✅ 支持 |
| typing_extensions | 需要补丁 | 原生支持 |
| langchain-core 1.4+ | ❌ 不兼容 | ✅ 兼容 |
| 性能 | 基准 | +5-10% |

---

## 下一步

1. ✅ 安装 Python 3.13 环境
2. ✅ 配置 `.env` 文件
3. ✅ 构建 RAG 向量索引
4. ✅ 测试脚本生成功能

详细文档请参考：
- `docs/PLATFORM_INTRODUCTION.md` - 平台介绍
- `docs/USER_GUIDE.md` - 用户指南
- `docs/API.md` - API 参考
