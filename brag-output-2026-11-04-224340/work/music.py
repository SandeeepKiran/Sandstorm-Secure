"""Make soundtrack.wav for the launch video: music and sound effects as one mix.

Key: D minor, 120 BPM. Chords Dm - Bb - F - C, two bars each.
Sound effects use notes from the same key and sit under the music.
The cue times match the timeline in composition/index.html.
Needs: numpy, scipy.
"""
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 23.0
BEAT = 0.5
HERE = Path(__file__).resolve().parent
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(7)

# Scene starts, clicks and other cues (seconds). Keep in sync with index.html.
SCENES = [3.1, 6.3, 11.0, 15.0, 19.4]
CLICKS = [7.9, 9.0, 12.3, 16.4]
END_HIT = 19.4


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff, order=2):
    return sosfilt(butter(order, cutoff, "low", fs=SR, output="sos"), x)


def highpass(x, cutoff, order=2):
    return sosfilt(butter(order, cutoff, "high", fs=SR, output="sos"), x)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def env_adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na, endpoint=False)
    e[na:na + nd] = np.linspace(1, s, nd, endpoint=False)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def add(buf, start, sig):
    i = int(start * SR)
    j = min(N, i + len(sig))
    if i < N:
        buf[i:j] += sig[: j - i]


# Chords as MIDI notes (D minor key).
CHORDS = [
    [50, 57, 62, 65, 69],   # Dm
    [46, 53, 58, 62, 65],   # Bb
    [41, 53, 57, 60, 65],   # F
    [48, 55, 60, 64, 67],   # C
]
BAR = 4 * BEAT
chord_len = 2 * BAR

pad = np.zeros(N)
bass = np.zeros(N)
for k in range(int(np.ceil(DUR / chord_len))):
    start = k * chord_len
    chord = CHORDS[k % 4]
    n = int(min(chord_len + 0.6, DUR - start) * SR)
    if n <= 0:
        continue
    tt = np.arange(n) / SR
    e = env_adsr(n, 0.5, 0.6, 0.85, min(0.8, n / SR / 3))
    voice = np.zeros(n)
    for m in chord[1:]:
        f = hz(m)
        for det in (-0.12, 0.12):
            ph = rng.uniform(0, 2 * np.pi)
            # Soft saw from a few harmonics, so the pad stays warm.
            voice += sum(np.sin(2 * np.pi * f * h * (1 + det / 100) * tt + ph * h) / h ** 1.6 for h in range(1, 6))
    add(pad, start, voice * e)
    # Bass: root on eighth notes, from the reveal onwards.
    root = hz(chord[0] - 12 if chord[0] > 45 else chord[0])
    for b in range(int(chord_len / (BEAT / 2))):
        bt = start + b * BEAT / 2
        if bt < SCENES[0] or bt >= DUR - 1.2:
            continue
        nn = int(0.22 * SR)
        tb = np.arange(nn) / SR
        note = (np.sin(2 * np.pi * root * tb) + 0.3 * np.sin(4 * np.pi * root * tb)) * env_adsr(nn, 0.005, 0.08, 0.5, 0.08)
        add(bass, bt, note * (1.0 if b % 2 == 0 else 0.7))

pad = lowpass(pad, 1800) * 0.05
bass = lowpass(bass, 400) * 0.28

# Drums: soft kick on every beat after the reveal, hats from the first feature.
drums = np.zeros(N)
nk = int(0.35 * SR)
tk = np.arange(nk) / SR
kick = np.sin(2 * np.pi * (48 + 70 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 9)
nh = int(0.06 * SR)
hat = highpass(rng.standard_normal(nh), 7000) * np.exp(-np.arange(nh) / SR * 70)
b = 0
while b * BEAT < DUR - 1.0:
    bt = b * BEAT
    if bt >= SCENES[0] - 0.01:
        add(drums, bt, kick * 0.55)
    if bt >= SCENES[1] - 0.01:
        add(drums, bt + BEAT / 2, hat * 0.10)
    b += 1

# Riser into the reveal, plus soft airy swells at each scene change.
fx = np.zeros(N)
nr = int(2.6 * SR)
riser = bandpass(rng.standard_normal(nr), 600, 5000) * np.linspace(0, 1, nr) ** 2
add(fx, SCENES[0] - 2.6, riser * 0.05)
for s in SCENES[1:]:
    nw = int(0.7 * SR)
    w = bandpass(rng.standard_normal(nw), 400, 3000)
    shape = np.sin(np.pi * np.linspace(0, 1, nw)) ** 2
    add(fx, s - 0.4, w * shape * 0.035)

# Clicks: a short tonal tick on A5 (in key) with a tiny noise transient.
for c in CLICKS:
    nc = int(0.12 * SR)
    tc = np.arange(nc) / SR
    tick = np.sin(2 * np.pi * hz(81) * tc) * np.exp(-tc * 60) * 0.10
    tick[: int(0.004 * SR)] += highpass(rng.standard_normal(int(0.004 * SR)), 3000) * 0.05
    add(fx, c, tick)

# Typing ticks in the hook, very quiet: texture only.
for i in range(26):
    tt0 = 0.15 + i * (1.75 / 26)
    nt = int(0.02 * SR)
    add(fx, tt0, highpass(rng.standard_normal(nt), 4000) * np.exp(-np.arange(nt) / SR * 250) * 0.018)

# Outro: a low D chord hit that rings out.
nhit = int((DUR - END_HIT) * SR)
th = np.arange(nhit) / SR
hit = sum(np.sin(2 * np.pi * hz(m) * th) for m in (38, 50, 57, 62)) * np.exp(-th * 0.9)
add(fx, END_HIT, lowpass(hit, 1500) * 0.07)

mix = pad + bass + drums + fx
# Gentle glue: soft clip, then fade in and out.
mix = np.tanh(mix * 1.4) / 1.4
fade_in = np.clip(t_all / 0.05, 0, 1)
fade_out = np.clip((DUR - t_all) / 1.5, 0, 1)
mix *= fade_in * fade_out
mix /= np.max(np.abs(mix)) / 0.79   # peak about -2 dBFS

# Small stereo width: pad delayed a little on one side.
left = mix
right = mix + np.concatenate([np.zeros(int(0.011 * SR)), pad[: N - int(0.011 * SR)]]) * 0.15
stereo = np.stack([left, right], axis=1)
stereo /= np.max(np.abs(stereo)) / 0.79

pcm = (stereo * 32767).astype("<i2")
import wave

with wave.open(str(HERE / "soundtrack.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote soundtrack.wav")
