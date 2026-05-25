# 分镜与关键帧 Agent

这个目录负责第 4 步：把脚本 Agent 的最终脚本转成分镜、关键帧提示词，并可选调用 OpenAI 图片模型生成关键帧。

默认命令只生成文本产物，不会调用图片接口：

```bash
python visual_agent/keyframe_storyboard_agent.py
```

默认读取：

```text
outputs/final_script/final_script.json
```

默认输出：

```text
outputs/keyframes/storyboard.json
outputs/keyframes/storyboard.md
outputs/keyframes/image_prompts.jsonl
```

如需生成关键帧图片，先设置 Token 工厂分配的 key，然后加 `--generate-images`。脚本默认使用项目里的 OpenAI 兼容地址 `https://ai.ktokenhub.app`：

```bash
export OPENAI_API_KEY="你的 Token 工厂 Key"
python visual_agent/keyframe_storyboard_agent.py --generate-images --image-model gpt-image-2
```

如果同学使用的是别的 OpenAI 兼容地址，可以显式传入：

```bash
python visual_agent/keyframe_storyboard_agent.py --generate-images --base-url "https://你的接口地址" --image-model gpt-image-2
```

常用参数：

- `--input`：指定最终脚本 JSON。
- `--output-dir`：指定输出目录。
- `--max-shots`：控制最多分镜数量，默认 10。
- `--generate-images`：调用 OpenAI 图片模型生成关键帧。
- `--base-url`：OpenAI 兼容 API 地址，默认读取 `OPENAI_BASE_URL`，否则使用 Token 工厂地址。
- `--image-model`：图片模型，默认 `gpt-image-2`。
- `--size`：图片尺寸，默认 `auto`。
- `--retries`：图片接口临时断连时自动重试次数，默认 2。
- `--overwrite`：已存在的 PNG 也重新生成；默认会跳过已有图片，便于断点续跑。
- `--skip-shots`：跳过指定分镜图片生成，例如 `--skip-shots S03,S07`。

## Seedance 安全关键帧

如果第 5 步 Seedance 提示输入图包含真人隐私，可以先生成一版“无可识别真人脸部”的安全首帧。它只保留客厅、电视、产品主机、线材、麦克风、遥控器和手部操作，方便在视频阶段再让 Seedance 生成虚构 AI 广告演员。

```bash
python visual_agent/safe_keyframe_generator.py \
  --storyboard outputs/keyframes/storyboard_k7_audio.json \
  --output-dir outputs/keyframes/k7_safe_images \
  --safe-storyboard outputs/keyframes/storyboard_k7_safe_audio.json \
  --product-dir k7
```

默认输出：

```text
outputs/keyframes/storyboard_k7_safe_audio.json
outputs/keyframes/k7_safe_images/S01.png
outputs/keyframes/k7_safe_images/S02.png
...
```
