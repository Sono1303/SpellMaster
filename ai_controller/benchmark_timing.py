#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SpellMaster — Benchmark: Đo thời gian thực tế từng giai đoạn pipeline.

Chạy:
    cd ai_controller
    python benchmark_timing.py

Yêu cầu: camera + 2 bàn tay trước webcam.
Script sẽ đo 100 frame rồi in kết quả ra console và ghi vào ../time.md
"""

import cv2
import mediapipe as mp
import joblib
import numpy as np
import time
import socket
import json
import warnings
import statistics
from pathlib import Path

warnings.filterwarnings('ignore')

# ── Paths ──
DATA_DIR = Path(__file__).parent / "data"
MODEL_PATH = DATA_DIR / "models" / "best_spell_model.pkl"
OUTPUT_FILE = Path(__file__).parent.parent / "time.md"

NUM_WARMUP = 20        # Warm-up frames (bỏ qua)
NUM_MEASURE = 100      # Số frame dùng để đo

def main():
    print("=" * 70)
    print("SPELLMASTER — BENCHMARK TIMING".center(70))
    print("=" * 70)

    # ── Load model ──
    model = joblib.load(MODEL_PATH)
    print(f"[+] Model loaded from {MODEL_PATH.name}")

    # ── Camera ──
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("[X] Camera not available")
        return
    print("[+] Camera opened 1280x720")

    # ── MediaPipe ──
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        model_complexity=1,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.4,
    )
    print("[+] MediaPipe Hands ready")

    # ── UDP sockets for round-trip measurement ──
    sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_recv.bind(('localhost', 16666))  # Temp port for benchmark
    sock_recv.settimeout(0.1)
    print("[+] UDP sockets ready (localhost)")

    # ── Timing buckets ──
    t_capture = []
    t_mediapipe = []
    t_feature = []
    t_svm = []
    t_udp = []
    t_end2end = []

    print(f"\n[*] Đưa 2 bàn tay lại gần nhau trước camera...")
    print(f"[*] Warm-up {NUM_WARMUP} frames, đo {NUM_MEASURE} frames có 2 tay...\n")

    measured = 0
    warmup_done = 0
    total_frames = 0

    while measured < NUM_MEASURE:
        # ── (A) Camera capture ──
        t0 = time.perf_counter()
        ret, frame = cap.read()
        t1 = time.perf_counter()
        if not ret:
            continue
        total_frames += 1
        frame = cv2.flip(frame, 1)

        # ── (B) MediaPipe ──
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        t2 = time.perf_counter()
        results = hands.process(frame_rgb)
        t3 = time.perf_counter()

        # Show live preview
        h, w, _ = frame.shape
        hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        status = f"Hands: {hand_count}/2 | Warmup: {warmup_done}/{NUM_WARMUP} | Measured: {measured}/{NUM_MEASURE}"
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Benchmark", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[!] Quit by user")
            break

        if not results.multi_hand_landmarks or len(results.multi_hand_landmarks) != 2:
            continue

        # ── Warm-up phase ──
        if warmup_done < NUM_WARMUP:
            warmup_done += 1
            continue

        # ── (C) Feature extraction ──
        t4 = time.perf_counter()
        left_coords = []
        right_coords = []
        left_wrist_x = left_wrist_y = left_palm_size = None

        for hand_lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            lms = [(lm.x, lm.y) for lm in hand_lm.landmark]
            if label == "Left":
                left_wrist_x, left_wrist_y = lms[0]
                px, py = lms[9]
                left_palm_size = max(0.001, np.sqrt((px - left_wrist_x)**2 + (py - left_wrist_y)**2))
                for lx, ly in lms:
                    left_coords.append((lx - left_wrist_x) / left_palm_size)
                    left_coords.append((ly - left_wrist_y) / left_palm_size)

        if left_wrist_x is None:
            continue

        for hand_lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            label = handedness.classification[0].label
            lms = [(lm.x, lm.y) for lm in hand_lm.landmark]
            if label == "Right":
                for lx, ly in lms:
                    right_coords.append((lx - left_wrist_x) / left_palm_size)
                    right_coords.append((ly - left_wrist_y) / left_palm_size)

        if len(left_coords) != 42 or len(right_coords) != 42:
            continue

        feature_vector = np.array(left_coords + right_coords)
        t5 = time.perf_counter()

        # ── (D) SVM inference ──
        t6 = time.perf_counter()
        pred = model.predict([feature_vector])[0]
        proba = model.predict_proba([feature_vector])[0]
        conf = max(proba) * 100
        t7 = time.perf_counter()

        # ── (E) UDP round-trip ──
        payload = json.dumps({
            "type": "spell_detected",
            "spell": pred,
            "confidence": round(conf, 2),
            "state": "cast",
            "timestamp": time.time()
        }).encode()

        t8 = time.perf_counter()
        sock_send.sendto(payload, ('localhost', 16666))
        try:
            data, _ = sock_recv.recvfrom(4096)
        except socket.timeout:
            continue
        t9 = time.perf_counter()

        # ── Record ──
        t_capture.append((t1 - t0) * 1000)
        t_mediapipe.append((t3 - t2) * 1000)
        t_feature.append((t5 - t4) * 1000)
        t_svm.append((t7 - t6) * 1000)
        t_udp.append((t9 - t8) * 1000)
        t_end2end.append((t9 - t0) * 1000)

        measured += 1
        if measured % 25 == 0:
            print(f"  [{measured}/{NUM_MEASURE}] Last: {pred} ({conf:.1f}%)")

    # ── Cleanup ──
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    sock_send.close()
    sock_recv.close()

    if measured < 10:
        print(f"\n[X] Chỉ đo được {measured} frame — không đủ dữ liệu. Hãy đưa 2 tay trước camera.")
        return

    # ── SVM-only bulk inference (thêm phép đo 1000 lần suy luận trên cùng 1 vector) ──
    svm_bulk = []
    sample_vec = np.array(left_coords + right_coords)
    for _ in range(1000):
        ts = time.perf_counter()
        model.predict([sample_vec])
        te = time.perf_counter()
        svm_bulk.append((te - ts) * 1000)

    # ── Statistics ──
    def stats(arr):
        return {
            "mean": statistics.mean(arr),
            "median": statistics.median(arr),
            "min": min(arr),
            "max": max(arr),
            "stdev": statistics.stdev(arr) if len(arr) > 1 else 0,
            "p95": sorted(arr)[int(len(arr) * 0.95)],
        }

    s_cap = stats(t_capture)
    s_mp = stats(t_mediapipe)
    s_feat = stats(t_feature)
    s_svm = stats(t_svm)
    s_svm_bulk = stats(svm_bulk)
    s_udp = stats(t_udp)
    s_e2e = stats(t_end2end)

    # ── Print ──
    print("\n" + "=" * 70)
    print("KẾT QUẢ ĐO THỜI GIAN THỰC TẾ".center(70))
    print(f"(Warm-up: {NUM_WARMUP} frames | Đo: {measured} frames)")
    print("=" * 70)

    def row(name, s):
        print(f"  {name:<30} {s['mean']:>8.3f}  {s['median']:>8.3f}  {s['min']:>8.3f}  {s['max']:>8.3f}  {s['stdev']:>8.3f}  {s['p95']:>8.3f}")

    print(f"  {'Giai đoạn':<30} {'Mean':>8}  {'Median':>8}  {'Min':>8}  {'Max':>8}  {'StDev':>8}  {'P95':>8}  (ms)")
    print("  " + "-" * 88)
    row("(A) Camera capture", s_cap)
    row("(B) MediaPipe detection", s_mp)
    row("(C) Feature extraction", s_feat)
    row("(D) SVM inference (in-loop)", s_svm)
    row("(D') SVM inference (bulk 1000)", s_svm_bulk)
    row("(E) UDP round-trip", s_udp)
    print("  " + "-" * 88)
    row("End-to-end (A→E)", s_e2e)

    total_pipeline = s_cap['mean'] + s_mp['mean'] + s_feat['mean'] + s_svm['mean'] + s_udp['mean']
    print(f"\n  Pipeline mean (sum of stages): {total_pipeline:.3f} ms")
    print(f"  End-to-end mean (wall clock):  {s_e2e['mean']:.3f} ms")

    # ── Write to time.md ──
    md = f"""# Đo thời gian thực tế — SpellMaster

