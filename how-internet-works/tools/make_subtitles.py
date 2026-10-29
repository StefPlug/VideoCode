#!/usr/bin/env python3
"""Build phrase-level SRT/WebVTT subtitles from the per-scene VO clips.

Honest timing model: each scene's narration text is split into short phrases
at sentence/comma boundaries; phrase durations are proportional to their
character count within the measured duration of the real audio clip.
This is phrase-level alignment (not forced word-level alignment).
"""
import json
import re
import subprocess
import sys

VO_STARTS = [0.35, 12.35, 27.35, 42.35, 58.35, 72.35, 92.35, 112.35]

TEXTS = [
    "Ты вводишь адрес — и через секунду видишь страницу. Но что происходит между твоим компьютером и сервером? Проследим путь одного запроса.",
    "В основе всего — физическая передача сигналов. По Wi-Fi данные идут радиоволнами, по оптоволокну — светом, по медным проводам — электрическими сигналами.",
    "Но компьютеры должны понимать, куда отправлять данные. DNS превращает доменное имя в IP-адрес — теперь браузер знает, к какому адресу направить запрос.",
    "Данные разбиваются на небольшие пакеты. IP отвечает за адресацию, а маршрутизаторы передают пакеты между сетями, каждый выбирая следующий участок пути — до самого сервера.",
    "Дальше транспортный уровень. TCP передаёт надёжно: следит за порядком, находит потери и повторяет передачу. UDP проще, без гарантий — его берут, где важна задержка.",
    "Мы на прикладном уровне. HTTP определяет обмен запросами и ответами между клиентом и сервером. HTTPS — это HTTP поверх защищённого TLS-соединения. Браузер запрашивает страницу, сервер отвечает кодом 200 — всё успешно.",
    "Что внутри сервера? Запрос принимает серверное приложение, при нужде обращается к базе данных и формирует ответ. REST API — подход к работе с ресурсами через HTTP: GET получает данные, POST отправляет. FTP — протокол для передачи файлов.",
    "Итак, интернет — это сеть сетей. Физическая среда передаёт сигналы, IP доставляет пакеты через сети, TCP и UDP обеспечивают транспорт, а HTTP связывает приложения. Всё работает вместе — и страница открывается за секунды.",
]


def probe(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]
    )
    return float(out.strip())


def phrases(text: str, max_words: int = 6):
    """Split into phrases at sentence/comma/colon boundaries, max max_words each."""
    parts = re.split(r"(?<=[.!?…:])\s+|,\s+|—\s+", text)
    out = []
    for part in parts:
        words = part.split()
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i : i + max_words])
            if chunk:
                out.append(chunk)
    return out


def fmt_ts(t: str, ms_sep: str) -> str:
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{ms_sep}{ms:03d}"


def main():
    cues = []
    for i, text in enumerate(TEXTS):
        clip = f"assets/audio/vo/scene{i+1:02d}.mp3"
        dur = probe(clip)
        start = VO_STARTS[i]
        ph = phrases(text)
        total_chars = sum(len(p) for p in ph)
        t = start
        for p in ph:
            d = dur * len(p) / total_chars
            cues.append((t, t + d, p))
            t += d

    srt_lines, vtt_lines = ["WEBVTT", ""], []
    for n, (a, b, p) in enumerate(cues, 1):
        srt_lines += [str(n), f"{fmt_ts(a, ',')} --> {fmt_ts(b, ',')}", p, ""]
        vtt_lines += [f"{fmt_ts(a, '.')} --> {fmt_ts(b, '.')}", p, ""]

    import os
    os.makedirs("assets/subs", exist_ok=True)
    with open("assets/subs/how-internet-works.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    with open("assets/subs/how-internet-works.vtt", "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_lines))
    meta = {
        "alignment": "phrase-level (proportional to character count within each measured VO clip)",
        "vo_starts": VO_STARTS,
        "cues": len(cues),
        "vo_durations": {f"scene{i+1:02d}": probe(f"assets/audio/vo/scene{i+1:02d}.mp3") for i in range(8)},
    }
    with open("assets/subs/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(cues)} cues -> assets/subs/how-internet-works.srt/.vtt")


if __name__ == "__main__":
    main()
