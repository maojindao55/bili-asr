# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import shutil
import subprocess
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

@dataclass
class TranscribeResult:
    status: str
    bvid: str
    aid: int
    duration: float
    segments_count: int
    srt_file: Optional[str]
    txt_file: Optional[str]
    raw_json_file: Optional[str]
    text: str
    segments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "bvid": self.bvid,
            "aid": self.aid,
            "duration": self.duration,
            "segments_count": self.segments_count,
            "srt_file": self.srt_file,
            "txt_file": self.txt_file,
            "raw_json_file": self.raw_json_file,
            "text": self.text,
            "segments": self.segments
        }

def log(msg: str, quiet: bool = False):
    if not quiet:
        sys.stderr.write(f"{msg}\n")
        sys.stderr.flush()

def get_ffmpeg_path() -> Optional[str]:
    """探测可用 FFmpeg 路径"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            return exe
    except Exception:
        pass

    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path

    common_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    return None

def load_cookies(cookie_file: str = "cookies.json"):
    """加载 Cookie 和 CSRF Token"""
    # 优先支持环境变量注入 (Agent 环境)
    env_sess = os.environ.get("BILI_SESSDATA")
    env_jct = os.environ.get("BILI_CSRF") or os.environ.get("BILI_JCT")
    if env_sess and env_jct:
        cookie_str = f"SESSDATA={env_sess}; bili_jct={env_jct}"
        return cookie_str, env_jct

    if not os.path.exists(cookie_file):
        raise FileNotFoundError(f"未找到 Cookie 配置文件: {cookie_file}。请先执行 `bili-asr --login` 配置登录凭证。")

    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    cookies = data.get("cookie_info", {}).get("cookies", [])
    cookie_dict = {item["name"]: item["value"] for item in cookies if "name" in item and "value" in item}
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
    csrf = cookie_dict.get("bili_jct", "")
    return cookie_str, csrf

def format_time_srt(seconds: float) -> str:
    millis = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def convert_audio_to_mp4(audio_path: str, output_mp4: str, ffmpeg_exe: str, quiet: bool = False):
    log("[*] 正在将音频转换为轻量级 MP4 视频...", quiet)
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", "color=c=black:s=1280x720:r=1",
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_mp4
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg 转换失败: {res.stderr.decode('utf-8', errors='ignore')}")
    size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
    log(f"[+] 视频生成完毕: {output_mp4} ({size_mb:.2f} MB)", quiet)

def upload_to_bilibili(mp4_path: str, cookie_file: str, title: str, quiet: bool = False):
    import stream_gears
    log(f"[*] 正在向 B 站上传视频 (标题: {title}, 隐私: 仅自己可见)...", quiet)
    stream_gears.upload(
        video_path=[os.path.abspath(mp4_path)],
        cookie_file=os.path.abspath(cookie_file),
        title=title,
        tid=171,
        tag="音频,转写",
        copyright=2,
        source="OriginalAudio",
        desc="ASR语音识别转写临时稿件",
        extra_fields='{"is_only_self": 1}'
    )
    log("[+] 视频上传成功 (已设为【仅自己可见】)！", quiet)

def get_latest_archive(cookie_str: str) -> Optional[Dict[str, Any]]:
    url = "https://member.bilibili.com/x/web/archives?status=all&pn=1&ps=1"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Cookie": cookie_str,
        "Referer": "https://member.bilibili.com/platform/upload-manager/article"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            archives = data.get("data", {}).get("arc_audits", [])
            if archives:
                arc = archives[0]
                archive_info = arc.get("Archive", {})
                videos = arc.get("videos", [])
                cid = videos[0].get("cid") if videos else None
                return {
                    "bvid": archive_info.get("bvid"),
                    "aid": archive_info.get("aid"),
                    "title": archive_info.get("title"),
                    "state": archive_info.get("state"),
                    "state_desc": archive_info.get("state_desc"),
                    "cid": cid
                }
    except Exception:
        pass
    return None

def query_subtitle_url(bvid: str, cid: int, cookie_str: str) -> Optional[str]:
    url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={bvid}&cid={cid}"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Cookie": cookie_str
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            for sub in subtitles:
                sub_url = sub.get("subtitle_url", "")
                if sub_url and ("aisubtitle" in sub_url or "subtitle" in sub_url):
                    if sub_url.startswith("//"):
                        sub_url = "https:" + sub_url
                    return sub_url
    except Exception:
        pass
    return None

def delete_archive(aid: int, csrf: str, cookie_str: str, quiet: bool = False) -> bool:
    url = "https://member.bilibili.com/x/web/archive/delete"
    data = urllib.parse.urlencode({"aid": aid, "csrf": csrf}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": USER_AGENT,
        "Cookie": cookie_str,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://member.bilibili.com/platform/upload-manager/article",
        "Origin": "https://member.bilibili.com"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 0:
                log(f"[+] B 站临时稿件 (aid: {aid}) 已自动清理删除！", quiet)
                return True
            elif res.get("code") == 340022:
                log(f"[*] 稿件删除触发了极验滑块验证码，请在网页创作中心手动清理。", quiet)
            else:
                log(f"[-] 删除稿件未成功: {res.get('message')}", quiet)
    except Exception as e:
        log(f"[-] 删除请求失败: {e}", quiet)
    return False

def transcribe(
    audio_path: str,
    output_dir: Optional[str] = None,
    cookie_file: str = "cookies.json",
    title: Optional[str] = None,
    auto_delete: bool = False,
    keep_temp: bool = False,
    timeout: int = 1800,
    quiet: bool = False
) -> TranscribeResult:
    """
    核心转写函数
    :param audio_path: 音频或视频文件路径
    :param output_dir: 字幕文件输出目录 (若为 None 则不落盘文件，仅返回数据)
    :param cookie_file: cookies.json 路径
    :param title: 投稿标题
    :param auto_delete: 转写后是否尝试删除 B 站视频
    :param keep_temp: 是否保留本地临时生成的 MP4
    :param timeout: 超时秒数 (默认 1800s / 30分钟)
    :param quiet: 是否静音输出日志
    """
    input_path = os.path.abspath(audio_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件未找到: {input_path}")

    cookie_str, csrf = load_cookies(cookie_file)

    ffmpeg_exe = get_ffmpeg_path()
    if not ffmpeg_exe:
        raise RuntimeError("未找到 ffmpeg，请安装 imageio-ffmpeg 或配置系统 ffmpeg")

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    upload_title = title or f"{base_name[:50]}_{int(time.time())}"
    temp_mp4 = os.path.abspath(f"temp_{base_name}_{int(time.time())}.mp4")

    is_video = input_path.lower().endswith((".mp4", ".flv", ".mkv"))
    upload_target = input_path if is_video else temp_mp4

    if not is_video:
        convert_audio_to_mp4(input_path, temp_mp4, ffmpeg_exe, quiet)

    try:
        upload_to_bilibili(upload_target, cookie_file, upload_title, quiet)

        log("[*] 等待 B 站后台注册新稿件...", quiet)
        bvid, aid, cid = None, None, None
        for _ in range(15):
            time.sleep(3)
            info = get_latest_archive(cookie_str)
            if info:
                bvid = info["bvid"]
                aid = info["aid"]
                cid = info.get("cid")
                log(f"[+] 稿件就绪: BV [{bvid}] | AID [{aid}]", quiet)
                break

        if not bvid:
            raise RuntimeError("未能从稿件列表中找到刚上传的视频，请稍后检查创作中心。")

        log("[*] 等待转码、审核与 AI 语音识别生成字幕...", quiet)
        start_wait = time.time()
        subtitle_url = None

        while True:
            elapsed = int(time.time() - start_wait)
            info = get_latest_archive(cookie_str)
            cid = info.get("cid") or cid

            if cid:
                subtitle_url = query_subtitle_url(bvid, cid, cookie_str)
                if subtitle_url:
                    log(f"\n[+] 成功获取 AI 智能字幕！(耗时 {elapsed} 秒)", quiet)
                    break

            if not quiet:
                sys.stderr.write(f"\r[等待中] 已等待: {elapsed} 秒 ...")
                sys.stderr.flush()

            time.sleep(12)

            if elapsed > timeout:
                raise TimeoutError(f"转录超时 (超过 {timeout} 秒)")

        # 拉取并解析字幕
        req = urllib.request.Request(subtitle_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req) as resp:
            sub_data = json.loads(resp.read().decode("utf-8"))

        body = sub_data.get("body", [])
        duration = float(body[-1].get("to", 0.0)) if body else 0.0

        srt_lines = []
        txt_lines = []
        parsed_segments = []

        for idx, item in enumerate(body, start=1):
            start = float(item.get("from", 0.0))
            end = float(item.get("to", 0.0))
            content = item.get("content", "").strip()

            start_str = format_time_srt(start)
            end_str = format_time_srt(end)

            srt_lines.append(f"{idx}\n{start_str} --> {end_str}\n{content}\n")
            txt_lines.append(f"[{start_str} -> {end_str}] {content}")
            parsed_segments.append({"start": start, "end": end, "text": content})

        full_text = " ".join([seg["text"] for seg in parsed_segments])

        srt_path, txt_path, json_path = None, None, None
        if output_dir:
            out_dir = os.path.abspath(output_dir)
            os.makedirs(out_dir, exist_ok=True)
            srt_path = os.path.join(out_dir, f"{base_name}.srt")
            txt_path = os.path.join(out_dir, f"{base_name}.txt")
            json_path = os.path.join(out_dir, f"{base_name}_raw.json")

            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(srt_lines))
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(txt_lines))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(sub_data, f, ensure_ascii=False, indent=2)

        if auto_delete and aid and csrf:
            delete_archive(aid, csrf, cookie_str, quiet)

        return TranscribeResult(
            status="success",
            bvid=bvid,
            aid=aid,
            duration=duration,
            segments_count=len(body),
            srt_file=srt_path,
            txt_file=txt_path,
            raw_json_file=json_path,
            text=full_text,
            segments=parsed_segments
        )

    finally:
        if not keep_temp and os.path.exists(temp_mp4):
            try:
                os.remove(temp_mp4)
            except Exception:
                pass