> Kết quả benchmark chạy tự động. Warm-up: {NUM_WARMUP} frame, đo: {measured} frame.
> Camera 1280×720, MediaPipe complexity=1, SVM RBF, UDP localhost.

## 1. Kết quả đo từng giai đoạn

| Giai đoạn | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | StDev (ms) | P95 (ms) |
|-----------|-----------|-------------|----------|----------|------------|----------|
| **(A) Camera capture** | {s_cap['mean']:.3f} | {s_cap['median']:.3f} | {s_cap['min']:.3f} | {s_cap['max']:.3f} | {s_cap['stdev']:.3f} | {s_cap['p95']:.3f} |
| **(B) MediaPipe detection** | {s_mp['mean']:.3f} | {s_mp['median']:.3f} | {s_mp['min']:.3f} | {s_mp['max']:.3f} | {s_mp['stdev']:.3f} | {s_mp['p95']:.3f} |
| **(C) Feature extraction** | {s_feat['mean']:.3f} | {s_feat['median']:.3f} | {s_feat['min']:.3f} | {s_feat['max']:.3f} | {s_feat['stdev']:.3f} | {s_feat['p95']:.3f} |
| **(D) SVM inference (in-loop)** | {s_svm['mean']:.3f} | {s_svm['median']:.3f} | {s_svm['min']:.3f} | {s_svm['max']:.3f} | {s_svm['stdev']:.3f} | {s_svm['p95']:.3f} |
| **(D') SVM inference (bulk ×1000)** | {s_svm_bulk['mean']:.3f} | {s_svm_bulk['median']:.3f} | {s_svm_bulk['min']:.3f} | {s_svm_bulk['max']:.3f} | {s_svm_bulk['stdev']:.3f} | {s_svm_bulk['p95']:.3f} |
| **(E) UDP round-trip (localhost)** | {s_udp['mean']:.3f} | {s_udp['median']:.3f} | {s_udp['min']:.3f} | {s_udp['max']:.3f} | {s_udp['stdev']:.3f} | {s_udp['p95']:.3f} |
| **End-to-end (A → E)** | {s_e2e['mean']:.3f} | {s_e2e['median']:.3f} | {s_e2e['min']:.3f} | {s_e2e['max']:.3f} | {s_e2e['stdev']:.3f} | {s_e2e['p95']:.3f} |

## 2. Tổng hợp

| Chỉ số | Giá trị |
|--------|---------|
| Pipeline mean (tổng các giai đoạn) | **{total_pipeline:.2f} ms** |
| End-to-end mean (wall clock) | **{s_e2e['mean']:.2f} ms** |
| Thời gian SVM trung bình (bulk) | **{s_svm_bulk['mean']:.3f} ms** |
| Số frame đo | {measured} |
| Số frame warm-up | {NUM_WARMUP} |

## 3. Pipeline

```
Camera ──► MediaPipe ──► Feature Extract ──► SVM Predict ──► UDP ──► Game
{s_cap['mean']:.1f}ms    {s_mp['mean']:.1f}ms       {s_feat['mean']:.2f}ms         {s_svm['mean']:.2f}ms      {s_udp['mean']:.2f}ms
```

## 4. Phân tích

- **Bottleneck chính**: MediaPipe detection chiếm phần lớn thời gian ({s_mp['mean']:.1f}/{s_e2e['mean']:.1f} ms = {s_mp['mean']/s_e2e['mean']*100:.0f}% end-to-end).
- **SVM inference**: Cực nhanh ({s_svm_bulk['mean']:.3f} ms trung bình trên 1000 lần đo).
- **UDP localhost**: Gần như tức thì ({s_udp['mean']:.3f} ms round-trip).
- **Feature extraction**: Không đáng kể ({s_feat['mean']:.3f} ms).
- **Camera capture**: Phụ thuộc vào phần cứng và driver ({s_cap['mean']:.1f} ms).

### Độ trễ đến game (thực tế)

Thời gian từ lúc camera chụp frame đến lúc game nhận được event qua UDP:

$$t_{{system}} = {s_cap['mean']:.1f} + {s_mp['mean']:.1f} + {s_feat['mean']:.2f} + {s_svm['mean']:.2f} + {s_udp['mean']:.2f} = {total_pipeline:.1f} \\text{{ ms}}$$

Cộng thêm thời gian chờ game frame (0 – 16.7 ms ở 60 FPS):

$$t_{{total}} = {total_pipeline:.1f} + 8.3 \\approx {total_pipeline + 8.3:.0f} \\text{{ ms (trung bình)}}$$

Thời gian cast tổng cộng (bao gồm 1s giữ cử chỉ):

$$t_{{cast}} = {total_pipeline + 8.3:.0f} + 1000 \\approx {total_pipeline + 8.3 + 1000:.0f} \\text{{ ms}}$$

*Trong đó 1000 ms là thời gian giữ cử chỉ có chủ đích (game design), không phải độ trễ hệ thống.*
"""
    OUTPUT_FILE.write_text(md, encoding='utf-8')
    print(f"\n[+] Đã ghi kết quả vào {OUTPUT_FILE}")
    print("Done!")


if __name__ == "__main__":
    main()
