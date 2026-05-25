# Seedance 视频生成 Agent

这个目录负责第 5 步：读取第 4 步生成的分镜和关键帧，用 Seedance 图生视频接口生成每个镜头的视频片段，并可选拼接成完整视频。

默认只生成请求计划，不调用接口：

```bash
python video_agent/seedance_video_agent.py
```

默认读取：

```text
outputs/keyframes/storyboard.json
outputs/keyframes/images/S01.png
outputs/keyframes/images/S02.png
...
```

默认输出：

```text
outputs/videos/seedance_request_plan.json
outputs/videos/seedance_results.json
outputs/videos/clips/S01.mp4
outputs/videos/final_seedance_video.mp4
```

真正调用 Seedance 时，需要配置 API Key。脚本会依次读取：

```bash
export SEEDANCE_API_KEY="你的 Seedance/LAS/Ark API Key"
```

默认 Base URL 已设置为火山方舟接口：

```text
https://ark.cn-beijing.volces.com/api/v3
```

生成单个镜头测试：

```bash
python video_agent/seedance_video_agent.py --submit --only-shots S01
```

生成已有关键帧对应的全部镜头：

```bash
python video_agent/seedance_video_agent.py --submit
```

生成并拼接：

```bash
python video_agent/seedance_video_agent.py --submit --concat
```

如果原关键帧被火山判定为可能包含真人隐私，建议先生成安全首帧，再跑完整视频流程：

```bash
python visual_agent/safe_keyframe_generator.py \
  --storyboard outputs/keyframes/storyboard_k7_audio.json \
  --output-dir outputs/keyframes/k7_safe_images \
  --safe-storyboard outputs/keyframes/storyboard_k7_safe_audio.json \
  --product-dir k7

python video_agent/seedance_video_agent.py \
  --submit \
  --storyboard outputs/keyframes/storyboard_k7_safe_audio.json \
  --keyframe-dir outputs/keyframes/k7_safe_images \
  --output-dir outputs/videos/seedance_k7_audio \
  --generate-audio \
  --no-watermark \
  --concat \
  --compatible-output
```

这种方式的首帧不出现可识别真人脸部，只包含产品、电视界面、手部和客厅环境；Seedance prompt 会在视频阶段允许虚构 AI 广告演员自然入镜。
当前最终版输出为：

```text
outputs/videos/seedance_k7_audio/final_seedance_video_compatible.mp4
```

常用参数：

- `--submit`：真正调用 Seedance；不加时只写请求计划。
- `--only-shots S01,S02`：只生成指定镜头，适合先小额测试。
- `--skip-shots S03`：跳过指定镜头。
- `--use-last-frame`：用下一张关键帧作为尾帧，适合支持首尾帧的模型。
- `--generate-audio`：让支持的模型生成原生音频。
- `--model`：Seedance 模型 ID，默认 `doubao-seedance-2-0-260128`。
- `--base-url`：Seedance 接口地址，也可用环境变量 `SEEDANCE_BASE_URL`。
- `--resolution`：默认不传；如果接口要求可设置 `720p` 或 `1080p`。
- `--ratio`：默认 `9:16`。
- `--concat`：用 `ffmpeg` 拼接已生成片段。
- `--compatible-output`：拼接后再导出一个更容易被播放器打开的 H.264/AAC 兼容版。
