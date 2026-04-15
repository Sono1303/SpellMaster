# 3.3. Huấn luyện mô hình (Model Training)

Phần này trình bày kiến trúc bộ huấn luyện trong tệp `gesture_model_battle.py`, bao gồm việc thiết lập các thuật toán ứng viên, quy trình huấn luyện và so sánh tự động, và cơ chế đóng gói mô hình tối ưu để tích hợp thời gian thực.

---

## 3.3.1. Thiết lập cấu hình các thuật toán ứng viên

### Danh sách thuật toán tham gia

Hệ thống đăng ký **4 thuật toán ứng viên** trong từ điển `models_config` bên trong phương thức `train_models()`:

| Thuật toán | Lớp sklearn | Mục đích |
|---|---|---|
| Support Vector Machine (SVM) | `SVC` | Phân loại phi tuyến tính mạnh |
| K-Nearest Neighbors (KNN) | `KNeighborsClassifier` | Baseline đơn giản dựa khoảng cách |
| Random Forest | `RandomForestClassifier` | Ensemble nhiều cây quyết định |
| MLP Neural Network | `MLPClassifier` | Mạng nơ-ron nhiều lớp |

### Siêu tham số (Hyperparameters) được cấu hình

```python
models_config = {
    'Random Forest': RandomForestClassifier(
        # ── Tham số được đặt rõ ràng ──
        n_estimators=100,       # 100 cây quyết định trong tập hợp
        random_state=42,        # Hạt giống tái tạo kết quả
        n_jobs=-1,              # Dùng toàn bộ CPU để song song hóa
        # ── Giữ nguyên giá trị mặc định ──
        # max_depth=None        # Cây phát triển đến khi lá thuần, không giới hạn độ sâu
        # max_features='sqrt'   # Mỗi lần chia nhánh xét sqrt(84) ≈ 9 features ngẫu nhiên
        # min_samples_split=2   # Cần ≥ 2 mẫu mới được phép chia nhánh
        # min_samples_leaf=1    # Lá có thể chứa chỉ 1 mẫu
        # bootstrap=True        # Lấy mẫu có hoàn lại (bagging) để xây từng cây
        # criterion='gini'      # Đo độ thuần của nhánh bằng Gini impurity
    ),
    'SVM (RBF)': SVC(
        # ── Tham số được đặt rõ ràng ──
        kernel='rbf',           # Kernel Radial Basis Function — xử lý dữ liệu phi tuyến
        probability=True,       # Bật tính xác suất (dùng cho ngưỡng 90%)
        random_state=42,
        # ── Giữ nguyên giá trị mặc định ──
        # C=1.0                 # Hệ số phạt lỗi phân loại — cân bằng margin vs. sai số
        # gamma='scale'         # γ = 1 / (n_features × Var(X)) — tự động theo dữ liệu
        # tol=1e-3              # Ngưỡng hội tụ của bộ tối ưu
        # class_weight=None     # Mọi lớp có trọng số bằng nhau
    ),
    'K-Nearest Neighbors': KNeighborsClassifier(
        # ── Tham số được đặt rõ ràng ──
        n_neighbors=5,          # Xét 5 điểm lân cận gần nhất
        # ── Giữ nguyên giá trị mặc định ──
        # weights='uniform'     # Mọi lân cận đóng góp như nhau (không theo khoảng cách)
        # metric='minkowski'    # Khoảng cách Minkowski với p=2 = Euclidean
        # algorithm='auto'      # Tự chọn cấu trúc tìm kiếm (ball_tree / kd_tree / brute)
        # leaf_size=30          # Kích thước lá cho ball_tree / kd_tree
    ),
    'MLP Neural Network': MLPClassifier(
        # ── Tham số được đặt rõ ràng ──
        hidden_layer_sizes=(64, 32),  # 2 lớp ẩn: 64 và 32 nơ-ron
        max_iter=500,                  # Tối đa 500 vòng lặp
        random_state=42,
        early_stopping=True,           # Dừng sớm nếu không cải thiện
        validation_fraction=0.1,       # 10% tập train dùng để validate
        # ── Giữ nguyên giá trị mặc định ──
        # activation='relu'            # Hàm kích hoạt ReLU cho các lớp ẩn
        # solver='adam'                # Bộ tối ưu Adam (adaptive learning rate)
        # alpha=1e-4                   # Hệ số L2 regularization chống overfitting
        # learning_rate_init=1e-3      # Tốc độ học ban đầu cho Adam
        # batch_size='auto'            # min(200, n_samples) mẫu mỗi mini-batch
    )
}
```

### Môi trường thử nghiệm đồng nhất

Để đảm bảo tính công bằng khi so sánh, tất cả 4 mô hình được huấn luyện trên **cùng một tập dữ liệu đã chia** (`X_train`, `y_train`) và đánh giá trên **cùng tập kiểm tra** (`X_test`, `y_test`). Điều này thực hiện được nhờ:

