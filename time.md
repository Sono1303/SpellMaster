# Đo thời gian thực tế — SpellMaster

> Kết quả benchmark chạy tự động. Warm-up: 20 frame, đo: 100 frame.
> Camera 1280×720, MediaPipe complexity=1, SVM RBF, UDP localhost.

## 1. Kết quả đo từng giai đoạn

| Giai đoạn | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | StDev (ms) | P95 (ms) |
|-----------|-----------|-------------|----------|----------|------------|----------|
| **(A) Camera capture** | 17.004 | 8.655 | 6.465 | 76.810 | 17.784 | 65.737 |
| **(B) MediaPipe detection** | 34.813 | 33.374 | 29.480 | 73.574 | 6.402 | 53.583 |
| **(C) Feature extraction** | 0.099 | 0.094 | 0.072 | 0.186 | 0.019 | 0.146 |
| **(D) SVM inference (in-loop)** | 0.651 | 0.549 | 0.467 | 7.257 | 0.675 | 0.826 |
| **(D') SVM inference (bulk ×1000)** | 0.199 | 0.194 | 0.089 | 0.632 | 0.084 | 0.363 |
| **(E) UDP round-trip (localhost)** | 0.422 | 0.407 | 0.342 | 0.729 | 0.062 | 0.550 |
| **End-to-end (A → E)** | 57.060 | 47.414 | 42.762 | 126.245 | 21.392 | 116.011 |

## 2. Tổng hợp

| Chỉ số | Giá trị |
|--------|---------|
| Pipeline mean (tổng các giai đoạn) | **52.99 ms** |
| End-to-end mean (wall clock) | **57.06 ms** |
| Thời gian SVM trung bình (bulk) | **0.199 ms** |
| Số frame đo | 100 |
| Số frame warm-up | 20 |

## 3. Pipeline

```
Camera ──► MediaPipe ──► Feature Extract ──► SVM Predict ──► UDP ──► Game
17.0ms    34.8ms       0.10ms         0.65ms      0.42ms
```

## 4. Phân tích

- **Bottleneck chính**: MediaPipe detection chiếm phần lớn thời gian (34.8/57.1 ms = 61% end-to-end).
- **SVM inference**: Cực nhanh (0.199 ms trung bình trên 1000 lần đo).
- **UDP localhost**: Gần như tức thì (0.422 ms round-trip).
- **Feature extraction**: Không đáng kể (0.099 ms).
- **Camera capture**: Phụ thuộc vào phần cứng và driver (17.0 ms).

### Độ trễ đến game (thực tế)

Thời gian từ lúc camera chụp frame đến lúc game nhận được event qua UDP:

$$t_{system} = 17.0 + 34.8 + 0.10 + 0.65 + 0.42 = 53.0 \text{ ms}$$

Cộng thêm thời gian chờ game frame (0 – 16.7 ms ở 60 FPS):

$$t_{total} = 53.0 + 8.3 \approx 61 \text{ ms (trung bình)}$$

Thời gian cast tổng cộng (bao gồm 1s giữ cử chỉ):

$$t_{cast} = 61 + 1000 \approx 1061 \text{ ms}$$

*Trong đó 1000 ms là thời gian giữ cử chỉ có chủ đích (game design), không phải độ trễ hệ thống.*
