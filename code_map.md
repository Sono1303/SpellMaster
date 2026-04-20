# SpellMaster — Bản đồ Mã nguồn (Code Map)

Tài liệu này là **bản đồ toàn hệ thống**: ánh xạ từng module, từng khối code đến vị trí tệp chính xác, kèm mô tả chức năng và cơ chế hoạt động. Được tổ chức theo luồng dữ liệu từ launcher đến màn hình.

> **Ghi chú:** One Euro Filter (`utils/one_euro_filter.py`) đã bị **loại bỏ khỏi pipeline suy diễn** — tệp vẫn còn trên đĩa nhưng không được import ở bất kỳ đâu trong mã nguồn đang chạy.

---

## Mục lục

1. [Launcher](#1-launcher)
2. [AI Controller — Phía nhận diện](#2-ai-controller--phía-nhận-diện)
   - 2.1 [SpellRecognizer — Module suy diễn](#21-spellrecognizer--module-suy-diễn)
   - 2.2 [GestureServer — Vòng lặp chính + UDP](#22-gestureserver--vòng-lặp-chính--udp)
   - 2.3 [Config — Hằng số toàn cục](#23-config--hằng-số-toàn-cục)
3. [Training Pipeline — Huấn luyện mô hình](#3-training-pipeline--huấn-luyện-mô-hình)
   - 3.1 [GestureDataCollector — Thu thập dữ liệu](#31-gesturedatacollector--thu-thập-dữ-liệu)
   - 3.2 [GestureModelBattle — Huấn luyện & so sánh](#32-gesturemodelobattle--huấn-luyện--so-sánh)
4. [Pygame Game — Phía game engine](#4-pygame-game--phía-game-engine)
   - 4.1 [GestureClient — Nhận UDP](#41-gestureclient--nhận-udp)
   - 4.2 [main_pygame — Vòng lặp game](#42-main_pygame--vòng-lặp-game)
   - 4.3 [Entity — Nhân vật & quái](#43-entity--nhân-vật--quái)
   - 4.4 [Spell — Hiệu ứng phép thuật](#44-spell--hiệu-ứng-phép-thuật)
   - 4.5 [SpellBar — Thanh kỹ năng UI](#45-spellbar--thanh-kỹ-năng-ui)
   - 4.6 [MapEngine — Render bản đồ](#46-mapengine--render-bản-đồ)
   - 4.7 [ResourceManager & AnimationCache — Tài nguyên](#47-resourcemanager--animationcache--tài-nguyên)
   - 4.8 [SFXManager — Âm thanh](#48-sfxmanager--âm-thanh)
   - 4.9 [PlayerUI — HUD người chơi](#49-playerui--hud-người-chơi)
   - 4.10 [MapData — Dữ liệu bản đồ](#410-mapdata--dữ-liệu-bản-đồ)
5. [Config Files — Tệp cấu hình JSON](#5-config-files--tệp-cấu-hình-json)

---

## 1. Launcher

### [`start_all.py`](start_all.py)

**Chức năng:** Điểm khởi động duy nhất của toàn hệ thống. Khởi chạy 2 tiến trình độc lập bằng `subprocess.Popen`.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`verify_files()`](start_all.py#L55) | 55 | Kiểm tra sự tồn tại của 4 tệp bắt buộc trước khi khởi động |
| [`start_gesture_server()`](start_all.py#L76) | 76 | Spawn `gesture_server.py` như subprocess độc lập; chờ 2 giây để xác nhận không crash |
| [`start_pygame_game()`](start_all.py#L103) | 103 | Spawn `main_pygame.py` như subprocess độc lập; tương tự wait & verify |
| [`main()`](start_all.py#L126) | 126 | Parse CLI args (`--no-camera`), gọi verify → server → game theo thứ tự; dọn dẹp khi thoát |

**Cơ chế:** Hai tiến trình chạy song song và **chỉ giao tiếp với nhau qua UDP** — AI server gửi lên cổng `6666`, game nhận từ cổng đó. Không có shared memory hay import chéo.

---

## 2. AI Controller — Phía nhận diện

### 2.1 SpellRecognizer — Module suy diễn

**Tệp:** [`ai_controller/spell_recognizer.py`](ai_controller/spell_recognizer.py)

**Chức năng:** Lớp học máy thuần túy — không chứa vòng lặp game, không gửi UDP. Chịu trách nhiệm duy nhất: nhận frame ảnh, trả về `(tên_phép, độ_tin_cậy)`.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class SpellRecognizer`](ai_controller/spell_recognizer.py#L23) | 23 | Khai báo class wrapper cho MediaPipe + SVM |
| [`__init__()`](ai_controller/spell_recognizer.py#L26) | 26 | Nạp `best_spell_model.pkl` qua `joblib.load()`; khởi tạo `mp.solutions.hands.Hands(complexity=1, max_hands=2)`; đặt `confidence_threshold=0.90` |
| [`extract_hand_landmarks()`](ai_controller/spell_recognizer.py#L90) | 90 | Chuyển `hand_landmarks.landmark` → list 21 tuple `(x, y)` dạng tọa độ chuẩn hóa [0,1] của MediaPipe |
| [`is_hand_count_stable()`](ai_controller/spell_recognizer.py#L97) | 97 | So sánh `current_hand_count` với `previous_hand_count`; trả `False` nếu khác → bỏ qua frame khi tay đột ngột vào/ra khung hình |
| [`process_frame_data()`](ai_controller/spell_recognizer.py#L106) | 106 | **Pipeline chuẩn hóa 2 lượt:** lượt 1 - tay trái → tính gốc tọa độ (cổ tay trái) và tỉ lệ (`palm_size` = khoảng cách wrist→landmark[9]); lượt 2 - tay phải → áp dùng cùng gốc và tỉ lệ đó; ghép → `np.array` shape `(84,)` |
| [`predict_gesture()`](ai_controller/spell_recognizer.py#L200) | 200 | Gọi `model.predict([fv])` + `model.predict_proba([fv])`, kiểm tra `max(proba) > 0.90`, trả `(name, conf%)` hoặc `(None, 0)` |
| [`draw_landmarks()`](ai_controller/spell_recognizer.py#L230) | 230 | Vẽ skeleton tay MediaPipe lên frame OpenCV để hiển thị debug |
| [`draw_info()`](ai_controller/spell_recognizer.py#L242) | 242 | Overlay số tay, tên cử chỉ, confidence, FPS lên góc frame |

**Cơ chế chuẩn hóa chi tiết:**
```
[Raw MediaPipe x,y] → (lx - wrist_x) / palm_size
                       (ly - wrist_y) / palm_size
→ Vector 84 chiều bất biến với vị trí camera và khoảng cách tay
```

---

### 2.2 GestureServer — Vòng lặp chính + UDP

**Tệp:** [`ai_controller/gesture_server.py`](ai_controller/gesture_server.py)

**Chức năng:** Điều phối toàn bộ pipeline phía AI — đọc camera, phát hiện tay, gọi `SpellRecognizer`, quản lý máy trạng thái cử chỉ, và broadcast UDP sang game.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class GestureServer`](ai_controller/gesture_server.py#L34) | 34 | Container cho toàn bộ server AI |
| [`__init__()`](ai_controller/gesture_server.py#L46) | 46 | Bind UDP socket `(host:5555)`, khởi tạo `SpellRecognizer`, khai báo các bộ đếm hold/tolerance, thiết lập `gesture_hold_duration=1.0`, `gesture_change_tolerance=0.2`, `spell_cooldown=0.5` |
| [`broadcast_spell()`](ai_controller/gesture_server.py#L126) | 126 | Đóng gói `{type, spell, confidence, state, timestamp}` thành JSON và `sendto()` địa chỉ game client |
| [`broadcast_status()`](ai_controller/gesture_server.py#L162) | 162 | Gửi gói `server_status` (`ready`/`disconnected`) khi server khởi động hoặc tắt |
| [`get_hand_bounding_box()`](ai_controller/gesture_server.py#L189) | 189 | Tính `(min_x, min_y, max_x, max_y)` chuẩn hóa từ tất cả 21 landmarks của một bàn tay |
| [`hands_are_close()`](ai_controller/gesture_server.py#L203) | 203 | Kiểm tra 2 tay có đủ gần nhau không: khoảng cách trung tâm < `avg_box_size × 1.3`; cử chỉ **chỉ được nhận diện khi tay chạm nhau** |
| [`draw_hand_bounding_boxes()`](ai_controller/gesture_server.py#L249) | 249 | Vẽ bounding box hợp nhất (màu cyan) khi 2 tay gần nhau; vẽ 2 hộp riêng (xanh/đỏ) khi tách |
| [`detect_gesture()`](ai_controller/gesture_server.py#L312) | 312 | Đọc frame từ `cap.read()`, flip, chuyển RGB, gọi `hands.process()`, kiểm tra `hands_are_close()`, gọi `process_frame_data()` và `predict_gesture()` |
| [`apply_spell_cooldown()`](ai_controller/gesture_server.py#L394) | 394 | Chặn cùng một phép gửi lại trong vòng 0.5 giây; phép khác loại luôn được gửi |
| [`update_gesture_hold()`](ai_controller/gesture_server.py#L425) | 425 | **Máy trạng thái 4 pha** — xem chi tiết bên dưới |
| [`run()`](ai_controller/gesture_server.py#L577) | 577 | Vòng lặp chính: `detect_gesture()` → `update_gesture_hold()` → `broadcast_spell()` → hiển thị OpenCV window |
| [`shutdown()`](ai_controller/gesture_server.py#L684) | 684 | Đóng OpenCV windows, gửi `disconnected`, giải phóng camera |

**Máy trạng thái trong `update_gesture_hold()`:**

| Điều kiện đầu vào | Trạng thái trả về | Hành động |
|---|---|---|
| Phát hiện cử chỉ X, không có cử chỉ đang hold | `focus` | Lưu X, ghi `hold_start_time = now` |
| Phát hiện cử chỉ X == cử chỉ đang hold | `holding` | Reset candidate, cập nhật max confidence |
| Phát hiện cử chỉ Y ≠ X đang hold, Y tồn tại < 0.2s | `holding` | Dùng X cũ (trong cửa sổ dung sai) |
| Phát hiện cử chỉ Y ≠ X đang hold, Y tồn tại ≥ 0.2s | `focus` (Y) | Chính thức chuyển sang Y, reset timer |
| Không phát hiện cử chỉ, đã hold ≥ 1s | `cast` | Phép được tung |
| Không phát hiện cử chỉ, đã hold < 1s | `cancel` | Bỏ cử chỉ quá sớm |

---

### 2.3 Config — Hằng số toàn cục

**Tệp:** [`ai_controller/config.py`](ai_controller/config.py)

**Chức năng:** Tập trung các đường dẫn tệp, hằng số màu, tham số cửa sổ.

| Nhóm | Dòng bắt đầu | Nội dung |
|---|---|---|
| [Đường dẫn](ai_controller/config.py#L13) | 13 | `PROJECT_ROOT`, `MODEL_PATH`, `SPRITES_DIR` |
| [Cửa sổ](ai_controller/config.py#L32) | 32 | `WINDOW_WIDTH=1280`, `WINDOW_HEIGHT=720`, tên cửa sổ |
| [Màu sắc](ai_controller/config.py#L44) | 44 | `COLOR_BLACK`, `COLOR_WHITE`, `COLOR_RED`... (BGR cho OpenCV) |

---

## 3. Training Pipeline — Huấn luyện mô hình

### 3.1 GestureDataCollector — Thu thập dữ liệu

**Tệp:** [`ai_controller/data/data_collector.py`](ai_controller/data/data_collector.py)

**Chức năng:** Công cụ offline — mở camera, hiển thị landmark tay theo thời gian thực, cho phép người dùng ghi nhãn và lưu từng mẫu dữ liệu (hai tay) vào CSV.

**Cơ chế:** Áp dụng **đúng cùng pipeline chuẩn hóa** với `spell_recognizer.py` (tịnh tiến về cổ tay trái, chia `palm_size`), đảm bảo không có domain shift giữa dữ liệu huấn luyện và inference. Mỗi mẫu là một hàng 84 cột + nhãn trong CSV.

---

### 3.2 GestureModelBattle — Huấn luyện & so sánh

**Tệp:** [`ai_controller/data/gesture_model_battle.py`](ai_controller/data/gesture_model_battle.py)

**Chức năng:** Huấn luyện 4 thuật toán (SVM RBF, KNN, Random Forest, MLP), đánh giá theo **Balanced Score = 0.7 × accuracy + 0.3 × tốc độ**, lưu mô hình tốt nhất vào `best_spell_model.pkl`.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class GestureModelBattle`](ai_controller/data/gesture_model_battle.py#L22) | 22 | Container huấn luyện; đọc `final_train.csv`, tạo thư mục `plots/` và `models/` |
| `load_and_split_data()` | ~57 | Đọc CSV, tách 80/20 train/test bằng `train_test_split(stratify=y)` |
| `train_all_models()` | — | Lặp qua 4 classifier, đo thời gian inference 1000 lần, tính Balanced Score |
| `save_best_model()` | — | Ghi `joblib.dump(best_model, "best_spell_model.pkl")` |

**Dữ liệu đầu vào:** [`ai_controller/data/final_train.csv`](ai_controller/data/final_train.csv) — tổng hợp từ 150 file CSV thô trong `data/csv/`.

---

## 4. Pygame Game — Phía game engine

### 4.1 GestureClient — Nhận UDP

**Tệp:** [`pygame/scripts/gesture_client.py`](pygame/scripts/gesture_client.py)

**Chức năng:** Cầu nối giữa mạng UDP và game loop — chạy trên luồng nền, nhận gói từ AI server, đẩy vào hàng đợi để game loop đọc an toàn mà không bị blocking.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class GestureClient`](pygame/scripts/gesture_client.py#L42) | 42 | UDP listener với thread-safe queue (maxsize=100) |
| [`__init__()`](pygame/scripts/gesture_client.py#L53) | 53 | Bind UDP socket lên `(host:6666)`; tạo `queue.Queue(maxsize=100)` |
| [`start()`](pygame/scripts/gesture_client.py#L99) | 99 | Tạo `threading.Thread(target=_listener_loop, daemon=True)` và khởi động |
| [`_listener_loop()`](pygame/scripts/gesture_client.py#L132) | 132 | Vòng lặp `recvfrom(4096)` → `json.loads()` → phân loại theo `data['type']`; bắt `socket.timeout` không crash; ngủ `0.1s` khi lỗi |
| [`_handle_spell_detected()`](pygame/scripts/gesture_client.py#L190) | 190 | Đẩy `{spell, confidence, state, timestamp}` vào queue; nếu queue đầy → drop gói |
| [`_handle_server_status()`](pygame/scripts/gesture_client.py#L217) | 217 | Xử lý `ready`/`disconnected` từ AI server khi khởi động/tắt |
| [`get_next_spell()`](pygame/scripts/gesture_client.py#L233) | 233 | `queue.get_nowait()` — **non-blocking**; trả `None` nếu hàng đợi trống |

---

### 4.2 main_pygame — Vòng lặp game

**Tệp:** [`pygame/scripts/main_pygame.py`](pygame/scripts/main_pygame.py)

**Chức năng:** Điểm vào chính của game Pygame — vòng lặp 60 FPS, điều phối wave system, xử lý sự kiện cử chỉ, gọi render.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| **Global state** | 1–140 | Khai báo toàn bộ biến trạng thái game: `GAME_STARTED`, `GAME_OVER`, `VICTORY`, `CURRENT_WAVE`, `GESTURE_TO_SPELL` mapping, các cooldown timer |
| [`GESTURE_TO_SPELL`](pygame/scripts/main_pygame.py#L95) | 95 | Dict ánh xạ `"Fire"→"fire"`, `"Ice"→"ice"` ... (10 phép) |
| [`initialize_pygame()`](pygame/scripts/main_pygame.py#L143) | 143 | `pygame.init()`, tạo cửa sổ kích thước lấy từ `MAP_DIMENSIONS`, khởi tạo font debug |
| [`initialize_game_resources()`](pygame/scripts/main_pygame.py#L172) | 172 | Nạp tất cả tài nguyên: `ResourceManager`, `TileManager`, `TileMap`, `Player`, `SpellManager`, `SFXManager`, `PlayerUI`, `SpellBar`, `GestureClient` |
| [`handle_events()`](pygame/scripts/main_pygame.py#L260) | 260 | Xử lý `pygame.QUIT` và phím tắt (ESC, F1 debug); trả `False` để thoát |
| [`_start_wave_countdown()`](pygame/scripts/main_pygame.py#L292) | 292 | Bắt đầu đếm ngược 3 giây trước mỗi wave |
| [`_begin_wave_spawning()`](pygame/scripts/main_pygame.py#L302) | 302 | Điền `WAVE_MONSTERS_LEFT` từ `level_config.json` theo wave index |
| [`_update_wave_spawn()`](pygame/scripts/main_pygame.py#L317) | 317 | Mỗi `spawn_delay` giây: lấy một quái từ queue, spawn tại portal, giảm bộ đếm |
| [`process_gesture_spells()`](pygame/scripts/main_pygame.py#L421) | 421 | **Xả toàn bộ hàng đợi UDP** mỗi frame; phân nhánh theo `state`: `focus`→chọn phép, `holding`→cập nhật progress bar, `cast`→tung phép, `cancel`→reset |
| [`update_game_state()`](pygame/scripts/main_pygame.py#L638) | 638 | Cập nhật player input/movement, wave system, gọi `process_gesture_spells()`, cập nhật `SpellManager`, tracking kill count |
| [`render_frame()`](pygame/scripts/main_pygame.py#L1039) | 1039 | Vẽ tile map → decorations → monsters → player → spell effects → UI → HUD → stat overlays |
| [`main()`](pygame/scripts/main_pygame.py#L1194) | 1194 | Khởi tạo → vòng lặp 60FPS (`clock.tick(60)`) → `handle_events` → `update_game_state` → `render_frame` → `display.flip()` |

**Khoảng thời gian chống nhiễu được khai báo toàn cục:**

| Biến | Dòng | Giá trị | Ý nghĩa |
|---|---|---|---|
| `GESTURE_SPELL_COOLDOWN_TIME` | 86 | 0.5s | Thời gian tối thiểu giữa 2 lần cast |
| `GESTURE_POST_CAST_COOLDOWN_END` | 89 | timestamp | Timestamp khóa nhận gesture sau cast (0.4s) hoặc cancel (0.2s) |

---

### 4.3 Entity — Nhân vật & quái

**Tệp:** [`pygame/scripts/entity.py`](pygame/scripts/entity.py)

**Chức năng:** Định nghĩa toàn bộ các thực thể trong game với hệ thống animation state machine và collision.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class EntityState(Enum)`](pygame/scripts/entity.py#L24) | 24 | Enum trạng thái: `IDLE`, `WALK`, `ATTACK`, `CAST_SPELL`, `HURT`, `DYING`, `DEAD` |
| [`class Entity`](pygame/scripts/entity.py#L42) | 42 | Lớp cơ sở: vị trí `(x, y)`, collision box `(col_x, col_y, collision_width, collision_height)`, frame animation, `set_state()` |
| [`class Player(Entity)`](pygame/scripts/entity.py#L219) | 219 | Di chuyển WASD, nhảy, hồi mana theo `mana_regen`, quản lý `selected_spell_index`, `casting_stage`, `EntityState.CAST_SPELL` animation |
| [`class Monster(Entity)`](pygame/scripts/entity.py#L637) | 637 | AI tuần tra, phát hiện nhân vật, tấn công, nhận sát thương, áp status effect (ice slow, poison), animation `DYING` → transition sang `DEAD` |
| [`class Statue(Entity)`](pygame/scripts/entity.py#L1113) | 1113 | Mục tiêu phòng thủ; có `display_health` (HP thanh mượt), nhận sát thương từ quái tấn công tới |
| [`class Portal(Entity)`](pygame/scripts/entity.py#L1192) | 1192 | Điểm spawn quái; animation idle loop; xác định `spawn_offset` cho vị trí quái khi xuất hiện |

---

### 4.4 Spell — Hiệu ứng phép thuật

**Tệp:** [`pygame/scripts/spell.py`](pygame/scripts/spell.py)

**Chức năng:** Quản lý toàn bộ vòng đời một phép thuật từ lúc được cast đến khi animation kết thúc và sát thương được áp.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class SpellEffect`](pygame/scripts/spell.py#L25) | 25 | Instance của một phép đang chạy: vị trí `(x,y)`, danh sách frame animation, hitbox, cờ `has_applied_damage`, `finished` |
| [`SpellEffect.get_hitbox()`](pygame/scripts/spell.py#L56) | 56 | Tính `pygame.Rect` từ `config["hitbox"]` + offset; dùng để kiểm tra va chạm với quái |
| [`SpellEffect.apply_effects()`](pygame/scripts/spell.py#L100) | 100 | Kiểm tra hitbox giao với collision box quái; áp sát thương + hiệu ứng trạng thái (freeze, poison, chain lightning) |
| [`class SpellManager`](pygame/scripts/spell.py#L263) | 263 | Quản lý tất cả `SpellEffect` đang active |
| [`SpellManager.cast_by_name()`](pygame/scripts/spell.py#L308) | 308 | Được gọi từ gesture pipeline: kiểm tra mana, tìm mục tiêu gần nhất (`_find_nearest_monster`), tính tọa độ spawn tại collision center của mục tiêu, tạo `SpellEffect` |
| [`SpellManager._find_nearest_monster()`](pygame/scripts/spell.py#L374) | 374 | Euclidean distance từ `player.col_center` tới `monster.col_center`; chọn min |
| [`SpellManager.update()`](pygame/scripts/spell.py#L400) | ~400 | Cập nhật từng `SpellEffect` mỗi frame: tăng frame index, gọi `apply_effects()` đúng một lần, xóa khi `finished=True` |

**Cách tính tọa độ spawn hiệu ứng:**
```python
tx = getattr(target, 'col_x', target.x) + getattr(target, 'collision_width', 0) / 2
ty = getattr(target, 'col_y', target.y) + getattr(target, 'collision_height', 0) / 2
```
→ VFX xuất hiện tại **tâm collision box của quái**, không phải tọa độ đồ họa.

---

### 4.5 SpellBar — Thanh kỹ năng UI

**Tệp:** [`pygame/scripts/spell_bar.py`](pygame/scripts/spell_bar.py)

**Chức năng:** Thanh 10 biểu tượng phép thuật ở góc dưới màn hình; hiển thị highlight khi chọn, thanh nạp phép khi hold, hiệu ứng nhấp nháy khi đủ 1 giây, overlay khóa với kill counter.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class SpellBar`](pygame/scripts/spell_bar.py#L33) | 33 | Nạp icon từ `ingame_assets/ui/spell_icon/`; sử dụng frame đặc biệt cho Crystal và Phoenix |
| `trigger_highlight()` | 138 | Đặt `highlight_timers[i] = highlight_duration (0.3s)`; mỗi frame giảm dần → tắt |
| `set_cast_progress()` | 142 | Cập nhật `cast_progress` (0.0→1.0); được gọi từ `process_gesture_spells()` mỗi frame holding |
| `clear_cast_progress()` | 147 | Reset về 0 khi cast hoặc cancel |
| `trigger_cast_complete_pulse()` | 152 | Bắt đầu `pulse_timer=2.0s`; icon dao động co giãn theo sin wave khi đã nạp đủ |
| `is_locked()` | ~120 | Kiểm tra `unlock_values[name] > 0 and shared_kills < unlock_value`; Crystal và Phoenix cần kill points |
| `consume_unlock()` | ~130 | Trừ `shared_kills` khi dùng phép đặc biệt |
| `draw()` | ~170 | Vẽ icon + frame + lock overlay (đen mờ từ trên xuống theo kill%) + blue cast progress overlay |

**Overlay thanh nạp phép:**
```
[==== BLUE ====][░░░░ REMAINING ░░░░]   ← xóa từ dưới lên
0.0                                 1.0   (progress đảo ngược: remaining = 1 - progress)
```

---

### 4.6 MapEngine — Render bản đồ

**Tệp:** [`pygame/scripts/map_engine.py`](pygame/scripts/map_engine.py)

**Chức năng:** Đọc ma trận tile từ `map_data.py`, nạp sprite sheet tương ứng, vẽ từng tile lên màn hình.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class TileManager`](pygame/scripts/map_engine.py#L15) | 15 | Cache toàn bộ sprite đã cắt từ sprite sheet; tra cứu theo tile ID |
| [`class TileMap`](pygame/scripts/map_engine.py#L98) | 98 | Nhận `LEVEL_1_BASE` (ma trận 20×8), render từng tile `64×64px` tại `(col × 64, row × 64)`; hỗ trợ layer trang trí (decorations) với collision box |

---

### 4.7 ResourceManager & AnimationCache — Tài nguyên

**Tệp:** [`pygame/scripts/resource_manager.py`](pygame/scripts/resource_manager.py)

**Chức năng:** Nạp và cache toàn bộ tài nguyên đồ họa, đảm bảo mỗi ảnh chỉ được đọc từ đĩa một lần duy nhất.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class ResourceManager`](pygame/scripts/resource_manager.py#L17) | 17 | Đọc `assets_map.json` → nạp sprite sheet theo path → cắt frame theo grid config → cache theo key; quản lý tài nguyên cho map tiles, decorations |
| [`class AnimationCache`](pygame/scripts/resource_manager.py#L443) | 443 | Đọc `animations_config.json` → cắt sprite sheet theo `(rows, cols, frame_count)` → lưu vào `animations[category][name]`; phục vụ Player, Monster, SpellEffect |

**Cấu trúc cache:**
```
animations["player"]["idle"] = [frame0, frame1, ...]
animations["spell"]["fire"]  = [frame0, frame1, ...]
animations["monster"]["orc"] = [frame0, frame1, ...]
```

---

### 4.8 SFXManager — Âm thanh

**Tệp:** [`pygame/scripts/sfx_manager.py`](pygame/scripts/sfx_manager.py)

**Chức năng:** Nạp và phát âm thanh hiệu ứng (SFX) với hỗ trợ cắt ghép, thay đổi tốc độ, âm lượng, looping.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`_resample_sound()`](pygame/scripts/sfx_manager.py#L22) | 22 | Thay đổi tốc độ âm thanh bằng cách resample buffer numpy; không phụ thuộc thư viện audio ngoài |
| [`class SFXManager`](pygame/scripts/sfx_manager.py#L39) | 39 | Đọc `sfx_config.json` → nạp tất cả `pygame.mixer.Sound` → lưu cache; cung cấp `play(category, name)` để phát theo key |

---

### 4.9 PlayerUI — HUD người chơi

**Tệp:** [`pygame/scripts/player_ui.py`](pygame/scripts/player_ui.py)

**Chức năng:** Thanh HP và Mana dạng icon container (không phải progress bar đơn giản). Mỗi container đại diện cho 10 HP/Mana; animation blink khi bị thương.

| Khối code | Dòng | Cơ chế |
|---|---|---|
| [`class PlayerUI`](pygame/scripts/player_ui.py#L42) | 42 | Quản lý danh sách container HP và Mana; update từ `player.health` / `player.mana` mỗi frame |
| `update(dt)` | — | So sánh HP hiện tại với HP frame trước; phát animation blink trên container vừa mất |
| `draw()` | — | Vẽ container từ trái qua phải ở góc trên-trái; container trống dùng frame "empty", đầy dùng frame "full" |

---

### 4.10 MapData — Dữ liệu bản đồ

**Tệp:** [`pygame/scripts/map_data.py`](pygame/scripts/map_data.py)

**Chức năng:** Mô tả tĩnh của bản đồ dưới dạng dữ liệu thuần Python — không có logic, không có class.

| Khối code | Dòng | Nội dung |
|---|---|---|
| [`LEVEL_1_BASE`](pygame/scripts/map_data.py#L27) | 27 | Ma trận 20×8 gồm tile ID (int); mỗi phần tử tương ứng một ô 64×64px |
| [`MAP_DIMENSIONS`](pygame/scripts/map_data.py#L55) | 55 | `{cols: 20, rows: 8, tile_size: 64}` → kích thước cửa sổ = 1280×512 |
| [`tile_to_pixel()`](pygame/scripts/map_data.py#L61) | 61 | Chuyển tọa độ tile `(col, row)` → pixel `(x, y)` |
| [`LEVEL_1_OBJECTS`](pygame/scripts/map_data.py#L135) | 135 | Danh sách decoration objects: vị trí, tên sprite, có/không collision box |

---

## 5. Config Files — Tệp cấu hình JSON

Tất cả tham số gameplay đều được externalize vào JSON — không hardcode trong Python.

| Tệp | Đường dẫn | Nội dung chính |
|---|---|---|
| `stat_config.json` | [`pygame/data/stat_config.json`](pygame/data/stat_config.json) | `player` (max_health, mana_regen, spawn), `spells` (damage, mana_cost, hitbox, cooldown, special), `monsters` (speed, health, damage), `player_ui` (icon sizing), `spell_bar` (layout) |
| `level_config.json` | [`pygame/data/level_config.json`](pygame/data/level_config.json) | Vị trí 3 portal (x,y), danh sách wave (`normal_mode.waves[]`) với monster types và spawn_delay |
| `animations_config.json` | [`pygame/data/animations_config.json`](pygame/data/animations_config.json) | Đường dẫn sprite sheet, layout grid `(rows, cols)`, số frame cho mỗi animation category/name |
| `sfx_config.json` | [`pygame/data/sfx_config.json`](pygame/data/sfx_config.json) | Đường dẫn file âm thanh, volume, speed, trim start/end, loop flag |
| `assets_map.json` | [`pygame/data/assets_map.json`](pygame/data/assets_map.json) | Sprite sheet cho tile map, collision size, offset cho decoration objects |

---

## Sơ đồ luồng dữ liệu tổng hợp

```
start_all.py
├── subprocess → gesture_server.py (AI Controller)
│     ├── cv2.VideoCapture → frame BGR
│     ├── MediaPipe Hands → 21 landmarks × 2 tay
│     ├── SpellRecognizer.process_frame_data() → np.array(84,)
│     ├── SpellRecognizer.predict_gesture() → (name, conf%)
│     ├── GestureServer.update_gesture_hold() → {state, spell}
│     └── UDP sendto(6666) → JSON payload
│
└── subprocess → main_pygame.py (Pygame Game)
      ├── GestureClient._listener_loop() [Thread]
      │     └── recvfrom → json.loads → spell_queue.put()
      │
      └── Game Loop @ 60 FPS
            ├── handle_events()          → keyboard/quit
            ├── process_gesture_spells() → queue.get_nowait() × all
            │     ├── focus  → SpellBar.trigger_highlight()
            │     ├── holding → SpellBar.set_cast_progress()
            │     ├── cast   → SpellManager.cast_by_name()
            │     │             └── _find_nearest_monster()
            │     │             └── SpellEffect(tx, ty, target)
            │     └── cancel → reset Player + SpellBar state
            ├── update_game_state()      → Entity AI, wave system
            └── render_frame()          → TileMap → Entities
                                           → SpellEffects → SpellBar → PlayerUI
```
