#!/usr/bin/env python3
"""Synthesize a subtle ambient electronic music bed (130 s) for the video.

No external samples: everything is generated from first principles (sine
harmonics with detune, slow envelopes, LFO shimmer, gentle sub pulse).
Output: assets/audio/bgm/bed.wav (44.1 kHz, 16-bit stereo).
"""
import numpy as np
import wave
import os

SR = 44100
DUR = 130.0
N = int(SR * DUR)
t = np.arange(N) / SR

rng = np.random.default_rng(42)  # seeded: deterministic output

# ---- chord progression (A minor family), 4 chords x 6 s = 24 s cycle ----
# (sub root freq, [(freq, amp), ...] pad partials)
CHORDS = [
    (110.00, [220.00, 261.63, 329.63, 440.00]),           # Am  (A C E A)
    (87.31,  [174.61, 220.00, 261.63, 329.63]),           # Fmaj7 (F A C E)
    (130.81, [196.00, 261.63, 329.63, 392.00]),           # C/G   (G C E G)
    (98.00,  [196.00, 246.94, 293.66, 392.00]),           # G     (G B D G)
]
SEG = 6.0  # seconds per chord
ATTACK, RELEASE = 1.6, 1.8

pad = np.zeros(N)
sub = np.zeros(N)

n_slots = int(np.ceil(DUR / SEG))
for k in range(n_slots):
    root, partials = CHORDS[k % len(CHORDS)]
    start = k * SEG
    s = int(start * SR)
    e = min(int((start + SEG + RELEASE) * SR), N)
    seg_t = t[s:e] - start
    seg_len = e - s
    # envelope: attack / sustain / release
    env = np.ones(seg_len)
    a = int(ATTACK * SR)
    r = int(RELEASE * SR)
    env[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if seg_len > r:
        env[-r:] = np.cos(np.linspace(0, np.pi / 2, r)) ** 2
    voice = np.zeros(seg_len)
    for f in partials:
        for det, w in ((-0.0016, 0.5), (0.0016, 0.5)):  # slight detune pair
            ff = f * (1 + det)
            for h, ha in ((1, 1.0), (2, 0.28), (3, 0.12)):
                voice += w * ha * np.sin(2 * np.pi * ff * h * seg_t + rng.uniform(0, 2 * np.pi))
    voice /= len(partials) * 3.2
    pad[s:e] += voice * env
    # sub pulse: two soft hits per chord segment
    for hit in (0.0, SEG / 2):
        hs = int(hit * SR)
        he = min(hs + int(1.1 * SR), seg_len)
        if hs < seg_len:
            ht = np.arange(he - hs) / SR
            henv = np.exp(-ht * 3.2)
            sub[s + hs:s + he] += np.sin(2 * np.pi * root / 2 * ht) * henv * 0.5

# ---- slow filter movement (one-pole lowpass with LFO cutoff) ----
lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.045 * t - np.pi / 2)  # 0.045 Hz
cutoff = 0.012 + 0.02 * lfo  # in normalized freq units
y = np.zeros(N)
acc = 0.0
for i in range(N):
    acc += cutoff[i] * (pad[i] - acc)
    y[i] = acc

# ---- shimmer: very quiet filtered noise swells every 12 s ----
noise = rng.standard_normal(N)
sh = np.zeros(N)
acc = 0.0
hp = 0.0
for i in range(N):
    acc += 0.004 * (noise[i] - acc)
    hp = noise[i] - acc
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * t[i] / 12.0 - np.pi / 2)
    sh[i] = hp * (swell ** 3)

bed = y * 0.45 + sub * 0.30 + sh * 0.012

# slow global arc: slightly quieter mid-piece, fuller at end
arc = 1.0 + 0.12 * np.sin(2 * np.pi * t / DUR - np.pi / 2) ** 2
bed *= arc

# fades
fi = int(2.5 * SR)
fo = int(3.5 * SR)
bed[:fi] *= np.linspace(0, 1, fi) ** 1.5
bed[-fo:] *= np.linspace(1, 0, fo) ** 1.5

# normalize: peak -8 dBFS
peak = np.max(np.abs(bed)) or 1.0
bed *= 0.4 / peak

# gentle stereo width: tiny delay + gain tilt between channels
delay = int(0.011 * SR)
left = bed.copy()
right = np.concatenate([np.zeros(delay), bed[:-delay]]) * 0.97 + bed * 0.03

out = np.stack([left, right], axis=1)
out16 = np.clip(out * 32767, -32768, 32767).astype(np.int16)

os.makedirs("assets/audio/bgm", exist_ok=True)
with wave.open("assets/audio/bgm/bed.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(out16.tobytes())
print("wrote assets/audio/bgm/bed.wav", DUR, "s")
