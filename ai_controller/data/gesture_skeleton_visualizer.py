import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

class GestureSkeletonVisualizer:
    def __init__(self, data_file="final_train.csv"):
        """
        Initialize the gesture skeleton visualizer.
        
        Args:
            data_file: Path to final_train.csv
        """
        self.data_dir = Path(__file__).parent
        self.data_file = self.data_dir / data_file
        self.df = None
        self.selected_labels = []
        self.mean_gestures = {}
        
        # Hand skeleton connections (landmark indices)
        self.skeleton_connections = [
            [0, 1, 2, 3, 4],      # Thumb
            [0, 5, 6, 7, 8],      # Index finger
            [0, 9, 10, 11, 12],   # Middle finger
            [0, 13, 14, 15, 16],  # Ring finger
            [0, 17, 18, 19, 20],  # Pinky finger
            [0, 5, 9, 13, 17, 0]  # Palm
        ]
        
        # Color palette for different gestures (high contrast)
        self.colors = [
            '#FF0000',  # Red
            '#0066FF',  # Blue
            '#00CC00',  # Green
            '#FF9900',  # Orange
            '#FF00FF',  # Magenta
            '#00FFFF',  # Cyan
            '#FFCC00',  # Yellow
            '#FF3366',  # Pink
            '#33FF00',  # Lime
            '#9933FF'   # Purple
        ]
    
    def load_data(self):
        """Load data from final_train.csv."""
        print("\n[+] Loading data from final_train.csv...")
        
        try:
            self.df = pd.read_csv(self.data_file)
            print(f"    Total samples: {len(self.df)}")
            
            # Get available labels
            available_labels = self.df['Label'].unique()
            print(f"    Available labels: {', '.join(sorted(available_labels))}")
            
            return True
        
        except FileNotFoundError:
            print(f"[ERROR] File not found: {self.data_file}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load data: {str(e)}")
            return False
    
    def get_user_input(self):
        """Get gesture labels from user input."""
        print("\n[*] Enter gesture labels to compare (comma-separated):")
        print("    Example: Tiger, Dragon, Fire")
        
        user_input = input("    Labels: ").strip()
        
        if not user_input:
            print("[ERROR] No labels entered")
            return False
        
        # Parse input
        labels = [label.strip() for label in user_input.split(',')]
        
        # Validate labels
        available_labels = self.df['Label'].unique()
        invalid_labels = [l for l in labels if l not in available_labels]
        
        if invalid_labels:
            print(f"[ERROR] Invalid labels: {', '.join(invalid_labels)}")
            return False
        
        self.selected_labels = labels
        print(f"[+] Selected labels: {', '.join(self.selected_labels)}")
        
        return True
    
    def extract_coordinates(self, gesture_data):
        """Extract left and right hand coordinates from gesture data.
        
        Args:
            gesture_data: Row from dataframe with 85 columns
        
        Returns:
            Tuple of (left_hand, right_hand) coordinates
        """
        # Drop label column and convert to array
        coords = gesture_data.drop('Label').values
        
        # Left hand: 42 coordinates (21 landmarks x 2)
        left_hand = coords[:42].reshape(21, 2)
        
        # Right hand: 42 coordinates (21 landmarks x 2)
        right_hand = coords[42:84].reshape(21, 2)
        
        return left_hand, right_hand
    
    def calculate_mean_gesture(self):
        """Calculate mean gesture skeleton for each selected label."""
        print("\n[*] Calculating mean gesture skeletons...")
        
        for label in self.selected_labels:
            # Filter data by label
            label_data = self.df[self.df['Label'] == label]
            
            if len(label_data) == 0:
                print(f"    [WARNING] No data found for {label}")
                continue
            
            # Extract all coordinates for this label
            all_left_hands = []
            all_right_hands = []
            
            for _, row in label_data.iterrows():
                left, right = self.extract_coordinates(row)
                all_left_hands.append(left)
                all_right_hands.append(right)
            
            # Calculate mean
            mean_left = np.mean(all_left_hands, axis=0)
            mean_right = np.mean(all_right_hands, axis=0)
            
            self.mean_gestures[label] = {
                'left': mean_left,
                'right': mean_right,
                'count': len(label_data)
            }
            
            print(f"    [+] {label}: {len(label_data)} samples processed")
    
    def plot_skeleton(self, ax, hand_data, hand_name, title_suffix=""):
        """Plot skeleton on given axis.
        
        Args:
            ax: Matplotlib axis
            hand_data: Dict of label -> hand coordinates
            hand_name: 'Left' or 'Right'
            title_suffix: Additional title text
        """
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.invert_yaxis()  # Invert Y axis to match hand orientation
        
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlabel('X Coordinate', fontsize=10, fontweight='bold')
        ax.set_ylabel('Y Coordinate', fontsize=10, fontweight='bold')
        
        title = f'{hand_name} Hand Skeleton{title_suffix}'
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Plot each gesture
        for idx, (label, gesture_info) in enumerate(hand_data.items()):
            if hand_name == 'Left':
                coords = gesture_info['left']
                marker_style = 'o'
            else:
                coords = gesture_info['right']
                marker_style = 's'
            
            color = self.colors[idx % len(self.colors)]
            
            # Plot landmarks (scatter)
            ax.scatter(coords[:, 0], coords[:, 1], 
                      c=color, s=120, alpha=0.8, 
                      label=label, edgecolors='black', linewidth=1.5,
                      marker=marker_style)
            
            # Plot skeleton lines
            for connection in self.skeleton_connections:
                # Get coordinates for connected landmarks
                line_coords = coords[connection]
                
                # Draw lines
                ax.plot(line_coords[:, 0], line_coords[:, 1], 
                       color=color, linewidth=2.5, alpha=0.8)
    
    def visualize(self):
        """Create visualization comparing gesture skeletons."""
        print("\n[*] Creating visualization...")
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        
        # Title for the whole figure
        labels_str = ', '.join(self.selected_labels)
        fig.suptitle(f'Gesture Structure Comparison: {labels_str}', 
                    fontsize=15, fontweight='bold', y=0.98)
        
        # Plot left hand
        self.plot_skeleton(axes[0], self.mean_gestures, 'Left', ' (Solid Circles)')
        
        # Plot right hand
        self.plot_skeleton(axes[1], self.mean_gestures, 'Right', ' (Hollow Squares)')
        
        # Create combined legend with better positioning
        handles_left, labels_left = axes[0].get_legend_handles_labels()
        
        # Add legend with gesture names and hand indicators
        legend_text = []
        for label in labels_left:
            legend_text.append(f'{label} (Left: O, Right: [])')
        
        fig.legend(handles_left, legend_text, loc='lower center', 
                  ncol=min(len(self.selected_labels), 5),
                  fontsize=11, bbox_to_anchor=(0.5, -0.08), 
                  frameon=True, fancybox=True, shadow=True, 
                  title='Gestures (Left Hand: Circle, Right Hand: Square)')
        
        plt.tight_layout(rect=[0, 0.08, 1, 0.96])
        
        # Save figure
        output_dir = self.data_dir / "plots"
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / "gesture_skeleton_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"[+] Saved visualization to plots/gesture_skeleton_comparison.png")
        
        return fig
    
    def print_statistics(self):
        """Print statistics for selected gestures."""
        print("\n" + "=" * 70)
        print("GESTURE SKELETON ANALYSIS")
        print("=" * 70)
        
        print("\nStatistics for selected gestures:\n")
        print(f"{'Gesture Label':<20} {'Sample Count':<15} {'Left Hand':<15} {'Right Hand':<15}")
        print("-" * 70)
        
        for label in self.selected_labels:
            if label in self.mean_gestures:
                info = self.mean_gestures[label]
                left_hand = info['left']
                right_hand = info['right']
                
                # Calculate gesture "size" (variance)
                left_size = np.std(left_hand)
                right_size = np.std(right_hand)
                
                print(f"{label:<20} {info['count']:<15} {left_size:<15.4f} {right_size:<15.4f}")
        
        print("\n" + "=" * 70)
    
    def run(self):
        """Main execution function."""
        print("\n" + "=" * 70)
        print("GESTURE SKELETON VISUALIZER")
        print("=" * 70)
        
        # Step 1: Load data
        if not self.load_data():
            return False
        
        # Step 2: Get user input
        if not self.get_user_input():
            return False
        
        # Step 3: Calculate mean gestures
        self.calculate_mean_gesture()
        
        if not self.mean_gestures:
            print("[ERROR] Failed to calculate mean gestures")
            return False
        
        # Step 4: Print statistics
        self.print_statistics()
        
        # Step 5: Create visualization
        self.visualize()
        
        print("\n[+] Visualization complete!")
        print("=" * 70 + "\n")
        
        return True


if __name__ == "__main__":
    visualizer = GestureSkeletonVisualizer(data_file="final_train.csv")
    success = visualizer.run()
    
    if success:
        plt.show()
