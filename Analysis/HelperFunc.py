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
            - D001_I001_score: 视觉冲击与钩子设定-得分
            - D001_I001_score_basis: 视觉冲击与钩子设定-评分依据
            - D001_I001_reason: 视觉冲击与钩子设定-理由
            - D001_I002_score: 身份认同与人群筛选-得分
            - D001_I002_score_basis: 身份认同与人群筛选-评分依据
            - D001_I002_reason: 身份认同与人群筛选-理由
            - ... (共9个指标，每个指标3个字段)
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
    
    # 5. 提取9个指标的详细信息（宽表格展平）
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


# ============= 列名常量（方便后续引用） =============

COLUMNS_SCORES = {
    'D001-I001': '视觉冲击与钩子设定',
    'D001-I002': '身份认同与人群筛选',
    'D002-I001': '痛点与解决方案闭环',
    'D002-I002': '节奏控制与信息密度',
    'D003-I001': '场景化痛点还原',
    'D003-I002': '竞品差异化与卖点可视化',
    'D004-I001': '演员表现力与口播',
    'D004-I002': '视听沉浸感与制作',
    'D005-I001': '决策心理博弈与CTA'
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
    从宽表格计算各维度平均分
    
    Args:
        df: 宽表格格式的DataFrame
        
    Returns:
        包含各维度平均分的DataFrame
    """
    dimension_map = {
        'D001': ['D001-I001', 'D001-I002'],
        'D002': ['D002-I001', 'D002-I002'],
        'D003': ['D003-I001', 'D003-I002'],
        'D004': ['D004-I001', 'D004-I002'],
        'D005': ['D005-I001']
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