import cv2
import mediapipe as mp
import math
from collections import deque
from datetime import datetime
import socket
import json

# Khởi tạo thư viện
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=2, 
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)

# Tạo cửa sổ có thể resize
cv2.namedWindow("Ignite: Spell Master - Gesture Recognition", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Ignite: Spell Master - Gesture Recognition", 800, 600)

# ==================== UDP SOCKET CONFIG ====================
"""
UDP Socket Setup để gửi data tới Unity:

1. Server (Python - AI Controller):
   - Gửi gesture/combo data qua UDP
   - Địa chỉ: localhost (127.0.0.1) hoặc IP máy
   - Port: 5005 (có thể thay đổi)

2. Client (Unity):
   - Nhận data UDP
   - Script C# để parse dữ liệu JSON

Message Format:
{
    "gesture": "Peace",
    "combo": "Spell_Peace+Peace",
    "timestamp": 1234567890
}
"""

class UDPSocket:
    """Quản lý UDP Socket để gửi data tới Unity"""
    def __init__(self, host="127.0.0.1", port=5005):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"✓ UDP Socket initialized: {host}:{port}")
    
    def send_gesture(self, gesture_name, combo_name=None):
        """Gửi gesture/combo data tới Unity"""
        try:
            data = {
                "gesture": gesture_name,
                "combo": combo_name,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
            message = json.dumps(data)
            self.socket.sendto(message.encode(), (self.host, self.port))
            print(f"→ Sent: {message}")
        except Exception as e:
            print(f"✗ Error sending UDP: {e}")
    
    def close(self):
        """Đóng socket"""
        self.socket.close()

# Khởi tạo UDP socket
udp_socket = UDPSocket(host="127.0.0.1", port=5005)

# ==================== GESTURE HISTORY TRACKING ====================
class GestureTracker:
    """Theo dõi lịch sử gesture để nhận diện combo"""
    def __init__(self, max_history=5, timeout_ms=500):
        self.history = deque(maxlen=max_history)
        self.timeout_ms = timeout_ms
        self.last_gesture = None
        self.last_time = None
    
    def add_gesture(self, gesture_name):
        """Thêm gesture mới vào history"""
        current_time = datetime.now()
        
        # Nếu gesture khác nhau hoặc timeout, thêm vào history
        if gesture_name != self.last_gesture or \
           (self.last_time and (current_time - self.last_time).total_seconds() * 1000 > self.timeout_ms):
            self.history.append(gesture_name)
            self.last_gesture = gesture_name
            self.last_time = current_time
    
    def get_history(self):
        """Lấy danh sách gesture gần nhất"""
        return list(self.history)
    
    def get_last_combo(self, combo_length=3):
        """Lấy combo gần nhất (ví dụ: Peace + Rock + Love)"""
        if len(self.history) >= combo_length:
            return '+'.join(list(self.history)[-combo_length:])
        return None

gesture_tracker = GestureTracker(max_history=5, timeout_ms=300)

# ==================== DEBUG MODE ====================
DEBUG_MODE = True  # Đặt True để xem chi tiết trạng thái ngón tay

def euclidean_distance(p1, p2):
    """Tính khoảng cách Euclid giữa hai điểm"""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

# ==================== LANDMARK INDICES REFERENCE ====================
"""
MediaPipe Hand Landmarks (21 landmarks per hand):
0  - Wrist (cổ tay)
1-4   - Thumb: 1=CMC, 2=MCP, 3=PIP, 4=TIP
5-8   - Index: 5=MCP, 6=PIP, 7=DIP, 8=TIP
9-12  - Middle: 9=MCP, 10=PIP, 11=DIP, 12=TIP
13-16 - Ring: 13=MCP, 14=PIP, 15=DIP, 16=TIP
17-20 - Pinky: 17=MCP, 18=PIP, 19=DIP, 20=TIP

Landmarks cần nhất để nhận diện:
- Thumb: 3 (PIP), 4 (TIP)
- Index: 6 (PIP), 8 (TIP)
- Middle: 10 (PIP), 12 (TIP)
- Ring: 14 (PIP), 16 (TIP)
- Pinky: 18 (PIP), 20 (TIP)
"""

def get_finger_status(hand_landmarks):
    """
    Trả về trạng thái của 5 ngón tay (opened/closed)
    Sử dụng khoảng cách giữa Tip và PIP để xác định mở/đóng
    Returns: [thumb, index, middle, ring, pinky]
    
    CƠ CHẾ:
    - Tip: đầu ngón tay (điểm xa nhất)
    - PIP: khớp giữa 
    - MCP: khớp gốc
    
    Logic:
    - Ngón ĐÓNG: tip gần PIP (distance nhỏ)
    - Ngón MỞ: tip xa PIP (distance lớn)
    
    Threshold: Nếu tip_to_pip > 30% của pip_to_mcp thì xem là MỞ
    """
    # Danh sách (Tip, PIP, MCP) cho mỗi ngón: Thumb, Index, Middle, Ring, Pinky
    finger_triplets = [
        (4, 3, 2),      # Thumb
        (8, 6, 5),      # Index
        (12, 10, 9),    # Middle
        (16, 14, 13),   # Ring
        (20, 18, 17)    # Pinky
    ]
    
    status = []
    
    for tip_idx, pip_idx, mcp_idx in finger_triplets:
        tip = hand_landmarks.landmark[tip_idx]
        pip = hand_landmarks.landmark[pip_idx]
        mcp = hand_landmarks.landmark[mcp_idx]
        
        # Tính khoảng cách từ Tip đến PIP
        tip_to_pip_dist = euclidean_distance(tip, pip)
        
        # Tính khoảng cách từ PIP đến MCP
        pip_to_mcp_dist = euclidean_distance(pip, mcp)
        
        # Nếu ngón mở: tip sẽ xa PIP, distance > 30% của pip_to_mcp
        # Threshold thấp hơn để nhạy cảm hơn
        is_open = tip_to_pip_dist > (pip_to_mcp_dist * 0.3)
        
        status.append("O" if is_open else "C")  # O=Open, C=Closed
    
    return status

# ==================== CUSTOM GESTURE DETECTION ====================
"""
HƯỚNG DẪN TẠO GESTURE MỚI:

1. BƯỚC 1: Xác định pattern mong muốn
   - Dùng debug info để thấy finger status của gesture bạn muốn
   - Ví dụ: "T:C I:O M:O R:C P:C" = Peace sign

2. BƯỚC 2: Viết detection function
   Cách 1 - Kiểm tra finger status (đơn giản nhất):
   -------
   def detect_my_gesture(hand_landmarks):
       status = get_finger_status(hand_landmarks)
       # status = [Thumb, Index, Middle, Ring, Pinky]
       # Kiểm tra trạng thái mong muốn
       return status[0] == "C" and status[1] == "O"  # Thumb closed, Index open
   
   Cách 2 - Kiểm tra distance giữa các điểm:
   -----------
   def detect_my_gesture(hand_landmarks):
       thumb_tip = hand_landmarks.landmark[4]
       index_tip = hand_landmarks.landmark[8]
       distance = euclidean_distance(thumb_tip, index_tip)
       return distance < 0.08  # Nếu distance < 0.08 thì được xem là gesture này
   
   Cách 3 - Kết hợp cả hai:
   --------
   def detect_my_gesture(hand_landmarks):
       status = get_finger_status(hand_landmarks)
       thumb_tip = hand_landmarks.landmark[4]
       index_tip = hand_landmarks.landmark[8]
       distance = euclidean_distance(thumb_tip, index_tip)
       return (status[1] == "O" and status[2] == "O" and 
               distance > 0.1)  # Index + Middle open, thumb-index distance > 0.1

3. BƯỚC 3: Thêm vào detect_gesture() và combo detection
"""

def detect_gesture(hand_landmarks):
    """
    Phát hiện gesture hiện tại
    Thứ tự ưu tiên: gesture cụ thể trước, gesture tổng quát sau
    Returns: Tên gesture hoặc "Unknown"
    """
    # Thứ tự: gesture cụ thể → tổng quát
    if detect_ok_sign(hand_landmarks):
        return "OK"
    elif detect_peace_sign(hand_landmarks):
        return "Peace"
    elif detect_thumbs_up(hand_landmarks):
        return "ThumbsUp"
    elif detect_fist(hand_landmarks):
        return "Fist"
    elif detect_open_hand(hand_landmarks):
        return "Open"
    else:
        return "Unknown"

def detect_ok_sign(hand_landmarks):
    """OK sign (👌): Thumb + Index gần nhau, khác open"""
    thumb_tip = hand_landmarks.landmark[4]
    index_tip = hand_landmarks.landmark[8]
    distance = euclidean_distance(thumb_tip, index_tip)
    
    status = get_finger_status(hand_landmarks)
    # OK: Thumb + Index close (distance nhỏ), Middle/Ring/Pinky open
    return distance < 0.06 and status[2] == "O" and status[3] == "O" and status[4] == "O"

def detect_peace_sign(hand_landmarks):
    """Peace sign (✌): Index + Middle open, Ring + Pinky closed"""
    status = get_finger_status(hand_landmarks)
    # [Thumb, Index, Middle, Ring, Pinky]
    # Peace: Index open, Middle open, Ring closed, Pinky closed (Thumb không quan trọng)
    return status[1] == "O" and status[2] == "O" and status[3] == "C" and status[4] == "C"

def detect_thumbs_up(hand_landmarks):
    """Thumbs Up (👍): Thumb open, khác closed"""
    status = get_finger_status(hand_landmarks)
    # [Thumb, Index, Middle, Ring, Pinky]
    # Thumbs Up: Thumb open, Index/Middle/Ring/Pinky closed
    return status[0] == "O" and status[1] == "C" and status[2] == "C" and status[3] == "C" and status[4] == "C"

def detect_fist(hand_landmarks):
    """Fist (✊): Tất cả ngón đóng"""
    status = get_finger_status(hand_landmarks)
    # Tất cả 5 ngón đóng
    return all(s == "C" for s in status)

def detect_open_hand(hand_landmarks):
    """Open hand (✋): Tất cả ngón mở"""
    status = get_finger_status(hand_landmarks)
    # Tất cả 5 ngón mở
    return all(s == "O" for s in status)

def format_finger_status_display(status):
    """Format trạng thái ngón tay để hiển thị: [T I M R P] = [O C O C O]"""
    labels = ["T", "I", "M", "R", "P"]  # Thumb, Index, Middle, Ring, Pinky
    return " ".join([f"{label}:{s}" for label, s in zip(labels, status)])

# ==================== COMBO DETECTION ====================
def detect_combo(history):
    """
    Phát hiện combo từ lịch sử gesture
    Thêm combo rules của bạn ở đây
    """
    if len(history) < 2:
        return None
    
    # === THÊM CÁC COMBO CỦA BẠN TẠI ĐÂY ===
    # Ví dụ:
    if history[-2:] == ["Peace", "Peace"]:
        return "Spell_Peace+Peace"
    elif history[-2:] == ["ThumbsUp", "ThumbsUp"]:
        return "Spell_ThumbsUp+ThumbsUp"
    elif history[-2:] == ["Fist", "Open"]:
        return "Spell_Fist+Open"
    
    return None


# ==================== MAIN LOOP ====================

while cap.isOpened():
    success, img = cap.read()
    if not success: 
        break

    img = cv2.flip(img, 1)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    h, w, c = img.shape
    
    # Hiển thị thông tin trên màn hình
    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_lms, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Vẽ hand skeleton
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
            
            # Lấy thông tin bàn tay
            hand_label = handedness.classification[0].label
            confidence = handedness.classification[0].score
            
            # Phát hiện gesture
            gesture = detect_gesture(hand_lms)
            gesture_tracker.add_gesture(gesture)
            
            # Hiển thị gesture
            index_tip = hand_lms.landmark[8]
            cx, cy = int(index_tip.x * w), int(index_tip.y * h)
            
            # Chọn màu dựa trên gesture
            gesture_colors = {
                "Peace": (255, 100, 0),      # Cyan
                "Rock": (0, 0, 255),         # Red
                "OK": (0, 255, 255),         # Yellow
                "ThumbsUp": (0, 255, 0),     # Green
                "Love": (255, 0, 255),       # Magenta
                "Fist": (0, 0, 128),         # Dark Red
                "Open": (128, 128, 128),     # Gray
                "Unknown": (200, 200, 200)   # Light Gray
            }
            color = gesture_colors.get(gesture, (200, 200, 200))
            
            # Vẽ vòng tròn tại ngón trỏ
            cv2.circle(img, (cx, cy), 12, color, cv2.FILLED)
            
            # Hiển thị thông tin bàn tay
            status_y = cy - 40 if cy > 100 else cy + 100
            gesture_text = f"{hand_label}: {gesture}"
            cv2.putText(img, gesture_text, (cx - 80, status_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # DEBUG MODE: Hiển thị trạng thái ngón tay
            if DEBUG_MODE:
                finger_status = get_finger_status(hand_lms)
                status_display = format_finger_status_display(finger_status)
                debug_y = status_y + 30
                cv2.putText(img, f"Fingers: {status_display}", (cx - 100, debug_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    
    # Hiển thị gesture history
    history = gesture_tracker.get_history()
    history_text = " → ".join(history) if history else "No gestures"
    cv2.putText(img, f"History: {history_text}", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Phát hiện combo
    combo = detect_combo(history)
    if combo:
        cv2.putText(img, f"🔥 COMBO: {combo}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        print(f"⚡ {combo} TRIGGERED!")
        # Gửi combo tới Unity qua UDP
        udp_socket.send_gesture(history[-1] if history else "Unknown", combo)
    elif gesture != "Unknown":
        # Gửi từng gesture tới Unity
        udp_socket.send_gesture(gesture, None)

    cv2.imshow("Ignite: Spell Master - Gesture Recognition", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
udp_socket.close()
print("✓ UDP Socket closed")