- **Một lần chia dữ liệu duy nhất** (`load_and_split_data()`) trước khi huấn luyện bất kỳ mô hình nào.
- **`random_state=42`** được truyền vào cả phép chia dữ liệu lẫn từng mô hình — đảm bảo kết quả tái tạo được (reproducible) mỗi lần chạy.
- **Stratified split**: `train_test_split(..., stratify=y)` — giữ tỉ lệ nhãn giống hệt nhau trong cả tập train lẫn test, tránh thiên lệch do mất cân bằng nhãn.

> **Tại sao giữ tham số ở mức tiêu chuẩn (Default) giúp đánh giá khách quan?**
>
> Mục tiêu của giai đoạn so sánh là tìm ra **thuật toán** phù hợp nhất với đặc điểm dữ liệu, không phải tìm bộ tham số tốt nhất của từng thuật toán. Nếu mỗi mô hình được tinh chỉnh riêng (fine-tuning), sự khác biệt về kết quả sẽ đến từ kỹ năng tinh chỉnh của người lập trình, không phải từ bản chất của thuật toán — gây ra sai số chủ quan. Tham số tiêu chuẩn loại bỏ biến nhiễu này, cho thấy "sức mạnh bản thân" của từng thuật toán trên dữ liệu này.

---

## 3.3.2. Quy trình huấn luyện và so sánh tự động

### Luồng xử lý dữ liệu

```
final_train.csv (31.740 mẫu, 85 cột)
        │
        ▼ df.drop('Label', axis=1)
   X (84 features)  +  y (Label)
        │
        ▼ train_test_split(stratify=y, test_size=0.2, random_state=42)
   X_train: 25.392 mẫu (80%)
   X_test:   6.348 mẫu (20%)
```

**84 features** là tọa độ (x, y) của 21 điểm landmark cho 2 bàn tay:
- 21 điểm × 2 tọa độ × 2 tay = **84 chiều**

**10 nhãn** tương ứng 10 phép thuật: Air, Crystal, Dark, Earth, Fire, Ice, Light, Lightning, Phoenix, Water.

**Phân bố nhãn trong tập train** (sau stratified split):

| Nhãn | Số mẫu | Tỉ lệ |
|---|---|---|
| Ice | 3.040 | 12,0% |
| Fire | 2.879 | 11,3% |
| Dark | 2.720 | 10,7% |
| Earth, Crystal, Phoenix, Lightning, Air | ~2.400 mỗi nhãn | ~9,5% |
| Light | 2.390 | 9,4% |
| Water | 2.363 | 9,3% |

### Cơ chế thực thi

Bốn mô hình được huấn luyện **tuần tự** (sequential) trong vòng lặp `for model_name, model in models_config.items()`, không song song:

```python
for model_name, model in models_config.items():
    start_time = time.time()
    model.fit(self.X_train, self.y_train)   # Huấn luyện
    train_time = time.time() - start_time
    self.models[model_name] = model          # Lưu vào bộ nhớ
```

Lý do chọn tuần tự thay vì song song: đảm bảo log output rõ ràng và tránh xung đột bộ nhớ khi các mô hình lớn (Random Forest với `n_jobs=-1` đã tự song song hóa nội bộ).

### Đánh giá sau huấn luyện

Sau khi tất cả mô hình được huấn luyện, `evaluate_models()` tính 3 chỉ số cho mỗi mô hình:

```python
accuracy = accuracy_score(self.y_test, y_pred)
f1_weighted = f1_score(self.y_test, y_pred, average='weighted')

# Đo thời gian suy luận: 100 lần predict lấy trung bình
for _ in range(100):
    model.predict(self.X_test.iloc[:1])
inference_time_ms = elapsed / 100 * 1000
```

### Logic lựa chọn mô hình "thắng cuộc"

Tiêu chí lựa chọn **không** chỉ dựa vào Accuracy mà dùng **Balanced Score** — điểm tổng hợp ưu tiên tốc độ cho ứng dụng thời gian thực:

```
Balanced Score = (Accuracy × 0.7) + (Speed Score × 0.3)

Speed Score = min(20.0 / (inference_time_ms + 1.0), 1.0)
             └── Chuẩn hóa: inference ≤ 20ms → score = 1.0
```

**Phân bổ trọng số 70/30** phản ánh yêu cầu của SpellMaster:
- 70% Accuracy: nhận diện sai phép thuật là trải nghiệm người chơi tồi
- 30% Speed: độ trễ cao > 100ms gây mất đồng bộ giữa cử chỉ và hiệu ứng

**Kết quả thực tế** (chạy ngày 30/03/2026):

| Mô hình | Accuracy | F1-Score | Inference (ms) | Balanced Score |
|---|---|---|---|---|
| **SVM (RBF)** ✅ | **100,00%** | **1,0000** | **0,915** | **1,0000** |
| Random Forest | 99,98% | 0,9998 | 17,231 | 0,9717 |
| K-Nearest Neighbors | 99,97% | 0,9997 | 2,846 | 0,9905 |

> SVM (RBF) thắng trên **cả 3 tiêu chí** — vừa chính xác nhất, vừa nhanh nhất.

