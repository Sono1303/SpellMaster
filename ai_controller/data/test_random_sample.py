import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import random

# Load data
data_file = Path(__file__).parent / "final_train.csv"

print("[+] Loading data...")
df = pd.read_csv(data_file)

# Get unique labels
labels = sorted(df['Label'].unique())
print(f"[+] Available labels: {', '.join(labels)}")
print()

# User selects label
print("[*] Select gesture label:")
for idx, label in enumerate(labels):
    count = len(df[df['Label'] == label])
    print(f"  {idx}: {label} ({count} samples)")
label_choice = int(input(f"[?] Enter label index (0-{len(labels)-1}): "))
selected_label = labels[label_choice]
print()

# Filter by label
label_data = df[df['Label'] == selected_label].reset_index(drop=True)
print(f"[+] Found {len(label_data)} samples for {selected_label}")

# User selects sample
print(f"[*] Select sample (0-{len(label_data)-1}) or -1 for random:")
sample_choice = int(input("[?] Enter sample index: "))
if sample_choice == -1:
    sample_idx = random.randint(0, len(label_data)-1)
    print(f"[+] Randomly selected sample {sample_idx}")
else:
    sample_idx = sample_choice
random_sample = label_data.iloc[sample_idx]
print(f"[+] Using sample {sample_idx}")
print()

# Extract coordinates (skip Label column)
coords = random_sample.drop('Label').values

# Split into left and right hand
left_hand = coords[:42].reshape(21, 2)
right_hand = coords[42:84].reshape(21, 2)

print(f"[+] Left hand coords shape: {left_hand.shape}")
print(f"[+] Right hand coords shape: {right_hand.shape}")

# Hand skeleton connections
skeleton_connections = [
    [0, 1, 2, 3, 4],      # Thumb
    [0, 5, 6, 7, 8],      # Index finger
    [0, 9, 10, 11, 12],   # Middle finger
    [0, 13, 14, 15, 16],  # Ring finger
    [0, 17, 18, 19, 20],  # Pinky finger
    [0, 5, 9, 13, 17, 0]  # Palm
]

# Create figure with single large subplot
fig, ax = plt.subplots(1, 1, figsize=(12, 12))

ax.set_xlim(-4, 4)
ax.set_ylim(-4, 4)
ax.set_aspect('equal')
ax.invert_yaxis()
ax.grid(True, alpha=0.4, linestyle='--', linewidth=0.5)
ax.set_xlabel('X Coordinate', fontsize=13, fontweight='bold')
ax.set_ylabel('Y Coordinate', fontsize=13, fontweight='bold')
ax.set_title(f'{selected_label} - Both Hands Overlay', fontsize=15, fontweight='bold')

# Plot LEFT hand (Red circles)
ax.scatter(left_hand[:, 0], left_hand[:, 1], c='#FF0000', s=200, alpha=0.9, 
          edgecolors='black', linewidth=2, marker='o', label='Left Hand', zorder=3)

# Plot LEFT hand skeleton lines
for connection in skeleton_connections:
    line_coords = left_hand[connection]
    ax.plot(line_coords[:, 0], line_coords[:, 1], 
           color='#FF0000', linewidth=3, alpha=0.7, zorder=2)

# Plot RIGHT hand (Blue squares)
ax.scatter(right_hand[:, 0], right_hand[:, 1], c='#0066FF', s=200, alpha=0.9, 
          edgecolors='black', linewidth=2, marker='s', label='Right Hand', zorder=3)

# Plot RIGHT hand skeleton lines
for connection in skeleton_connections:
    line_coords = right_hand[connection]
    ax.plot(line_coords[:, 0], line_coords[:, 1], 
           color='#0066FF', linewidth=3, alpha=0.7, zorder=2)

# Add landmark indices for reference
for i in range(21):
    # Left hand labels
    ax.text(left_hand[i, 0], left_hand[i, 1] - 0.08, str(i), 
           fontsize=8, ha='center', color='#FF0000', fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='#FF0000'))
    
    # Right hand labels
    ax.text(right_hand[i, 0], right_hand[i, 1] + 0.08, str(i), 
           fontsize=8, ha='center', color='#0066FF', fontweight='bold',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='#0066FF'))

ax.legend(fontsize=13, loc='upper right', framealpha=0.9, edgecolor='black', fancybox=True)

fig.suptitle(f'Random Sample Visualization - {selected_label} (Both Hands)', 
            fontsize=16, fontweight='bold', y=0.98)

plt.tight_layout()
plt.savefig(Path(__file__).parent / "plots" / "random_sample_test.png", dpi=300, bbox_inches='tight')
print(f"[+] Saved to plots/random_sample_test.png")

plt.show()
