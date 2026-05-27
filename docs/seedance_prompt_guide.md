# Doubao Seedance 2.0 Prompt Guide

> Reference: Official documentation from Volcengine (火山方舟)

---

## 1. Basic Formulas

### 1.1 Multi-modal Reference
Extract elements from source materials to generate a new video.

**Use cases**: Action transfer, subject reuse, atmosphere reference

**Recommended patterns**:
- Image reference: `参考 <图片N> 中的 <主体N>，生成...`
- Video reference: `参考 <视频N> 中的 <动作/运镜/风格/音效>，生成...`
- Audio reference: `参考 <音频N> 中的音色，生成...`

### 1.2 Video Editing
Modify part or all of the original video. Unmentioned parts remain unchanged.

**Use cases**: Partial replacement, subject removal, attribute modification

**Recommended patterns**:
- Add element: `清晰描述 <元素特征> + <出现时机> + <出现位置>`
- Modify element: `严格编辑 <视频N>，将其中的 <原特征> 修改为 <新特征>`
- Delete element: Point out the element to delete; emphasize elements that should remain unchanged

### 1.3 Video Extension
Extend the original video in the time dimension, keeping audio/video style, subject, and narrative consistent.

**Use cases**: Continue plot, extend action, complete segments

**Recommended patterns**:
- Extend video: `向前/向后延长 <视频N>，生成...`
- Track completion: `<视频1> + <过渡画面描述> + 接 <视频2> + <过渡画面描述> + 接 <视频3>`

> **Important**: For editing/extending tasks, use `<视频N>` directly, NOT `参考 <视频N>`, to avoid being misinterpreted as a reference task.

### 1.4 Combined Tasks
Reference one material while editing another.

**Pattern**: `参考 <图片/视频N> 的 [参考维度]，严格编辑 <视频X>，[具体编辑内容]`

---

## 2. Advanced Formula

**Template**:
```
精准主体 + 动作细节 + 场景环境 + 光影色调 + 镜头运镜 + 视觉风格 + 画质 + 约束条件
```

**Process**: 
1. First lock in "who" is "doing what"
2. Then explain "where", "what atmosphere"
3. Then tell the model "how to shoot"
4. Finally use style, quality, and constraints to tighten the result

---

## 3. Key Elements

### 3.1 Define Subject

**Basic definition**:
```
将 <图片/视频N> 中的 [主体核心特征] 定义为 <主体N>
```

**Core feature requirements**: Use 2-3 clear, stable static features (clothing, hairstyle, appearance, category) to ensure unique identifiability

**Example**:
```
将图片1中穿红色连衣裙、戴草帽的女人定义为主体1
将图片1中穿红色连衣裙、戴草帽的女人定义为张红
```

**Multi-material same subject**:
```
将图片1中的 [...] 、图片2中的 [...] 定义为 <主体N>
```

**Multi-subject scene**: Define each subject separately with unique tags

**Example**:
```
将视频1中的高个子男人定义为警察，将另一个矮个子男人定义为小偷。场景设定为拥挤的白天集市，阳光明媚，周围有许多水果摊位和密集的行人，充满市井生活气息。小偷在拥挤的集市人群中惊慌失措地向前狂奔，警察在后方紧随其后全速追赶，两人快速穿梭在各个摊位之间。手持镜头向前快速跟拍，画面带有轻微真实的晃动感，营造追逐的紧张氛围。
```

> **Important**: Each time a subject is mentioned, use clear reference. Two methods:
> - For undefined subjects: Use `<主体N>@<图片N>` format
> - For defined subjects: Use the same tag consistently throughout

### 3.2 Shot Sequence (分镜时序)

The model internally decouples space and time. Best practice is timeline-based shots:

**Recommended structure**:
```
镜头1：[运镜/切换方式] + [主体动作与表情] + [位置或空间变化] + [音频信息]
镜头2：...
镜头3：...
```

**Example**:
```
镜头1：街巷侧拍，男人缓慢起跑，带有急促的呼吸感。
镜头2：男人撞翻水果摊，镜头快速摇动并给到男人惊恐的特写。
镜头3：男人翻过矮墙消失，镜头缓慢拉远定格在空荡的街道。
```

