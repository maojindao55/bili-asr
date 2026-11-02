# -*- coding: utf-8 -*-
import sys
import json
import argparse
from .core import transcribe, TranscribeResult
from . import __version__

def login_interactive(cookie_file: str = "cookies.json"):
    import stream_gears
    print("=" * 60)
    print("【B 站 Cookie 登录授权设置】")
    print("请在已登录的浏览器打开 bilibili.com，按 F12 -> Application -> Cookies：")
    print("=" * 60)
    sess_data = input("请输入 SESSDATA: ").strip()
    bili_jct = input("请输入 bili_jct (CSRF): ").strip()

    if not sess_data or not bili_jct:
        print("错误: SESSDATA 或 bili_jct 不能为空！")
        sys.exit(1)

    success = stream_gears.login_by_web_cookies(sess_data, bili_jct, file=cookie_file)
    if success:
        print(f"[+] 登录成功！凭证已保存至: {cookie_file}")
    else:
        print("[-] 登录验证失败，请检查 Cookie 是否有效。")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="bili-asr",
        description="bili-asr: Zero-cost, high-speed CLI for audio transcription using Bilibili Cloud AI (Agent & Human friendly)"
    )
    parser.add_argument("input", nargs="?", help="待转写的音频或视频文件路径 (mp3, wav, m4a, flac, mp4...)")
    parser.add_argument("-o", "--output-dir", default=".", help="字幕输出目录 (默认当前目录)")
    parser.add_argument("--json", action="store_true", help="【Agent模式】静默运行，结果以标准 JSON 格式输出至 stdout")
    parser.add_argument("--delete", action="store_true", help="转写完成后自动尝试从 B 站删除临时视频")
    parser.add_argument("--keep-temp", action="store_true", help="保留本地生成的临时 MP4 视频")
    parser.add_argument("--title", help="自定义视频投稿标题")
    parser.add_argument("--cookie-file", default="cookies.json", help="Cookie 配置文件路径 (默认 cookies.json)")
    parser.add_argument("--login", action="store_true", help="配置或更新 B 站 Cookie 凭证")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    if args.login:
        login_interactive(args.cookie_file)
        return

    if not args.input:
        parser.print_help()
        sys.exit(1)

    try:
        res: TranscribeResult = transcribe(
            audio_path=args.input,
            output_dir=args.output_dir,
            cookie_file=args.cookie_file,
            title=args.title,
            auto_delete=args.delete,
            keep_temp=args.keep_temp,
            quiet=args.json  # Agent 模式下日志打到 stderr，不污染 stdout
        )

        if args.json:
            # 严格向 stdout 输出纯净 JSON，方便 AI Agent 直接解析
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print(f"🎉 转写完成！共生成 {res.segments_count} 条字幕段落 (总时长约 {res.duration:.1f} 秒)")
            print(f"📄 SRT 时间轴文件: {res.srt_file}")
            print(f"📄 TXT 纯文本文件: {res.txt_file}")
            print("=" * 60)

    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        else:
            sys.stderr.write(f"\n[ERROR] 执行失败: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
