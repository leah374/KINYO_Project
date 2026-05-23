# KaiWang V-0417-01
from dataclasses import dataclass
from string import Template
import json 
import os 

ANALYSIS_DIR = r"..//Analysis"
DATA_DIR = r"..//Data"
Processed_DATA_DIR = r"..//Processed_Data"

CONTENT_EVALUATION_PATH = os.path.join(DATA_DIR, "内容评价标准库.json")
with open(CONTENT_EVALUATION_PATH, 'r', encoding='utf-8') as f:
    content_evaluation = json.load(f)

@dataclass
class PromptTemplate:
    """
    用于短视频标题营销评审的提示词模板。
    """

    TITLE_EVAL_PROMPT = """你是一名短视频营销评审专家。
        请对给定标题进行结构化评估,并严格按要求返回结果。

        评估维度(每项1-5分,必须为整数,分数越高越正向):
        1) 营销性:是否体现卖点、利益点、转化导向。
        2) 吸引眼球性:是否能快速抓住注意力、引发点击兴趣。
        3) 推广性:是否适合大范围传播、复用和品牌推广。

        评分锚点:
        - 1分:非常弱,几乎无效
        - 2分:较弱,有少量相关性
        - 3分:中等,基本可用
        - 4分:较强,表现良好
        - 5分:非常强,明显优秀

        关键字抽取规则:
        - 提取标题中最有营销/传播价值的词
        - 最多5个,去重,保持原文顺序
        - 无明显关键字时返回空数组 []

        异常输入规则:
        - 若标题为空、纯符号、纯数字或明显无语义,三个分数不高于2分
        - overall_comment 简短说明原因(不超过40字)

        输出要求:
        - 只能输出合法JSON对象
        - 不要输出Markdown代码块
        - 不要输出任何解释性文字
        - 字段必须且仅包含以下内容:

        {{
        "marketing_score": <1-5整数>,
        "attention_score": <1-5整数>,
        "promotion_score": <1-5整数>,
        "keywords": ["关键字1", "关键字2"],
        "overall_comment": "不超过40字的简短评价"
        }}

        待评估标题:"{title}"
    """


    VOLCENGINE_VIDEO_ANALYSIS_PROMPT = Template("""
    # 角色
    你是一位专业的短视频内容营销分析师，精通爆款内容逻辑、视听语言与转化心理学。你具备以下核心能力：
    - 深度理解短视频用户心理和行为模式
    - 精准识别爆款视频的核心要素
    - 严格遵循量化评估标准进行客观评分
    - 提供具有实操性的优化建议


    # 任务
    请严格依据【评分标准库】，对我给你上传的【待评分视频】进行量化评估。你必须输出一个符合指定格式的JSON对象。

    # 评分标准库
    $evaluation_standard

    # 输出格式要求
    你必须只输出一个合法的JSON对象,格式如下。不要有任何额外文字,不要用```json代码块包裹。

    {
    "video_id": "$video_id",
    "indicator_scores": [
        {
        "indicator_id": "D001-I001",
        "indicator_name": "Hook (0-3秒)",
        "score": $score_D001_I001,
        "score_basis": "$basis_D001_I001",
        "reason": "$reason_D001_I001"
        },
        {
        "indicator_id": "D001-I002",
        "indicator_name": "Setup (铺垫与信任)",
        "score": $score_D001_I002,
        "score_basis": "$basis_D001_I002",
        "reason": "$reason_D001_I002"
        },
        {
        "indicator_id": "D001-I003",
        "indicator_name": "Twist (反转与高潮)",
        "score": $score_D001_I003,
        "score_basis": "$basis_D001_I003",
        "reason": "$reason_D001_I003"
        },
        {
        "indicator_id": "D001-I004",
        "indicator_name": "CTA (行动召唤)",
        "score": $score_D001_I004,
        "score_basis": "$basis_D001_I004",
        "reason": "$reason_D001_I004"
        },
        {
        "indicator_id": "D002-I001",
        "indicator_name": "冲突与反差强度",
        "score": $score_D002_I001,
        "score_basis": "$basis_D002_I001",
        "reason": "$reason_D002_I001"
        },
        {
        "indicator_id": "D002-I002",
        "indicator_name": "悬念留存设计",
        "score": $score_D002_I002,
        "score_basis": "$basis_D002_I002",
        "reason": "$reason_D002_I002"
        },
        {
        "indicator_id": "D003-I001",
        "indicator_name": "BPM与卡点频率",
        "score": $score_D003_I001,
        "score_basis": "$basis_D003_I001",
        "reason": "$reason_D003_I001"
        },
        {
        "indicator_id": "D003-I002",
        "indicator_name": "转场与剪辑强度",
        "score": $score_D003_I002,
        "score_basis": "$basis_D003_I002",
        "reason": "$reason_D003_I002"
        },
        {
        "indicator_id": "D004-I001",
        "indicator_name": "产品颜值与高光展示",
        "score": $score_D004_I001,
        "score_basis": "$basis_D004_I001",
        "reason": "$reason_D004_I001"
        },
        {
        "indicator_id": "D004-I002",
        "indicator_name": "价格锚点与即时满足",
        "score": $score_D004_I002,
        "score_basis": "$basis_D004_I002",
        "reason": "$reason_D004_I002"
        },
        {
        "indicator_id": "D005-I001",
        "indicator_name": "数字与具象化表达",
        "score": $score_D005_I001,
        "score_basis": "$basis_D005_I001",
        "reason": "$reason_D005_I001"
        },
        {
        "indicator_id": "D005-I002",
        "indicator_name": "痛点直击与悬念词",
        "score": $score_D005_I002,
        "score_basis": "$basis_D005_I002",
        "reason": "$reason_D005_I002"
        },
        {
        "indicator_id": "D006-I001",
        "indicator_name": "视觉冲击与反差大",
        "score": $score_D006_I001,
        "score_basis": "$basis_D006_I001",
        "reason": "$reason_D006_I001"
        },
        {
        "indicator_id": "D006-I002",
        "indicator_name": "关键词大字报",
        "score": $score_D006_I002,
        "score_basis": "$basis_D006_I002",
        "reason": "$reason_D006_I002"
        },
        {
        "indicator_id": "D007-I001",
        "indicator_name": "评论引导与互动钩",
        "score": $score_D007_I001,
        "score_basis": "$basis_D007_I001",
        "reason": "$reason_D007_I001"
        },
        {
        "indicator_id": "D007-I002",
        "indicator_name": "收藏与转发触发",
        "score": $score_D007_I002,
        "score_basis": "$basis_D007_I002",
        "reason": "$reason_D007_I002"
        }
    ],
    "summary": {
        "total_score": $total_score,
        "core_strength": "$core_strength",
        "core_weakness": "$core_weakness",
        "key_suggestion": "$key_suggestion"
    }
    }

    # 评分规则
    1. **指标评分**：共7个维度、16个指标，每个指标独立打分，整数分，范围1-7分
    2. **判分依据**：每个指标的score_basis必须引用评分标准库中对应等级的描述原文
    3. **reason字段**：结合视频具体内容给出评分理由，30字以内
    4. **总分计算**：
    - 先计算每个维度的平均分 = 该维度下所有指标分数的算术平均值（保留一位小数）
    - 再计算总分 = 7个维度平均分的算术平均值（保留一位小数）
    5. **综合评语**：
    - core_strength：一句话核心优势，30字以内
    - core_weakness：一句话核心劣势，30字以内
    - key_suggestion：一句话最关键提升建议，30字以内

    # 重要约束
    - 只输出JSON对象本身，不要有任何额外文字
    - 不要用```json代码块包裹
    - 不要有任何解释性文字
    - 所有字符串必须使用双引号
    - 严格按照上述JSON结构输出

    # 开始评分
    """)

    COMPLETION_RATE_SUMMARY_PROMPT = """
        你是一位专业的短视频内容策略专家，专注于分析**完播率**的影响因素。

        # 任务
        请基于以下完播率相关指标的高分视频评分理由数据，总结出一套系统化的**短视频完播率提升知识库**。

        # 数据说明
        这个JSON文件包含了以下7个完播率核心指标的评分依据：
        - D001-I001 (Hook 0-3秒): 开头3秒的冲突或利益承诺
        - D002-I001 (冲突与反差强度): 画面/文案的前后对比和认知冲突
        - D002-I002 (悬念留存设计): 通过提问、倒计时等方式引导用户等待
        - D003-I001 (BPM与卡点频率): 音乐节奏与剪辑卡点的匹配度
        - D005-I002 (痛点直击与悬念词): 强情绪词的使用（千万别、竟然、后悔等）
        - D006-I001 (视觉冲击与反差大): 第一帧画面的视觉张力
        - D006-I002 (关键词大字报): 超大字体和高对比度关键词的使用

        每个指标的数据包含：
        - 该指标的平均分
        - 高于平均分的高质量视频示例
        - 每个视频的具体评分理由（描述了什么做得好）

        # 输出要求
        请输出一个**JSON格式**的知识库，结构如下：

        {{
        "knowledge_base_name": "短视频完播率提升知识库",
        "version": "1.0",
        "summary": {{
            "total_indicators": 7,
            "core_insight": "一句话总结完播率的核心秘诀",
            "key_finding": "基于数据发现的最重要规律（1-2段话）"
        }},
        "indicators": [
            {{
            "indicator_id": "D001-I001",
            "indicator_name": "Hook (0-3秒)",
            "avg_score": 6.2,
            "success_patterns": [
                "高频出现的成功策略1",
                "高频出现的成功策略2"
            ],
            "best_practices": [
                {{
                "practice": "具体做法示例",
                "example_from_data": "数据中提到的具体案例或理由",
                "why_it_works": "为什么这样做有效"
                }}
            ],
            "common_mistakes": [
                "需要避免的错误做法1",
                "需要避免的错误做法2"
            ],
            "actionable_tips": [
                "可以直接使用的技巧1",
                "可以直接使用的技巧2"
            ]
            }}
        ],
        "cross_indicator_insights": {{
            "synergy_effects": [
            "多个指标组合使用时的协同效应"
            ],
            "priority_focus": [
            "应该优先优化的指标排序建议"
            ]
        }},
        "content_strategy_recommendations": [
            "基于数据的整体内容策略建议1",
            "基于数据的整体内容策略建议2"
        ]
        }}

        # 生成要求
        1. **基于数据**：所有总结必须来源于提供的数据，不要凭空编造
        2. **具体可操作**：每个建议都要有具体的操作指导
        3. **结构清晰**：每个指标都要有成功模式、最佳实践、常见错误和操作技巧
        4. **内容丰富**：尽可能提取数据中的细节，生成详细的知识点
        5. **实战导向**：建议要能让内容创作者直接使用

        # 待分析数据
        {{json_data}}

        请开始分析并输出JSON格式的知识库。
        """

    ROI_SUMMARY_PROMPT = """
        你是一位专业的短视频电商转化专家，专注于分析**ROI（投资回报率/下单转化）** 的影响因素。

        # 任务
        请基于以下ROI相关指标的高分视频评分理由数据，总结出一套系统化的**短视频转化率提升知识库**。

        # 数据说明
        这个JSON文件包含了以下4个ROI核心指标的评分依据：
        - D001-I002 (Setup 铺垫与信任): 4-15秒是否建立场景、痛点或人设信任
        - D003-I002 (转场与剪辑强度): 镜头切换的特效、遮罩、运镜的丝滑程度
        - D004-I001 (产品颜值与高光展示): 产品外观、使用效果的吸引力
        - D007-I001 (评论引导与互动钩): 通过提问、求赞等方式引导用户互动

        每个指标的数据包含：
        - 该指标的平均分
        - 高于平均分的高质量视频示例
        - 每个视频的具体评分理由（描述了什么做得好）

        # 输出要求
        请输出一个**JSON格式**的知识库，结构如下：

        {{
        "knowledge_base_name": "短视频转化率提升知识库",
        "version": "1.0",
        "summary": {{
            "total_indicators": 4,
            "core_insight": "一句话总结转化率的核心秘诀",
            "key_finding": "基于数据发现的最重要规律（1-2段话）"
        }},
        "indicators": [
            {{
            "indicator_id": "D001-I002",
            "indicator_name": "Setup (铺垫与信任)",
            "avg_score": 6.0,
            "success_patterns": [
                "高频出现的成功策略1",
                "高频出现的成功策略2"
            ],
            "best_practices": [
                {{
                "practice": "具体做法示例",
                "example_from_data": "数据中提到的具体案例或理由",
                "why_it_works": "为什么这样做有效",
                "trust_building_method": "信任建立的具体方法（针对信任类指标）"
                }}
            ],
            "common_mistakes": [
                "需要避免的错误做法1",
                "需要避免的错误做法2"
            ],
            "actionable_tips": [
                "可以直接使用的技巧1",
                "可以直接使用的技巧2"
            ]
            }}
        ],
        "cross_indicator_insights": {{
            "conversion_funnel": {{
            "awareness_to_trust": "从注意到信任的转化路径",
            "trust_to_action": "从信任到行动的触发点"
            }},
            "complementary_effects": [
            "各指标如何相互配合提升转化"
            ]
        }},
        "content_strategy_recommendations": [
            "基于数据的整体转化策略建议1",
            "基于数据的整体转化策略建议2"
        ],
        "cta_optimization_tips": [
            "CTA（行动召唤）优化的具体建议"
        ]
        }}

        # 生成要求
        1. **基于数据**：所有总结必须来源于提供的数据，不要凭空编造
        2. **具体可操作**：每个建议都要有具体的操作指导
        3. **结构清晰**：每个指标都要有成功模式、最佳实践、常见错误和操作技巧
        4. **内容丰富**：尽可能提取数据中的细节，生成详细的知识点
        5. **转化导向**：建议要聚焦如何让用户下单购买

        # 待分析数据
        {{json_data}}

        请开始分析并输出JSON格式的知识库。"""