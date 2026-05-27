# KaiWang V-0417-01
import requests
import pandas as pd 
import numpy as np 
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict
import time
from tqdm import tqdm
import json 
from openai import OpenAI
import re 
import os 
from typing import Dict, List, Optional, Any

# 中国假日数据获取
def fetch_holiday_details(year):
    # 获取中国的假日
    url = f'https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            holidays_list = [day for day in data['days']] # isOffDay 为 True 代表放假, False 代表工作日, 还有一些特殊情况如调休、补班等
            return pd.DataFrame(holidays_list)
    except Exception as e:
        print(f"获取 {year} 年数据失败: {e}")
    return pd.DataFrame()

def normalize_name(text):
    """统一命名: 去掉首尾空白, 按空格和-分词后用-连接"""
    if pd.isna(text):
        return ""
    text = Path(str(text)).stem  # 去掉文件扩展名
    text = str(text).strip()
    parts = [p for p in re.split(r"[\s\-]+", text) if p]
    return "-".join(parts)

def create_analysis_dataframe(reasons_dict):
    """将分析结果转换为DataFrame格式"""
    rows = []
    for base_id, info in reasons_dict.items():
        for video in info['high_score_videos']:
            rows.append({
                'indicator_id': base_id,
                'indicator_name': info['indicator_name'],
                'avg_score': info['avg_score'],
                'video_id': video['video_id'],
                'score': video['score'],
                'reason': video['reason']
            })
    return pd.DataFrame(rows)


# 对于素材标题使用LLM进行分析
def evaluate_single_title(title, api_key, prompt_template, max_retries=3):
    """
    评估单个标题（线程安全）
    """
    for attempt in range(max_retries):
        try:
            llm_client = OpenAI(
                api_key=api_key,
                base_url="https://api.siliconflow.cn/v1" # 我用的硅基流动的
            )
            response = llm_client.chat.completions.create(
                model="Pro/zai-org/GLM-4.7", # GLM 4.7
                messages=[
                    {
                        "role": "system",
                        "content": "你只返回合法JSON, 不要使用Markdown代码块, 不要添加额外字段。"
                    },
                    {
                        "role": "user",
                        "content": prompt_template.format(title=title)
                    }
                ],
                stream=False,
                max_tokens=1024,
                temperature=0.2
            )
            result_text = response.choices[0].message.content.strip()
            # 清理 markdown 代码块
            if result_text.startswith("```"):
                result_text = re.sub(r"^```json?\s*", "", result_text)
                result_text = re.sub(r"\s*```$", "", result_text)
            # 解析 JSON
            result_dict = json.loads(result_text)
            # 添加标题信息
            result_dict['meaningful_title'] = title
            result_dict['status'] = 'success'
            result_dict['error'] = ''
            return result_dict
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败 (尝试 {attempt+1}/{max_retries}): {str(e)}"
            if attempt == max_retries - 1:
                return {
                    'meaningful_title': title,
                    'status': 'failed',
                    'error': error_msg,
                    'marketing_score': np.nan,
                    'attention_score': np.nan,
                    'promotion_score': np.nan,
                    'keywords': [],
                    'overall_comment': '',
                    'raw_response': result_text if 'result_text' in locals() else ''
                }
            time.sleep(0.5) 
            
        except Exception as e:
            error_msg = f"API调用失败 (尝试 {attempt+1}/{max_retries}): {str(e)}"
            if attempt == max_retries - 1:
                return {
                    'meaningful_title': title,
                    'status': 'failed',
                    'error': error_msg,
                    'marketing_score': np.nan,
                    'attention_score': np.nan,
                    'promotion_score': np.nan,
                    'keywords': [],
                    'overall_comment': '',
                    'raw_response': ''
                }
            time.sleep(0.5)  
    return None

def evaluate_titles_multithread(titles, api_key, prompt_template, max_workers= 8, timeout = 40):
    """
    多线程评估标题列表
    """
    results = []
    max_workers = min(os.cpu_count() or 1, max_workers)  # 限制最大线程数不超过CPU核心数
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_title = {
            executor.submit(evaluate_single_title, title, api_key, prompt_template): title 
            for title in titles
        }
        # total = max(len(titles) - 1, 1) 是为了避免当标题列表为空时 tqdm 报错, 同时防止卡进度条
        with tqdm(total=max(len(titles), 1), desc="评估标题进度", unit="个") as pbar:
            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    result = future.result(timeout = timeout)
                    results.append(result)
                except Exception as e:
                    # 处理未捕获的异常
                    results.append({
                        'meaningful_title': title,
                        'status': 'failed',
                        'error': str(e),
                        'marketing_score': np.nan,
                        'attention_score': np.nan,
                        'promotion_score': np.nan,
                        'keywords': [],
                        'overall_comment': '',
                        'raw_response': ''
                    })
                pbar.update(1)
                # 可选：更新进度条描述，显示成功/失败统计
                success_count = sum(1 for r in results if r.get('status') == 'success')
                pbar.set_postfix({
                    '成功': success_count,
                    '失败': len(results) - success_count
                })
    return results


