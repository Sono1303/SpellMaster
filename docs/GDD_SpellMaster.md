**GDD \- Ignite: Spell Master**  
**1\. Concept**

* **Tên game:** Ignite: Spell Master  
* **Thể loại:** Stationary FPS / Arcade Defense  
* **Nền tảng:** PC (Sử dụng Webcam/Camera)  
* **Góc nhìn:** First-person (Góc nhìn thứ nhất)  
* **Phong cách:** High Fantasy / Magic  
* **Ý tưởng:** Người chơi sử dụng một chiếc đũa phép thật (hoặc ngón tay) tương tác qua Camera để điều khiển nhân vật Đại Pháp Sư. Người chơi đứng yên tại vị trí thủ thành, thực hiện các động tác vung tay để tấn công và xoay tay để nạp năng lượng.  
* **Gameplay:** Người chơi phải đối mặt với các đợt tấn công của quái vật từ xa lao đến, sử dụng kỹ năng chính xác và quản lý năng lượng (Mana) để không để kẻ địch chạm vào màn hình.

**2\. Game Story**

* **Cốt truyện:** Cánh cổng Hư Không (The Void Gate) đã bị phá vỡ. Những sinh vật hắc ám cổ đại đang tràn vào thế giới thực tại. Bạn là người gác cổng cuối cùng của Hội Đồng Pháp Thuật.  
* **Tại tháp canh:** Bạn đứng trên đỉnh tháp, sử dụng quyền năng của cây đũa phép cổ đại để đẩy lùi từng đợt sóng quái vật (Waves) đang cố gắng phá hủy phong ấn.  
* **Bối cảnh:** "The Last Bastion" – Pháo đài cuối cùng, bầu trời rực lửa và mặt đất đầy rẫy quái vật.  
* **Nhân vật:**  
  * The Archmage (Người chơi): Pháp sư quyền năng, người duy nhất có thể điều khiển đũa phép thần.  
  * The Void Legion (Kẻ địch): Đội quân quái vật gồm Goblin, Orc, Rồng và Bóng ma.

**3\. Core**

* **Mục tiêu:**  
  * Sống sót qua càng nhiều đợt quái (Wave) càng tốt để đạt điểm cao trên bảng xếp hạng.  
  * Bảo vệ cổng thành (HP) không bị về 0\.  
  * Thu thập Tinh thể năng lượng (Mana Crystal) và Vàng để nâng cấp sức mạnh phép thuật.  
* **Trong đó:**  
  * Mana (Năng lượng) → Dùng để bắn đạn. Hết Mana phải thực hiện thao tác "Xoay" để nạp.  
  * Vàng (Gold) → Mua các phép thuật mới hoặc nâng cấp sát thương.  
  * Vật phẩm (Artifacts) → Power-ups buff sức mạnh tạm thời trong trận đấu.

**Các vật phẩm & Kỹ năng bổ trợ**

| Vật phẩm / Kỹ năng | Tác dụng | Thời gian hiệu lực |
| :---- | :---- | :---- |
| **Mana Potion** | Hồi đầy thanh Mana ngay lập tức mà không cần xoay tay. | Tức thì |
| **Frost Nova** | Đóng băng toàn bộ kẻ địch trên màn hình, chặn di chuyển. | 5s |
| **Inferno Blast** | Tạo vụ nổ lớn tiêu diệt quái vật trong bán kính rộng. | Tức thì |
| **Time Warp** | Làm chậm thời gian (Slow motion) để người chơi dễ ngắm bắn. | 7s |
| **Double Damage** | Nhân đôi sát thương của đạn phép bắn ra. | 10s |
| **Auto-Turret** | Triệu hồi một tinh linh tự động bắn quái vật gần nhất. | 15s |
| **Guardian Shield** | Tạo lá chắn chặn 1 đòn tấn công bất kỳ từ quái vật xa. | Đến khi vỡ |

**4\. Core Loop**

1. **Defend/Combat:** Người chơi vung tay tiêu diệt quái vật trong Wave.  
2. **Collect:** Thu thập Vàng và Điểm kinh nghiệm sau mỗi Wave.  
3. **Upgrade:** Sử dụng Vàng để nâng cấp tốc độ đạn, sức chứa Mana hoặc mua phép mới.  
4. (Quay lại bước 1 với độ khó cao hơn)

**5\. Cơ chế tính điểm**  
**Điểm thưởng Combo Hit**

| Combo count | Bonus |
| :---- | :---- |
| 1-4 hits | \+0 điểm |
| 5-9 hits | \+10 điểm/hit |
| 10-19 hits | \+20 điểm/hit |
| 20+ hits | \+50 điểm/hit (Trạng thái "On Fire") |

*Giải thích: Bắn trúng kẻ địch liên tiếp mà không bị trượt (miss) hoặc bị dính sát thương sẽ tăng chuỗi Combo.*  
**Tính điểm tổng**  
**Công thức:** Points\_event \= (BaseScore \+ WeakspotBonus \+ ComboBonus) × ActiveMultiplier  
**6\. Cơ chế điều khiển (Quan trọng)**

| Hành động | Thực hiện (Thao tác tay qua Camera) |
| :---- | :---- |
| **Tấn công (Bắn thường)** | **Vung mạnh** đũa/tay về phía màn hình (theo hướng kẻ địch). |
| **Nạp đạn (Hồi Mana)** | **Xoay tròn** đũa/tay liên tục (vẽ hình vòng tròn). |
| **Tấn công đặc biệt** | Xoay nạp đầy Mana \+ Xoay thêm 3 vòng rồi Vung mạnh. |
| **Ngắm (Aim)** | Di chuyển tay để điều khiển tâm ngắm trên màn hình. |
| **Kích hoạt Vật phẩm** | Di chuyển tâm ngắm vào biểu tượng vật phẩm và giữ nguyên 1s. |
| **Hồi sinh** | Giơ hai tay lên trời (Pose: Surrender) để kích hoạt hồi sinh. |

**7\. Nhiệm vụ và thử thách**  
Hoàn thành 3 nhiệm vụ hàng ngày để mở Rương Kho Báu.

| Loại nhiệm vụ | Mô tả |
| :---- | :---- |
| **Diệt quái** | Tiêu diệt số lượng quái vật nhất định (Ví dụ: 50 Goblin). |
| **Kỹ năng xoay** | Nạp đầy thanh Mana 20 lần trong một ván chơi. |
| **Sinh tồn** | Sống sót qua Wave 10 mà không mất máu. |
| **Thiện xạ** | Đạt chuỗi Combo 30 hits liên tiếp. |

