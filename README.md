# Ignite: Spell Master

**Game phòng thủ thời gian thực sử dụng nhận diện cử chỉ tay bằng AI**

Người chơi sử dụng cử chỉ tay trước webcam để cast phép thuật, bảo vệ tượng đài khỏi các đợt quái vật tấn công.

> **Nền tảng:** PC + Webcam | **Engine:** Pygame | **AI:** MediaPipe + scikit-learn (SVM)

<!-- TODO: Thêm ảnh screenshot gameplay tổng quan tại đây -->

---

## Mục lục

1. [Cài đặt và Khởi chạy](#cài-đặt-và-khởi-chạy)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Quy trình thu thập dữ liệu](#quy-trình-thu-thập-dữ-liệu)
4. [Quy trình huấn luyện mô hình](#quy-trình-huấn-luyện-mô-hình)
5. [Áp dụng AI vào Game](#áp-dụng-ai-vào-game)
6. [Nội dung Game](#nội-dung-game)
7. [Hướng dẫn chơi](#hướng-dẫn-chơi)

---

## Cài đặt và Khởi chạy

### Yêu cầu

- Python 3.11+
- Webcam (độ phân giải tối thiểu 720p)

### Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Các thư viện chính:

| Thư viện | Phiên bản | Mục đích |
|----------|-----------|----------|
| opencv-python | 4.8.1.78 | Xử lý ảnh từ webcam |
| mediapipe | 0.10.9 | Nhận diện bàn tay (21 landmarks) |
| scikit-learn | >= 1.3.0 | Mô hình SVM phân loại cử chỉ |
| pygame | >= 2.5.0 | Game engine |
| pandas | >= 1.5.0 | Xử lý dữ liệu huấn luyện |
| numpy | >= 1.24.0 | Tính toán số |
| joblib | >= 1.3.0 | Lưu/tải mô hình |

### Khởi chạy

```bash
python start_all.py
```

Hệ thống tự động khởi động 2 tiến trình:
- **Gesture Server** (port 5555): Nhận diện cử chỉ tay từ webcam
- **Pygame Game** (port 6666): Game loop nhận lệnh qua UDP

**Các tùy chọn:**

| Lệnh | Mô tả |
|-------|--------|
| `python start_all.py` | Chạy đầy đủ (game + server + camera) |
| `python start_all.py --no-camera` | Không hiển thị cửa sổ camera |

---

## Kiến trúc hệ thống

<!-- TODO: Thêm sơ đồ kiến trúc tổng quan (architecture diagram) tại đây -->

Hệ thống gồm 2 tiến trình chính giao tiếp qua giao thức UDP:

```
┌─────────────────────────────────┐        UDP (JSON)        ┌──────────────────────────────┐
│     GESTURE SERVER (port 5555)  │ ──────────────────────►  │     PYGAME GAME (port 6666)  │
│                                 │                           │                              │
│  Webcam (1280×720 @ 30 FPS)    │   Payload:                │  Game Loop (60 FPS)          │
│  ↓                              │   {                       │  ↓                           │
│  MediaPipe Hands Detection      │     "type": "spell",      │  Nhận spell event qua UDP    │
│  ↓                              │     "spell": "fire",      │  ↓                           │
│  One Euro Filter (làm mượt)    │     "confidence": 95.5,   │  State Machine:              │
│  ↓                              │     "state": "cast"       │    focus → holding → cast    │
│  Chuẩn hóa 84D vector          │   }                       │  ↓                           │
│  ↓                              │                           │  Entity System (Player,      │
│  SVM RBF Classifier             │                           │    Monster, Statue, Spell)   │
│  ↓                              │                           │  ↓                           │
│  Ngưỡng tin cậy (≥ 90%)        │                           │  Render + Audio              │
│  ↓                              │                           │                              │
│  Broadcast UDP                  │                           │                              │
└─────────────────────────────────┘                           └──────────────────────────────┘
```

### Cấu trúc thư mục

```
SpellMaster/
├── start_all.py                    # Launcher chính
├── ai_controller/                  # Module AI
│   ├── gesture_server.py           # UDP server + gesture state machine
│   ├── spell_recognizer.py         # SVM model + One Euro Filter
│   ├── utils/hand_tracker.py       # MediaPipe wrapper
│   └── data/                       # Dữ liệu huấn luyện
│       ├── csv/                    # 159 file CSV (10 lớp × ~16 file)
│       ├── models/                 # Mô hình đã train (joblib)
│       ├── gesture_model_battle.py # Script huấn luyện
│       └── data_collector.py       # Script thu thập dữ liệu
├── pygame/                         # Game module
│   ├── scripts/                    # Source code game
│   │   ├── main_pygame.py          # Game loop chính
│   │   ├── entity.py               # Player, Monster, Statue, Portal
│   │   ├── spell.py                # Spell system
│   │   ├── spell_bar.py            # UI thanh phép
│   │   ├── map_engine.py           # Tile-based map renderer
│   │   ├── sfx_manager.py          # Quản lý âm thanh
│   │   └── player_ui.py            # HP/MP bar
│   ├── data/                       # JSON config
│   │   ├── stat_config.json        # Chỉ số nhân vật/phép/quái
│   │   ├── level_config.json       # Cấu hình wave
│   │   └── sfx_config.json         # Cấu hình âm thanh
│   └── ingame_assets/              # Sprite, map, UI, sfx
└── docs/                           # Tài liệu thiết kế
    └── GDD_SpellMaster.md          # Game Design Document
```

---

## Quy trình thu thập dữ liệu

### Tổng quan

Dữ liệu được thu thập từ **cử chỉ tay thật** qua webcam sử dụng script `data_collector.py`. Mỗi cử chỉ tương ứng với một phép thuật trong game.

### Phương pháp thu thập

1. **Thiết bị:** Webcam 720p, khoảng cách tay 30–100 cm
2. **Phần mềm:** MediaPipe Hands phát hiện 21 điểm landmark mỗi bàn tay (tổng 42 điểm cho 2 tay)
3. **Quy trình:**
   - Chạy `data_collector.py`, chọn tên cử chỉ cần thu thập
   - Thực hiện cử chỉ trước camera
   - Mỗi frame ghi lại 84 tọa độ (42 điểm × 2 chiều x, y)
   - Dữ liệu lưu vào file CSV tương ứng

### Tiền xử lý dữ liệu

| Bước | Mô tả |
|------|--------|
| **Chuẩn hóa gốc** | Tọa độ được chuyển về gốc tại cổ tay trái (wrist = 0, 0) |
| **Chuẩn hóa tỷ lệ** | Chia cho khoảng cách wrist → MCP (chuẩn hóa kích thước bàn tay) |
| **Làm mượt** | Exponential Moving Average (30% frame mới + 70% frame cũ) |

### Thống kê dữ liệu

- **Tổng số mẫu:** 31,740
- **Số lớp (cử chỉ):** 10
- **Số chiều đặc trưng:** 84
- **Số file CSV:** 159

| Cử chỉ | Số mẫu | Tỷ lệ |
|---------|---------|--------|
| Ice | 3,040 | 12.0% |
| Fire | 2,879 | 11.3% |
| Dark | 2,720 | 10.7% |
| Earth | 2,400 | 9.5% |
| Crystal | 2,400 | 9.5% |
| Phoenix | 2,400 | 9.5% |
| Lightning | 2,400 | 9.5% |
| Air | 2,400 | 9.5% |
| Light | 2,390 | 9.4% |
| Water | 2,363 | 9.3% |

<!-- TODO: Thêm ảnh minh họa cử chỉ tay cho từng phép (gesture reference images) tại đây -->

---

## Quy trình huấn luyện mô hình

### Tách dữ liệu

| Tập dữ liệu | Số mẫu | Tỷ lệ |
|-------------|---------|--------|
| Training | 25,392 | 80% |
| Test | 6,348 | 20% |

### Các mô hình đã thử nghiệm

Script `gesture_model_battle.py` huấn luyện và so sánh 4 mô hình:

| Mô hình | Accuracy | F1-Score | Thời gian suy luận |
|---------|----------|----------|-------------------|
| **SVM (RBF)** | **100.00%** | **1.0000** | **0.915 ms** |
| Random Forest | 99.98% | 0.9998 | 17.231 ms |
| K-Nearest Neighbors | 99.97% | 0.9997 | 2.846 ms |
| MLP Neural Network | ~99.9% | ~0.999 | Không ổn định |

### Mô hình được chọn: SVM (RBF Kernel)

**Lý do chọn:**
- Accuracy cao nhất (100% trên tập test)
- Thời gian suy luận nhanh nhất (0.915 ms) — quan trọng cho real-time
- Ổn định, không cần GPU

**Tham số SVM:**

| Tham số | Giá trị | Mô tả |
|---------|---------|--------|
| Kernel | RBF (Radial Basis Function) | Ánh xạ phi tuyến |
| C | Mặc định (1.0) | Hệ số regularization |
| Gamma | scale | Tự động tính theo số chiều |
| Ngưỡng tin cậy | 90% | Chỉ nhận diện khi confidence ≥ 90% |

### Kết quả chi tiết

<!-- TODO: Thêm ảnh confusion matrix tại đây (file: ai_controller/data/plots/confusion_matrix.png) -->
<!-- TODO: Thêm ảnh so sánh mô hình (file: ai_controller/data/plots/model_comparison.png) -->

Trên tập test 6,348 mẫu, tất cả 10 lớp cử chỉ đều đạt Precision = Recall = F1-Score = 100%.

---

## Áp dụng AI vào Game

### Pipeline nhận diện real-time

```
Webcam (1280×720 @ 30 FPS)
    │
    ▼
MediaPipe Hands Detection
    │  Phát hiện 21 landmarks × 2 bàn tay = 42 điểm
    ▼
Chuẩn hóa vector 84 chiều
    │  Gốc: cổ tay trái, tỷ lệ: kích thước lòng bàn tay
    ▼
SVM RBF Classifier
    │  Phân loại thành 1 trong 10 cử chỉ
    ▼
Kiểm tra ngưỡng tin cậy (≥ 90%)
    │
    ▼
Gesture State Machine (focus → holding → cast)
    │  focus: Phát hiện cử chỉ mới
    │  holding: Giữ cử chỉ (đếm thời gian 1 giây)
    │  cast: Thả tay sau ≥ 1s → cast phép
    │  cancel: Thả tay sớm (< 1s) → hủy
    ▼
UDP Broadcast → Game (port 6666)
```

### One Euro Filter

Bộ lọc thích ứng giúp giảm nhiễu landmark từ MediaPipe mà vẫn giữ được phản hồi nhanh khi cử chỉ thay đổi:

| Tham số | Giá trị | Mục đích |
|---------|---------|----------|
| `min_cutoff` | 0.005 | Mức làm mượt khi tay đứng yên (thấp = mượt hơn) |
| `beta` | 0.0005 | Mức phản hồi khi tay di chuyển (thấp = ít nhạy hơn với noise) |
| `d_cutoff` | 1.0 | Cutoff cho đạo hàm tốc độ |
| `freq` | 30.0 | Tần số lấy mẫu (Hz) |

### Giao thức truyền thông UDP

Server gửi JSON payload qua UDP broadcast:

```json
{
  "type": "spell_detected",
  "spell": "fire",
  "confidence": 95.5,
  "state": "cast",
  "timestamp": 1234567890.123
}
```

| Trường | Kiểu | Mô tả |
|--------|------|--------|
| `type` | string | Loại sự kiện (`spell_detected`) |
| `spell` | string | Tên cử chỉ/phép (fire, ice, ...) |
| `confidence` | float | Độ tin cậy (0–100%) |
| `state` | string | Trạng thái: `focus`, `holding`, `cast`, `cancel` |
| `timestamp` | float | Thời điểm phát hiện |

---

## Nội dung Game

### Thông tin cơ bản

| Thuộc tính | Giá trị |
|-----------|---------|
| Thể loại | Phòng thủ tĩnh (Stationary Defense) |
| Độ phân giải | 1280 × 768 px |
| FPS | 60 |
| Số wave | 7 |
| Mục tiêu | Bảo vệ tượng đài sống sót qua tất cả các wave |

### Thông số người chơi

| Thuộc tính | Giá trị |
|-----------|---------|
| HP tối đa | 100 |
| MP tối đa | 100 |
| Hồi MP | 5 MP/giây |
| Tốc độ di chuyển | 100 px/s |

<!-- TODO: Thêm ảnh sprite nhân vật wizard tại đây -->

### Tượng đài (Statue)

| Thuộc tính | Giá trị |
|-----------|---------|
| HP tối đa | 200 |
| Vị trí | Cố định trên bản đồ |

Khi HP tượng đài hoặc HP người chơi về 0 → **Game Over**.

---

### Danh sách phép thuật

| Icon | Tên | Loại | Sát thương | Mana | Hiệu ứng | Điều kiện mở khóa |
|------|-----|------|-----------|------|-----------|-------------------|
| <!-- TODO: fire icon --> | **Fire** | Đơn mục tiêu | 15 | 10 | Đốt cháy (5 dmg/3s) | Mặc định |
| <!-- TODO: water icon --> | **Water** | Diện rộng | 10 | 12 | Hất tung (1s) | Mặc định |
| <!-- TODO: earth icon --> | **Earth** | Đơn mục tiêu | 20 | 10 | Choáng (1s) | Mặc định |
| <!-- TODO: air icon --> | **Air** | Diện rộng | 8 | 10 | Đẩy lùi (lực 150) | Mặc định |
| <!-- TODO: lightning icon --> | **Lightning** | Đơn mục tiêu | 25 | 15 | Dây chuyền (0.5s delay) | Mặc định |
| <!-- TODO: ice icon --> | **Ice** | Đơn mục tiêu | 12 | 12 | Làm chậm (0.5x, 3s) + Đóng băng (1s) | Mặc định |
| <!-- TODO: dark icon --> | **Dark** | Đơn mục tiêu | 10 | 15 | Nguyền rủa (4 dmg/5s, lây lan) | Mặc định |
| <!-- TODO: light icon --> | **Light** | Diện rộng | 18 | 14 | Đánh kép (1s delay) | Mặc định |
| <!-- TODO: crystal icon --> | **Crystal** | Diện rộng | 30 | 20 | — | Tiêu diệt 10 quái |
| <!-- TODO: phoenix icon --> | **Phoenix** | Diện rộng | 35 | 25 | Nổ trễ | Tiêu diệt 10 quái |

**Ghi chú:** Crystal và Phoenix là phép đặc biệt, yêu cầu tích lũy đủ số lượng tiêu diệt (shared kill counter) mới được sử dụng. Mỗi lần cast sẽ tiêu hao số kill tương ứng.

<!-- TODO: Thêm ảnh hand sign tương ứng cho mỗi phép (file: pygame/ingame_assets/ui/spell_icon/) -->
<!-- TODO: Thêm ảnh hiệu ứng phép thuật (file: pygame/ingame_assets/spell/) -->

---

### Danh sách quái vật

| Sprite | Tên | HP | Sát thương | Tốc độ | Tầm Aggro | Cooldown tấn công | Exp |
|--------|-----|-----|-----------|--------|----------|-------------------|-----|
| <!-- TODO: slime sprite --> | **Slime** | 15 | 5 | 35 | 1000 | 0.6s | 25 |
| <!-- TODO: skeleton sprite --> | **Skeleton** | 20 | 8 | 70 | 1200 | 0.8s | 40 |
| <!-- TODO: orc sprite --> | **Orc** | 30 | 10 | 60 | 1500 | 1.0s | 50 |
| <!-- TODO: werewolf sprite --> | **Werewolf** | 35 | 12 | 70 | 1800 | 0.6s | 120 |
| <!-- TODO: armored_skeleton sprite --> | **Armored Skeleton** | 40 | 10 | 50 | 1200 | 1.0s | 70 |
| <!-- TODO: armored_orc sprite --> | **Armored Orc** | 60 | 12 | 45 | 1500 | 1.2s | 100 |
| <!-- TODO: greatsword_skeleton sprite --> | **Greatsword Skeleton** | 35 | 25 | 40 | 1500 | 2.0s | 90 |
| <!-- TODO: orc_rider sprite --> | **Orc Rider** | 70 | 15 | 80 | 2000 | 1.0s | 130 |
| <!-- TODO: elite_orc sprite --> | **Elite Orc** | 80 | 20 | 50 | 1500 | 1.0s | 150 |
| <!-- TODO: werebear sprite --> | **Werebear** | 100 | 18 | 35 | 1500 | 1.5s | 200 |

<!-- TODO: Thêm ảnh sprite cho từng loại quái (file: pygame/ingame_assets/character/{tên_quái}/) -->

---

### Hệ thống Wave

Game gồm **7 wave**, độ khó tăng dần. Quái vật xuất hiện từ 3 cổng (Portal) ở các vị trí khác nhau trên bản đồ.

| Wave | Thành phần quái vật | Tổng số | Tốc độ spawn | Mô tả |
|------|---------------------|---------|-------------|--------|
| 1 | 3 Slime + 2 Orc | 5 | 3.0s | Wave giới thiệu |
| 2 | 2 Orc + 2 Skeleton + 2 Slime | 6 | 2.5s | Thêm Skeleton |
| 3 | 1 Armored Orc + 2 Orc + 2 Skeleton + 1 Werewolf | 6 | 2.5s | Quái mạnh xuất hiện |
| 4 | 1 Armored Orc + 1 Armored Skeleton + 2 Werewolf + 1 Orc Rider | 5 | 2.0s | Quái tốc độ & giáp |
| 5 | 1 Elite Orc + 1 Armored Orc + 1 Armored Skeleton + 1 Greatsword Skeleton + 1 Orc Rider + 1 Werewolf | 6 | 2.0s | Đa dạng quái mạnh |
| 6 | 2 Elite Orc + 2 Armored Orc + 1 Werebear + 1 Werewolf + 1 Orc Rider + 1 Greatsword Skeleton | 8 | 1.5s | Boss wave |
| 7 | 2 Werebear + 2 Werewolf + 2 Greatsword Skeleton + 2 Elite Orc + 1 Orc Rider | 9 | 1.5s | Wave cuối cùng |

**Cơ chế giữa các wave:**
- Thời gian chờ: 5 giây giữa các wave
- Đếm ngược: 5 giây trước khi wave bắt đầu
- Điều kiện qua wave: Tiêu diệt toàn bộ quái vật

---

### Bản đồ

<!-- TODO: Thêm ảnh screenshot bản đồ game tại đây -->

Bản đồ tile-based gồm 2 lớp:
- **Base layer:** Nền đất, cỏ, đường đi
- **Object layer:** Cây cối, đá, trang trí

Quái vật di chuyển từ 3 cổng (portal) ở bên phải màn hình → tượng đài ở bên trái.

---

## Hướng dẫn chơi

### Trạng thái game

| Trạng thái | Hành động | Kết quả |
|-----------|----------|---------|
| Chờ bắt đầu | Thực hiện bất kỳ cử chỉ nào | Game bắt đầu |
| Đang chơi | Thực hiện cử chỉ để cast phép | Bảo vệ tượng đài |
| Nghỉ giữa wave | Chờ đếm ngược | Wave tiếp theo |
| Game Over | Thực hiện bất kỳ cử chỉ nào | Chơi lại từ Wave 1 |
| Chiến thắng | Sống sót qua 7 wave | Hiển thị màn hình chiến thắng |

### Cách cast phép

1. Đặt **hai bàn tay** trước webcam (khoảng cách 30–100 cm)
2. Thực hiện **hình dạng cử chỉ** tương ứng với phép cần cast
3. **Giữ nguyên** cử chỉ khoảng 1 giây (thanh progress hiển thị trên spell bar)
4. **Thả tay** → phép thuật được cast vào quái vật gần nhất

### Mẹo chơi

- Ánh sáng tốt giúp tăng độ chính xác nhận diện
- Giữ tay ổn định trong suốt quá trình cast
- Sử dụng **Air** để đẩy lùi quái nguy hiểm ra xa tượng đài
- Tích lũy kill để mở khóa **Crystal** và **Phoenix** — sát thương diện rộng cực cao
- Quản lý **mana** hợp lý, ưu tiên phép có hiệu ứng kiểm soát (Ice, Earth)

---

## Cấu hình nâng cao

### Ngưỡng tin cậy

File `ai_controller/spell_recognizer.py`:
```python
self.confidence_threshold = 0.90  # 0.0–1.0 (cao hơn = chặt hơn)
```

### Thời gian giữ cử chỉ

File `ai_controller/gesture_server.py`:
```python
self.gesture_hold_duration = 1.0  # giây
```

---

**Phiên bản:** 1.0  
**Công nghệ:** MediaPipe + Pygame + scikit-learn (SVM RBF)  
**Giao tiếp:** UDP broadcast (port 5555 → 6666)