# 对于素材标题调用Embedding接口
def embed_single_title(
    title,
    api_key,
    model="BAAI/bge-large-zh-v1.5",
    max_retries=3,
    base_url="https://api.siliconflow.cn/v1/embeddings",
    timeout=40,
):
    """
    对单个标题生成 embedding
    """
    for attempt in range(max_retries):
        try:
            payload = {
                "model": model,
                "input": title,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(base_url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            result_json = response.json()

            data = result_json.get("data", [])
            if not data:
                raise ValueError("Embedding响应缺少 data 字段")

            embedding = data[0].get("embedding", None)
            if embedding is None:
                raise ValueError("Embedding响应缺少 embedding 字段")

            return {
                "meaningful_title": title,
                "status": "success",
                "error": "",
                "embedding": embedding,
                "embedding_dim": len(embedding),
                "model": result_json.get("model", model),
            }

        except Exception as e:
            error_msg = f"Embedding调用失败 (尝试 {attempt+1}/{max_retries}): {str(e)}"
            if attempt == max_retries - 1:
                return {
                    "meaningful_title": title,
                    "status": "failed",
                    "error": error_msg,
                    "embedding": np.nan,
                    "embedding_dim": np.nan,
                    "model": model,
                }
            time.sleep(0.5)
    return None


def embed_titles_multithread(
    titles,
    api_key,
    model="BAAI/bge-large-zh-v1.5",
    max_workers=8,
    timeout=40,
    max_retries=3,
):
    """
    多线程批量生成标题 embedding
    """
    results = []
    max_workers = min(os.cpu_count() or 1, max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_title = {
            executor.submit(
                embed_single_title,
                title,
                api_key,
                model,
                max_retries,
                "https://api.siliconflow.cn/v1/embeddings",
                timeout,
            ): title
            for title in titles
        }

        with tqdm(total=max(len(titles), 1), desc="Embedding进度", unit="个") as pbar:
            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    result = future.result(timeout=timeout)
                    results.append(result)
                except Exception as e:
                    results.append(
                        {
                            "meaningful_title": title,
                            "status": "failed",
                            "error": str(e),
                            "embedding": np.nan,
                            "embedding_dim": np.nan,
                            "model": model,
                        }
                    )

                pbar.update(1)
                success_count = sum(1 for r in results if r.get("status") == "success")
                pbar.set_postfix({
                    "成功": success_count,
                    "失败": len(results) - success_count,
                })

    return results

def compress_json_to_txt(input_json_path, output_txt_path):
    """
    读取JSON文件,输出紧凑格式的TXT文件
    """
    # 读取原始JSON文件
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换为紧凑JSON字符串（无额外空格，但保留必要结构）
    # separators=(',', ':') 去掉逗号和冒号后的空格
    compact_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    # 写入TXT文件
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(compact_json)
    
    print(f"已生成紧凑格式文件：{output_txt_path}")
    print(f"原始JSON字符数：{len(json.dumps(data, ensure_ascii=False))}")
    print(f"压缩后字符数：{len(compact_json)}")
    print(f"节省了 {len(json.dumps(data, ensure_ascii=False)) - len(compact_json)} 个字符 \n")


def extract_video_analysis_to_wide_table(model_response: Dict[str, Any]) -> pd.DataFrame:
    """
    从火山引擎模型响应中提取视频分析结果，返回宽表格格式（一行一个视频）
    
    Args:
        model_response: 火山引擎API返回的完整响应字典
        
    Returns:
        pd.DataFrame: 宽表格格式，包含以下列：
            - video_id: 视频ID
            - total_score: 总分
            - core_strength: 核心优势
            - core_weakness: 核心劣势
            - key_suggestion: 提升建议
            - D001-I001_score: Hook (0-3秒)-得分
            - D001-I001_score_basis: Hook (0-3秒)-评分依据
            - D001-I001_reason: Hook (0-3秒)-理由
            - ... 
    """
    
    # 1. 提取content字段中的JSON字符串并解析
    content_str = model_response['choices'][0]['message']['content']
    analysis_result = json.loads(content_str)
    
    # 2. 初始化结果字典
    result = {}
    
    # 3. 提取基础信息
    result['video_id'] = analysis_result.get('video_id', 'unknown')
    
    # 4. 提取summary信息
    summary = analysis_result.get('summary', {})
    result['total_score'] = summary.get('total_score')
    result['core_strength'] = summary.get('core_strength')
    result['core_weakness'] = summary.get('core_weakness')
    result['key_suggestion'] = summary.get('key_suggestion')
    
    # 5. 提取所有指标的详细信息（宽表格展平）
    for indicator in analysis_result.get('indicator_scores', []):
        indicator_id = indicator.get('indicator_id')  # 如 D001-I001
        
        # 构建列名
        score_col = f"{indicator_id}_score"
        basis_col = f"{indicator_id}_score_basis"
        reason_col = f"{indicator_id}_reason"
        
        # 填充数据
        result[score_col] = indicator.get('score')
        result[basis_col] = indicator.get('score_basis')
        result[reason_col] = indicator.get('reason')
    
    # 6. 转换为DataFrame（一行）
    df = pd.DataFrame([result])
    
    return df


def extract_batch_to_wide_table(model_responses: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    批量处理多个模型响应，合并为宽表格（多行，每行一个视频）
    
    Args:
        model_responses: 多个火山引擎API响应的列表
        
    Returns:
        pd.DataFrame: 合并后的宽表格
    """
    all_rows = []
    
    for i, response in enumerate(model_responses):
        try:
            df = extract_video_analysis_to_wide_table(response)
            all_rows.append(df)
            print(f"成功处理第 {i+1} 个视频，ID: {df['video_id'].iloc[0]}")
        except Exception as e:
            print(f"处理第 {i+1} 个响应时失败: {e}")
            continue
    
    if all_rows:
        return pd.concat(all_rows, ignore_index=True)
    else:
        return pd.DataFrame()


def extract_video_analysis_simple(model_response: Dict[str, Any]) -> pd.DataFrame:
    """
    简化版：只提取content内容并解析为DataFrame
    （如果content本身就是完整的JSON结构，直接转换）
    
    Args:
        model_response: 火山引擎API返回的完整响应字典
        
    Returns:
        pd.DataFrame: 解析后的DataFrame
    """
    # 直接提取并解析content
    content_str = model_response['choices'][0]['message']['content']
    data = json.loads(content_str)
    
    # 如果data是列表，直接转为DataFrame
    if isinstance(data, list):
        return pd.DataFrame(data)
    # 如果data是字典，转为单行DataFrame
    elif isinstance(data, dict):
        return pd.json_normalize(data)
    else:
        raise ValueError(f"不支持的数据类型: {type(data)}")


# ============= 列名常量 =============

COLUMNS_SCORES = {
    # D001 脚本结构
    'D001_I001': 'Hook (0-3秒)',
    'D001_I002': 'Setup (铺垫与信任)',
    'D001_I003': 'Twist (反转与高潮)',
    'D001_I004': 'CTA (行动召唤)',
    # D002 钩子设计
    'D002_I001': '冲突与反差强度',
    'D002_I002': '悬念留存设计',
    # D003 节奏BGM与剪辑工程
    'D003_I001': 'BPM与卡点频率',
    'D003_I002': '转场与剪辑强度',
    # D004 选品视角
    'D004_I001': '产品颜值与高光展示',
    'D004_I002': '价格锚点与即时满足',
    # D005 文案张力
    'D005_I001': '数字与具象化表达',
    'D005_I002': '痛点直击与悬念词',
    # D006 第一秒视觉
    'D006_I001': '视觉冲击与反差大',
    'D006_I002': '关键词大字报',
    # D007 CTA与互动设计
    'D007_I001': '评论引导与互动钩',
    'D007_I002': '收藏与转发触发'
}

def get_score_columns() -> List[str]:
    """获取所有得分列名"""
    return [f"{indicator_id}_score" for indicator_id in COLUMNS_SCORES.keys()]


def get_reason_columns() -> List[str]:
    """获取所有理由列名"""
    return [f"{indicator_id}_reason" for indicator_id in COLUMNS_SCORES.keys()]


# ============= 辅助分析函数 =============
def calculate_dimension_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    从宽表格计算各维度平均分（基于v3的7个维度）
    
    Args:
        df: 宽表格格式的DataFrame
        
    Returns:
        包含各维度平均分的DataFrame
    """
    # 按照v3标准库的7个维度组织指标
    dimension_map = {
        'D001': ['D001-I001', 'D001-I002', 'D001-I003', 'D001-I004'],
        'D002': ['D002-I001', 'D002-I002'],
        'D003': ['D003-I001', 'D003-I002'],
        'D004': ['D004-I001', 'D004-I002'],
        'D005': ['D005-I001', 'D005-I002'],
        'D006': ['D006-I001', 'D006-I002'],
        'D007': ['D007-I001', 'D007-I002']
    }
    
    result_rows = []
    for _, row in df.iterrows():
        row_result = {'video_id': row['video_id'], 'total_score': row['total_score']}
        
        for dim_id, indicators in dimension_map.items():
            scores = []
            for indicator_id in indicators:
                score_col = f"{indicator_id}_score"
                if score_col in row and pd.notna(row[score_col]):
                    scores.append(row[score_col])
            
            if scores:
                row_result[f"{dim_id}_avg"] = round(sum(scores) / len(scores), 1)
            else:
                row_result[f"{dim_id}_avg"] = None
        
        result_rows.append(row_result)
    
    return pd.DataFrame(result_rows)


def get_lowest_indicators(df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """
    找出每个视频得分最低的几个指标
    
    Args:
        df: 宽表格格式的DataFrame
        top_n: 返回最低的N个指标
        
    Returns:
        每个视频得分最低的指标列表
    """
    score_cols = get_score_columns()
    results = []
    
    for _, row in df.iterrows():
        video_id = row['video_id']
        scores = []
        
        for col in score_cols:
            if pd.notna(row[col]):
                indicator_id = col.replace('_score', '')
                scores.append({
                    'video_id': video_id,
                    'indicator_id': indicator_id,
                    'indicator_name': COLUMNS_SCORES.get(indicator_id, indicator_id),
                    'score': row[col]
                })
        
        # 排序取最低的top_n
        scores.sort(key=lambda x: x['score'])
        results.extend(scores[:top_n])
    
    return pd.DataFrame(results)

def get_indicator_name(indicator_id):
    """根据指标ID返回指标名称"""
    name_map = {
        # 完播率相关
        "D001-I001": "Hook (0-3秒)",
        "D002-I001": "冲突与反差强度",
        "D002-I002": "悬念留存设计",
        "D003-I001": "BPM与卡点频率",
        "D005-I002": "痛点直击与悬念词",
        "D006-I001": "视觉冲击与反差大",
        "D006-I002": "关键词大字报",
        # ROI相关
        "D001-I002": "Setup (铺垫与信任)",
        "D003-I002": "转场与剪辑强度",
        "D004-I001": "产品颜值与高光展示",
        "D007-I001": "评论引导与互动钩"
    }
    return name_map.get(indicator_id, indicator_id)


def get_high_score_reasons(df, indicator_list):
    """
    对每个指标，计算平均分，筛选出高于平均分的视频，提取其score_reason
    
    Args:
        df: DataFrame，包含评分数据
        indicator_list: 指标列表（带_score后缀）
    
    Returns:
        dict: {
            "indicator_id": {
                "avg_score": 平均分,
                "high_score_videos": [
                    {
                        "video_id": "xxx",
                        "score": 分数,
                        "reason": "评分理由"
                    },
                    ...
                ]
            }
        }
    """
    result_dict = {}
    
    for indicator in indicator_list:
        # 获取指标的基础ID（去掉_score后缀）
        base_id = indicator.replace('_score', '')
        reason_col = f"{base_id}_reason"
        
        # 计算该指标的平均分
        avg_score = df[indicator].mean()
        
        # 筛选高于平均分的视频
        high_score_df = df[df[indicator] > avg_score].copy()
        
        # 提取video_id、score和reason
        high_score_videos = []
        for _, row in high_score_df.iterrows():
            high_score_videos.append({
                'video_id': row['video_id'],
                'score': row[indicator],
                'reason': row[reason_col] if pd.notna(row[reason_col]) else "无理由"
            })
        
        # 存入字典
        result_dict[base_id] = {
            'indicator_name': get_indicator_name(base_id),  # 需要定义这个函数
            'avg_score': round(avg_score, 2),
            'high_score_count': len(high_score_videos),
            'high_score_videos': high_score_videos
        }
    
    return result_dict

def load_json_data(file_path: str):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_knowledge_base(knowledge_base, file_path: str):
    """保存知识库到文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, ensure_ascii=False, indent=2, fp=f)
    print(f"知识库已保存: {file_path}")


def print_knowledge_base_summary(knowledge_base, name: str):
    """打印知识库摘要"""
    print("\n" + "=" * 80)
    print(f"{name} - 知识库摘要")
    print("=" * 80)
    
    summary = knowledge_base.get('summary', {})
    print(f"\n核心洞察: {summary.get('core_insight', 'N/A')}")
    print(f"\n关键发现: {summary.get('key_finding', 'N/A')}")
    
    print("\n指标概览:")
    for indicator in knowledge_base.get('indicators', []):
        print(f"  - {indicator.get('indicator_name')}: 平均分 {indicator.get('avg_score')}")
        print(f"    成功模式: {', '.join(indicator.get('success_patterns', [])[:2])}")
    
    print("\n策略建议:")
    for i, rec in enumerate(knowledge_base.get('content_strategy_recommendations', [])[:3], 1):
        print(f"  {i}. {rec}")