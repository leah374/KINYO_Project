# KINYO 视频生成使用说明

这份说明给后续想用本项目生成视频的人。当前最终版流程是：

```text
脚本/念白要求 -> 无脸安全关键帧 -> Seedance 图生视频 + 音频 -> 拼接兼容版 MP4
```

## 当前最终产物

最终视频：

```text
outputs/videos/seedance_k7_audio/final_seedance_video_compatible.mp4
```

关键帧：

```text
outputs/keyframes/k7_safe_images/
```

最终分镜和念白：

```text
outputs/keyframes/storyboard_k7_safe_audio.json
```

## 重新生成完整视频

先设置火山方舟 API Key：

```bash
export ARK_API_KEY="你的火山方舟 API Key"
```

生成无脸安全关键帧：

```bash
python visual_agent/safe_keyframe_generator.py \
  --storyboard outputs/keyframes/storyboard_k7_audio.json \
  --output-dir outputs/keyframes/k7_safe_images \
  --safe-storyboard outputs/keyframes/storyboard_k7_safe_audio.json \
  --product-dir k7
```

调用 Seedance 生成有声视频片段并拼接兼容版：

```bash
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

## 想更改要求时改哪里

### 1. 改产品图片

把新的产品图放进：

```text
k7/
```

建议使用白底或干净背景图，主机和麦克风清晰可见。替换后重新运行“生成无脸安全关键帧”和“调用 Seedance”两步。

### 2. 改画面内容

编辑：

```text
outputs/keyframes/storyboard_k7_audio.json
```

每个镜头主要改：

- `visual_beat`：这一镜头画面要发生什么。
- `camera`：机位要求。
- `motion`：动作和镜头运动。

不要在 `subtitle` 里写内容；当前最终要求是不显示字幕。

### 3. 改台词念白

还是编辑：

```text
outputs/keyframes/storyboard_k7_audio.json
```

改每个镜头的：

```json
"voiceover": "这里写这一镜头要念的口播"
```

建议每条念白只讲一个信息点，避免重复。当前结构是：

```text
痛点 -> 产品外观 -> 连接方式 -> 操作简单 -> 家庭场景 -> 下单引导
```

### 4. 改音乐或声音风格

编辑：

```text
video_agent/seedance_video_agent.py
```

搜索：

```text
音频要求
```

可以把“普通话女声”“轻快、温暖、家庭氛围”等描述改成你想要的风格。注意要保留“原创免版权”，避免触发 Seedance 输出版权审核。

### 5. 如果视频被审核拦截

常见原因和处理：

- 输入图真人隐私：关键帧避免正脸，只保留手部、产品、电视和客厅。
- 输出版权限制：不要出现真实歌名、影视名、歌手、平台名、商标或版权素材。
- 字幕/文字乱入：在 prompt 里强调“不出现字幕、促销大字、角标文案或任何可读文字”。

## 主要脚本

```text
visual_agent/safe_keyframe_generator.py
video_agent/seedance_video_agent.py
```

`safe_keyframe_generator.py` 负责生成不含可识别真人脸部的安全首帧。

`seedance_video_agent.py` 负责提交 Seedance 任务、轮询结果、下载片段、拼接最终视频。
