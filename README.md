# bili-asr

<p align="center">
  <b>面向开发者与 AI Agent 的零成本、免 GPU 高速语音转文字 CLI 工具</b><br>
  <i>Zero-cost, GPU-free speech-to-text CLI powered by Bilibili Cloud AI.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Agent-Ready-purple.svg" alt="Agent Ready">
</p>

---

## 💡 特性 (Features)

* **零算力负担**：无需本地独立显卡（GPU），普通笔记本/低配服务器均可秒级运行。
* **极速长音频转写**：1 小时超长音频通常仅需 2~3 分钟即可完成全量转写。
* **精准时间轴**：全自动导出标准 `.srt` 字幕、`.txt` 对照文本及原始毫秒级 JSON。
* **Agent 原生友好**：内置 `--json` 静默输出模式，与 LangChain、CrewAI、Cursor、Claude Code 等 AI 框架无缝对接。
* **隐私安全保障**：所有上传的临时视频均强制默认为**【仅自己可见】（私密草稿）**，转写后可配置自动清理。

---

## 📦 安装 (Installation)

克隆本仓库并在项目根目录下安装：

```bash
git clone https://github.com/your-username/bili-asr.git
cd bili-asr
pip install -e .
```

*已内置跨平台 `imageio-ffmpeg`，**无需手动安装系统级别的 FFmpeg**。*

---

## 🔑 首次配置 (Setup Cookie)

首次运行前，需配置一次 B 站账号凭证：

```bash
bili-asr --login
```
根据提示输入浏览器中的 `SESSDATA` 和 `bili_jct` 即可生成本地 `cookies.json`。

> **提示**：在自动化/Agent 容器环境中，也可以直接通过环境变量注入凭证：
> ```bash
> export BILI_SESSDATA="your_sessdata"
> export BILI_CSRF="your_bili_jct"
> ```

---

## 🚀 快速上手 (Quickstart)

### 1. 人类开发者命令行使用
```bash
# 转写音频并生成字幕
bili-asr meeting.mp3

# 指定输出目录，并在完成后自动从 B 站清理临时视频
bili-asr podcast.m4a -o ./subtitles --delete
```

### 2. AI Agent 自动化调用 (`--json` 模式)
在 `--json` 模式下，所有运行日志将重定向至 `stderr`，`stdout` 仅输出结构化的 JSON 结果：

```bash
bili-asr audio.mp3 --json --delete
```

**stdout 输出示例**：
```json
{
  "status": "success",
  "bvid": "BV1xxxxxx",
  "aid": 117544044205480,
  "duration": 3610.7,
  "segments_count": 1766,
  "srt_file": "/path/to/audio.srt",
  "txt_file": "/path/to/audio.txt",
  "text": "接下来您将收听992特报团 河北交通广播为您整点报时...",
  "segments": [
    { "start": 0.0, "end": 3.96, "text": "接下来您将收听992特报团" },
    { "start": 8.52, "end": 13.88, "text": "河北交通广播为您整点报时" }
  ]
}
```

### 3. Python SDK 直接调用
```python
from bili_asr import transcribe

result = transcribe("interview.mp3", output_dir="./output", auto_delete=True)

print(f"总时长: {result.duration} 秒")
print(f"字幕文件路径: {result.srt_file}")
print(f"文本内容: {result.text[:100]}...")
```

---

## 🛠️ 参数说明 (CLI Options)

| 参数 | 说明 |
| :--- | :--- |
| `input` | 输入的音频/视频路径 (`.mp3`, `.wav`, `.m4a`, `.flac`, `.mp4` 等) |
| `-o, --output-dir` | 字幕与文本的输出目录（默认当前目录） |
| `--json` | **【Agent 推荐】** 输出纯净 JSON 到 stdout |
| `--delete` | 转写完成后自动尝试从 B 站删除该临时视频 |
| `--login` | 交互式设置或更新本地 `cookies.json` |
| `--keep-temp` | 保留本地转换的中间 720p MP4 文件 |
| `-v, --version` | 查看工具版本 |

---

## ⚠️ 免责声明 (Disclaimer)

1. 本项目仅供个人学习、计算机语音技术研究与自动化测试使用。
2. 请勿利用本项目进行高频、恶意或侵害哔哩哔哩平台权益的行为。
3. 请严格遵守《哔哩哔哩用户服务协议》，因不当使用造成的一切后果由使用者自行承担。

---

## 📄 开源许可 (License)

本项目基于 [MIT License](LICENSE) 开源。
