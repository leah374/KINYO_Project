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