**Rules**:
- Use `镜头1`, `镜头2`, `镜头3` markers, organize by event sequence (main first, then secondary)
- Model's support for precise timing (e.g., "0-3 seconds") is unstable, avoid forcing time limits

**Each shot should include**:
1. Camera movement or switch method
2. Subject action and expression
3. Position or spatial changes
4. Audio information

### 3.3 Action Description Requirements

#### 3.3.1 Limbs + Degree Quantification
Actions should be specific to body parts with amplitude, speed, force descriptions.

**Example**: 缓慢抬手, 快速转头, 用力蹬地, 微微低头

#### 3.3.2 Prioritize Slow Continuous Small Actions
Avoid high-burst, large-dynamic actions like sprinting, big jumps, violent rolling.

**Preferred**: 缓慢行走, 轻轻抬手, 微微低头, 顺势坐下

#### 3.3.3 Add Action Transitions
Describe the inertia and connection between actions for natural continuity.

**Example**: 借着转身惯性顺势抬手, 从停顿状态自然过渡到举手

#### 3.3.4 Externalize Emotions as Actions
Use specific body details instead of abstract emotion words.

| Abstract Emotion | Externalized as Actions & Details |
|------------------|-----------------------------------|
| 悲伤 | 低头、肩膀微微颤抖、眼眶泛红、手指无意识地攥紧衣角、泪水在眼眶里打转但没有落下 |
| 喜悦 | 嘴角抑制不住地上扬、眉眼舒展、脚步变得轻快、下意识地哼起小曲、忍不住原地转个圈 |
| 紧张/焦虑 | 频繁地看手表、手指不停敲击桌面、呼吸急促、眼神闪躲、无意识地啃咬指甲 |
| 愤怒 | 双拳紧握、下颌线紧绷、胸口剧烈起伏、眼神如刀般锐利、从牙缝里挤出话语 |
| 释然 | 长长地舒了一口气、紧绷的肩膀完全放松下来、脸上露出久违的、淡淡的微笑、抬头望向远方 |

### 3.4 Camera Movement (运镜写法)

The model understands camera terminology well. Use standard terms directly.

**Common terms**: 中景, 特写, 全景, 缓慢推镜, 平稳横移, 固定镜头

> **Important**: Try to specify only 1 camera movement per shot. Do not combine push/pull/pan/tilt simultaneously as it increases instability.

### 3.5 Quality, Style & Constraints

#### Quality (画质)
Define clarity, detail texture, and lighting quality.

**Example**: 高清, 细节丰富, 电影质感, 色彩自然, 光影柔和

#### Style (风格)
Set overall art style and visual tone.

**Example**: 赛博朋克冷蓝紫色调, 复古胶片, 日系清新

#### Constraints (约束词)
Critical for avoiding defects, distortions, and unreasonable elements.

**Common constraint templates**:
- Avoid subtitles: `保持无字幕`, `避免生成任何文字或字幕`
- Avoid logo: `不要生成Logo`
- Avoid watermark: `不要生成水印`

---

## 4. Symbol Conventions

| Information Type | Symbol | Example |
|------------------|--------|---------|
| Music | （） | （背景中播放着快节奏的摇滚乐） |
| Sound effects | <> | <远处传来狗叫声> |
| Dialogue | {} | {你好，世界}. For non-Chinese/English, specify language: 用日语说道{こんにちは} |
| Subtitles | 【】 | 【第一章：启程】 |

---

## 5. Practical Cases

### Case 1: Emotional Drama (Dialogue-focused)

**Materials**:
- @图片1: Female lead bust shot
- @图片2: Dorm scene reference
- @视频1: Indoor dialogue camera reference
- @音频1: Indoor ambient sound or light music