> **Quy trình tự động giảm thiểu sai số chủ quan như thế nào?**
>
> Thay vì người lập trình đọc bảng kết quả rồi "cảm thấy" mô hình nào tốt hơn, hàm `calculate_balanced_score()` lượng hóa quyết định thành một con số duy nhất. `max(..., key=lambda x: calculate_balanced_score(...))` chọn winner hoàn toàn bằng code — không có bước phán đoán thủ công nào giữa đánh giá và lưu mô hình.

---

## 3.3.3. Đóng gói và lưu trữ mô hình (Serialization)

### Phương thức đóng gói: Joblib

Mô hình được lưu bằng **Joblib** thay vì Pickle tiêu chuẩn:

```python
import joblib

model_file = self.models_dir / "best_spell_model.pkl"
joblib.dump(best_model, model_file)
```

**Tại sao Joblib?** Joblib được tối ưu hóa cho các đối tượng NumPy (mảng lớn, ma trận trọng số) — nhanh hơn Pickle tới 2-5× với mô hình sklearn vì nó nén các mảng số học hiệu quả hơn.

### Nội dung file `.pkl`

Tệp `best_spell_model.pkl` không chỉ lưu một con số — nó lưu **toàn bộ trạng thái của đối tượng Python** sau huấn luyện, bao gồm:

| Thành phần trong SVM (RBF) | Mô tả |
|---|---|
| `support_vectors_` | Các vector hỗ trợ (điểm dữ liệu biên giới) |
| `dual_coef_` | Hệ số Lagrange nhân với nhãn |
| `intercept_` | Các hệ số offset cho từng cặp lớp |
| `classes_` | Danh sách 10 nhãn: Air, Crystal, Dark, ... |
| `gamma`, `C` | Siêu tham số kernel RBF |
| `_calibrated_classifiers` | Thông số CalibratedClassifierCV (cho `probability=True`) |

Đây là phép ẩn dụ "não người được đông lạnh": toàn bộ "tri thức" học được từ 25.392 mẫu huấn luyện được cô đọng vào file ~vài MB.

### Cấu trúc tệp đầu ra

```
ai_controller/data/
└── models/
    ├── best_spell_model.pkl      ← Mô hình SVM đã huấn luyện (dùng bởi spell_recognizer.py)
    └── model_statistics.md       ← Báo cáo so sánh tự động sinh
```

Module **Detect** (`spell_recognizer.py`) truy cập mô hình bằng:

```python
# spell_recognizer.py — __init__
self.model = joblib.load(model_path)  # Nạp ngay khi khởi động server
# ...
# Mỗi frame:
pred = self.model.predict([feature_vector])[0]
proba = self.model.predict_proba([feature_vector])[0]
```

### Tại sao Serialization là yếu tố then chốt cho thời gian thực?

Khi game đang chạy, mỗi frame camera (~33ms) cần một kết quả phân loại. Nếu mô hình được huấn luyện lại từ đầu mỗi lần khởi động, thời gian chờ sẽ là **hàng phút** (Random Forest mất ~17ms/inference nhưng huấn luyện lại mất nhiều giờ với 31.740 mẫu). Joblib cho phép **nạp lại mô hình đã có sẵn trong < 1 giây**, đưa hệ thống vào trạng thái sẵn sàng nhận diện ngay lập tức.

### Lợi ích của việc tách biệt Offline Training và Online Inference

| Khía cạnh | Offline Training | Online Inference |
|---|---|---|
| **Thời điểm chạy** | Một lần, trước khi deploy | Mỗi frame (33ms/lần) |
| **Tài nguyên** | CPU/RAM tùy ý, có thể mất vài phút | Phải xong trong < 5ms |
| **Dữ liệu đầu vào** | `final_train.csv` (tĩnh) | Frame camera (thời gian thực) |
| **Mô-đun thực hiện** | `gesture_model_battle.py` | `spell_recognizer.py` |
| **Kết quả** | `best_spell_model.pkl` | Tên phép thuật + confidence% |

Sự tách biệt này cho phép **cải tiến mô hình độc lập với game**: thêm dữ liệu mới, thử thuật toán khác, tái huấn luyện — tất cả đều không ảnh hưởng đến code game, chỉ cần thay thế file `.pkl` là hoàn tất.

---

## Tóm tắt luồng toàn bộ Module Training

```
gesture_model_battle.py
│
├── load_and_split_data()
│     └── final_train.csv → X (84D), y (10 lớp), Stratified 80/20
│
├── train_models()
│     ├── Random Forest  (n_estimators=100, n_jobs=-1)
│     ├── SVM RBF        (kernel='rbf', probability=True)
│     ├── KNN            (n_neighbors=5)
│     └── MLP            (hidden=64+32, early_stopping)
│
├── evaluate_models()
│     └── accuracy, F1-weighted, inference_time (100 lần đo)
│
├── print_comparison_table()
│     └── Balanced Score = 0.7×accuracy + 0.3×speed
│            → WINNER: SVM RBF (100%, 0.915ms, score=1.0000)
│
├── save_best_model()
│     └── joblib.dump(svm_model, "models/best_spell_model.pkl")
│
└── save_model_statistics()
      └── "models/model_statistics.md" (báo cáo tự động)
```
