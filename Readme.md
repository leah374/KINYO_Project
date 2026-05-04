# KINYO Project（金运）
''' text
Author: Kai Wang, Yunxi Li, Yahui Li
Last Date: 2026.05.05
Status: Mid-Tem
'''

本项目旨在通过数据驱动的方式，赋能 KINYO金运 的短视频内容营销。我们基于企业提供的海量视频素材（700GB+）及多维投放数据，利用计算机视觉、自然语言处理及大模型技术，深度挖掘“爆款”视频的关键特征。
核心目标：
1. 深度归因分析：关联视频内容特征与投放绩效（完播率、点击率等），量化内容价值。
2. 构建评价模型：基于火山引擎LAS与豆包2.0-Pro，建立自动化的视频质量评分体系。
3. 打造编导Agent：最终训练一个智能编导Agent，辅助企业自动化生成高转化率的营销视频，降低创作成本，提升流量获取效率。

## 目录结构（截至 2026-05-04）

> 说明：下方为工作区中已存在的主要文件/目录结构；对于可能很大的素材/数据目录，仅展示到文件夹层级。

```text
KINYO_Project/
├─ Analysis/                    # 存放代码的文件夹
│  ├─ ffmpeg_parallel_worker.py # 通过使用ffmpeg来处理视频的相关函数
│  ├─ HelperFunc.py             # Helper Function
│  ├─ Prompt_Template.py        # 提示词模板类
│  ├─ Transcribe_Whisper.py     # Whisper相关函数
│  ├─ Week2_Task1.ipynb         # 金运第一次任务-对应Week2_Task.md的第一项任务： 对视频文件,Excel统计文件进行预处理 (已废弃, 后续不用参考)
│  ├─ Week2_Task2.ipynb         # 金运第一次任务-对应Week2_Task.md的第二项任务： 构建爆款视频标签 (已废弃, 后续不用参考)
│  ├─ Week2_Task3.ipynb         # 金运第一次任务-对应Week2_Task.md的第三项任务：对(非)爆款视频进行描述性统计，以及画图 (已废弃, 后续不用参考)
│  ├─ Week4_Task1.ipynb         # 经过沟通和反馈过后的进一步处理：对新提供的视频数据以及Excel统计文件进行预处理，根据相关指标筛选爆款视频，对爆款视频进行压缩和截取，并根据评价json文件(Data/内容评价标准库.json)使用Volcengine-LAS的doubao-2.0-pro模型来对视频进行评价打分，并根据对打分结果进行初步分析 ⭐⭐⭐⭐⭐
│  ├─ Week4_Task2.ipynb         # 经过沟通和反馈过后的进一步处理：对(非)爆款视频进行描述性统计，以及画图 ⭐⭐⭐⭐⭐
├─ Data/                        # 存放原始数据的文件夹
│  ├─ 内容营销本体库.json         # 金运提供的内容营销json文件
│  ├─ 内容评价标准库.json         # 金运提供的内容评价json文件 ⭐⭐⭐⭐⭐
│  ├─ K7视频素材/                # 经过沟通和反馈过后额外提供的Excel文件
│  └─ 金运/                     # 第一次任务提供的Excel文件 (已废弃, 后续不用参考)
│     └─ 抖音每日绩效数据/
├─ Deliverables/                # 可交付的内容
│  ├─ Mid-Term/                 # 中期报告相关内容 ⭐⭐⭐⭐⭐
│  │  ├─ Desc.md                # 中期报告描述文档
│  │  ├─ Charts/                # 中期报告会用到的图片
│  │  └─ Tables/                # 中期报告会用到的表格
│  └─ week2_task3/              # 金运第一次任务的交付内容 (已废弃, 后续不用参考)
│     ├─ figures/
│     ├─ report_week2_task3.aux
│     ├─ report_week2_task3.log
│     ├─ report_week2_task3.out
│     ├─ report_week2_task3.pdf
│     ├─ report_week2_task3.tex
│     ├─ task3_descriptive_stats.xlsx
│     ├─ K7_short_video_analysis_table.xlsx
│     └─ K7直播间短视频分析表.xlsx
├─ Processed_Data/                                  # 处理后的数据的文件夹
│  ├─ chinese_holidays_2022_2026.csv                # 中国节假日
│  ├─ doubao_k7_analysis_result_15s.csv             # 豆包分析的爆款视频结果csv (15s截断版)
│  ├─ doubao_k7_analysis_result_full.csv            # 豆包分析的爆款视频结果csv (完整视频)
│  ├─ k7_filtered_videos.csv                        # K7的爆款视频DataFrame ⭐⭐⭐⭐⭐
│  ├─ 内容营销本体库_compact.txt                      # 金运提供的内容营销json文件的紧凑txt版本
│  ├─ 内容评价标准库_compact.txt                      # 金运提供的内容评价json文件的紧凑txt版本
│  ├─ dy_daily_perf_with_mv_match.xlsx              # 抖音的数据匹配 (已废弃, 后续不用参考)
│  ├─ dy_main_perf.xlsx                             # 抖音的处理结果 (已废弃, 后续不用参考)
│  ├─ dy_meaningful_titles_analysis_result.xlsx     # 抖音的视频标题，用GLM4.7分析的结果 (已废弃, 后续不用参考)
│  ├─ k7_inner_merged_df.xlsx                       # K7视频数据和视频地址匹配的DataFrame ⭐⭐⭐
│  ├─ k7_main_perf.xlsx                             # K7的处理结果 (已废弃, 后续不用参考)
│  ├─ k7_material_desc_with_mv_match.xlsx           # K7的数据匹配 (已废弃, 后续不用参考)
│  ├─ k7_meaningful_titles_analysis_result.xlsx     # K7的视频标题，用GLM4.7分析的结果 (已废弃, 后续不用参考)
│  ├─ main_perf_merged_all.xlsx                     # 将抖音和K7的数据合并 (已废弃, 后续不用参考)
│  ├─ main_perf_merged_common.xlsx                  # 将抖音和K7的数据合并 (已废弃, 后续不用参考)
│  └─ K7VideoProcessed/                             # K7的数据处理后的文件夹(视频太大了，需要的话Call Me!) ⭐⭐⭐
│     ├─ ffmpeg_k7_processed_results.csv            # ffmpeg的处理结果
│     ├─ audio_full/                                # 完整的音频文件夹
│     ├─ transcripts/                               # 根据完整音频用Whisper转译的口播文字稿
│     ├─ video_15s/                                 # 筛选的爆款视频-截断的15s视频
│     └─ video_full/                                # 筛选的爆款视频-完整 ⭐⭐⭐
├─ Task/
│   ├─  Week2_Task.md           # 金运第一次任务
│  	└─  Week4_Task.md           # 经过沟通后的任务清单 & Mid-Term ⭐⭐⭐⭐⭐
│
├─ 外接了一个硬盘来存经过沟通后他们提供的所有视频，一共700GB
├─ .gitignore
└─ Readme.md