**Prompt**:
```
@图片1 中的女孩作为主角，@图片2 作为宿舍场景风格参考，参考 @视频1 的运镜方式。

镜头1：傍晚时分，女孩 @图片1 脚步轻快地走到宿舍门口 @图片2，镜头中景平稳跟拍，暖黄色日光从窗外洒进走廊，她在门口停顿一下，深呼吸，表情略带紧张。

镜头2：女孩 @图片1 推开门走进宿舍，镜头切到室内中景，舍友们一边整理书本一边抬头看向她，其中一人笑着问 {考得怎么样呀，过了吗}，镜头在几人之间缓慢切换半身特写。

镜头3：女孩 @图片1 先低头露出落寞表情，镜头给到她的近景，随后她抬头憋不住笑意，哈哈大笑说 {骗你们的}，舍友们追着打闹起来，镜头缓慢拉远，定格在宿舍内一片欢声笑语的全景画面。

全程画面高清电影纪实风，色调温暖，光影柔和；人物面部稳定不变形，动作自然流畅，无卡顿无闪烁；环境音效与 @音频1 自然融合。
```

### Case 2: Action Scene (Action/Atmosphere)

**Materials**:
- @图片1: Red-dressed female lead
- @图片2: Black-clothed assassin
- @图片3: Cliff bamboo scene
- @视频1: Martial arts camera reference
- @音频1: Compact drum beats or fighting sound effects

**Prompt**:
```
@图片1 的红衣女子作为女主，@图片2 的黑衣女子作为对手，场景参考 @图片3 的悬崖竹林环境，整体运镜和动作节奏参考 @视频1，背景音效与 @音频1 同步。

镜头1：傍晚，镜头从红衣女子 @图片1 侧面中景缓慢推进，她站在悬崖边拿起酒壶喝酒，衣袂在山风中轻轻摆动，镜头环绕她半圈，从正面推到背影，远处隐约可见竹林中的黑衣人影。

镜头2：镜头变焦渐隐到远景，无人机视角俯瞰整片悬崖和竹林，两人分立山崖两端，山风卷起衣摆和尘土，节奏随鼓点略微加快。

镜头3：镜头切回地面近景，二人缓慢拔剑对峙，红衣女子@图片1 神情从漫不经心转为冷冽，黑衣女子@图片2 目光坚毅，剑尖微微颤动，镜头平稳跟随两人绕圈移动，最后定格在两剑相交前一瞬间的特写。

整体画面烟雨江湖电影感，冷调低饱和，电影胶片质感，光影层次丰富；人物面部和身体比例稳定不变形，动作连贯自然，不僵硬，无穿模无卡顿。
```

---

## 6. Common Problems & Solutions

### 6.1 Character ID Drift

**Symptoms**: Generated character appearance inconsistent with reference, or "face swap" mid-video, leading to celebrity lookalike rejection.

**Root causes**:
- Face reference image mixed with full-body/pose/clothing images
- Face area too small in mixed reference image

**Solutions**:
1. Prepare face close-up: Additional head-only photo (passport style, minimal shoulders/background)
2. Clear subject definition: `<主体1> 的面部特征参考图片1（大头照），妆造参考图片2（全身照）`
3. Important materials first: More important references should be placed earlier in the prompt

> **Note**: Use headshot + full-body shot. Do NOT use character multi-view shots as model may identify different angles as different subjects.

### 6.2 Unwanted Subtitles

**Symptoms**: Video contains subtitles not requested in prompt.

**Solutions**:
1. Add constraint: `保持无字幕`, `避免生成任何文字或字幕`
2. Remove text from reference images/videos first
3. Generate in landscape orientation (lower subtitle probability), then crop to portrait

### 6.3 Unwanted Logo/Watermark

**Solution**: Add constraint: `不要生成水印`, `不要生成Logo`

### 6.4 Style Drift

**Symptoms**: Expecting 2D/3D anime style but reference image is realistic, causing drift to realistic style.

**Solution**: Add explicit style constraint: `2D日漫风格`, `3D国风漫画`. For precise control, convert reference image to target style first.

### 6.5 Extension Jump Cuts

**Symptoms**: Splicing extended video with original shows jumps/rewinds at connection points.

**Solution**: Post-production fix:
1. Import videos into editing software
2. At each connection: remove 6 frames from end of previous video, remove 1 frame from start of next video
3. Repeat for all splice points
4. Export and check smoothness

> **Tip**: When extending, end the generation at a camera cut moment, and start the next video with the new scene.

### 6.6 Twin/Duplicate Problem

**Symptoms**: In multi-character scenes with character multi-view references, same character appears twice in one frame.

**Root causes**:
- Unclear subject definitions
- Multi-view references cause character confusion

**Solutions**:
1. Clear character association: `张三（对应图片1）将绿色存折扔向站立的李四（对应图片2）`
2. Add global constraint: `视频全程禁止出现外形、着装、配饰完全一致的人物，禁止生成同款分身、双胞胎效果`
3. Use single-person photos, not multi-view references
4. Simplify prompt - remove irrelevant content

### 6.7 Quality Degradation in Extensions

**Symptoms**: Using generated video for extension causes quality degradation. Multiple extensions compound the issue, especially on faces.

**Solutions**:
1. Convert original video to white model: `将视频转为白色3D模型，人物统一为纯白3D模型，无色彩、无纹理、无阴影，纯白背景，结构稳定、运动流畅`
2. Prefer HD images as reference
3. Limit number of extension iterations

### 6.8 Effects Don't Match Expectations

**Solution**: Use reference video to define effects instead of text description. Example: `数字"2999"出场方式参考视频1`

### 6.9 Too Many Reference Characters

**Symptoms**: More than 4 reference characters causes instability (missing/duplicate characters).

**Solution**: Generate in groups with ≤4 characters per image, then use multiple group images for video generation.

### 6.10 Noise at Video End

**Symptoms**: Voiceover videos have abrupt clicking/cut-off sounds at the end.

**Solution**: Use audio volume envelope to fade out at the end in editing software.

### 6.11 Chinese Pronunciation Errors

**Symptoms**: Model misreads polyphonic, rare, or similar-looking characters.

**Solution**: Replace problematic characters with homophones. Example: `螭龙山` → `吃龙山`

### 6.12 Voice Timbre Inaccuracy

**Symptoms**: Generated audio timbre differs from reference audio.

**Solutions**:
1. Add detailed timbre description in prompt
2. Keep dialogue style consistent with reference audio's tone and expression

---

## 7. Other Tips

### 7.1 Video Extension vs. Segment Splicing

**Continuous long shot (extension)**: Suitable for single-scene "dialogue scenes" - long conversations, emotional progression, single-path movement. Achieves immersive, seamless one-take effect.

**Scene/action transitions (splicing)**: Suitable for plot turns or complex/fast "action scenes" - chases, fights, montages. Generate segments independently then edit together for rhythm and visual impact.

### 7.2 Material Configuration Strategy

**Four functional roles**:
1. Character anchor: Lock character appearance
2. Scene setting: Lock environment and style
3. Camera reference: Lock camera language and action rhythm
4. Rhythm atmosphere: Control emotion and timbre with audio

**Recommended configuration (4-5 materials total)**:
- Character images: 1-2 (face close-up + full body)
- Scene image: 1
- Camera reference video: 1
- Audio: 1

> **Note**: Don't use maximum materials. Too many cause priority confusion, style conflicts, and subject identification issues.

### 7.3 Language Standards

- Keep dialogue language unified, avoid mixing Chinese and English (except proper nouns)

---

## 8. API Parameter Notes

- **duration**: Model support for precise duration control is unstable; may cause generation issues
- **role field**: Image contents require `"role": "reference_image"` field
- **content structure**: Text first, then images with role specification
- **video_url location**: Found in `response["content"]["video_url"]`

---

## Quick Reference Card

```
[Subject Definition]
将图片N中的[特征1、特征2]定义为主体N

[Shot Sequence]
镜头1：[运镜] + [动作] + [位置] + [音频]
镜头2：...

[Action Guide]
- 具体到肢体部位
- 优先低缓连贯小动作
- 情绪外化为动作细节

[Camera Terms]
中景/特写/全景/推镜/横移/固定镜头

[Quality/Style/Constraints]
高清电影质感 + [风格] + 保持无字幕无Logo无水印

[Symbol Usage]
（）音乐  <>音效  {}台词  【】字幕
```
