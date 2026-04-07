#!/usr/bin/env python3
"""
Compare normalized vs raw gesture data from compare mode output.

Analyzes differences between normalized and raw coordinates to validate
the normalization transformations.

Usage:
    python compare_normalize_data.py <gesture_label> <recording_number>
    
Example:
    python compare_normalize_data.py Tiger 1
    
Output:
    - Statistical comparison (mean, std, min, max)
    - Per-frame differences
    - Coordinate range analysis
    - Normalization validation report
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

def load_csv_files(gesture_label, recording_num):
    """Load both normalized and raw CSV files."""
    base_path = Path(__file__).parent / "compare" / "normalize_data" / gesture_label
    
    norm_file = base_path / f"normalized_{recording_num}.csv"
    raw_file = base_path / f"raw_{recording_num}.csv"
    
    if not norm_file.exists():
        print(f"❌ File not found: {norm_file}")
        return None, None
    if not raw_file.exists():
        print(f"❌ File not found: {raw_file}")
        return None, None
    
    df_norm = pd.read_csv(norm_file)
    df_raw = pd.read_csv(raw_file)
    
    return df_norm, df_raw

def analyze_coordinate_differences(df_norm, df_raw):
    """Analyze differences between normalized and raw coordinates."""
    
    # Get coordinate columns (exclude Label)
    coord_cols = [col for col in df_norm.columns if col != "Label"]
    
    print("\n" + "="*80)
    print("COORDINATE ANALYSIS")
    print("="*80)
    
    # 1. Range Analysis
    print("\n[1] COORDINATE RANGES")
    print("-" * 80)
    print(f"{'Metric':<20} {'Normalized':<20} {'Raw':<20}")
    print("-" * 80)
    
    norm_vals = df_norm[coord_cols].values.flatten()
    raw_vals = df_raw[coord_cols].values.flatten()
    
    metrics = {
        "Mean": (np.mean(norm_vals), np.mean(raw_vals)),
        "Std Dev": (np.std(norm_vals), np.std(raw_vals)),
        "Min": (np.min(norm_vals), np.min(raw_vals)),
        "Max": (np.max(norm_vals), np.max(raw_vals)),
        "Range": (np.max(norm_vals) - np.min(norm_vals), 
                 np.max(raw_vals) - np.min(raw_vals)),
    }
    
    for metric, (norm_val, raw_val) in metrics.items():
        print(f"{metric:<20} {norm_val:>19.4f} {raw_val:>19.4f}")
    
    # 2. Left Hand Analysis
    print("\n[2] LEFT HAND COORDINATES (should be relative to wrist)")
    print("-" * 80)
    left_cols = [col for col in coord_cols if col.endswith("_L")]
    
    # First landmark (wrist) should always be (0, 0) in normalized
    wrist_norm = df_norm[[col for col in left_cols if col.startswith("x1") or col.startswith("y1")]].iloc[0].values
    wrist_raw = df_raw[[col for col in left_cols if col.startswith("x1") or col.startswith("y1")]].iloc[0].values
    
    print(f"Left wrist (first frame):")
    print(f"  Normalized: ({wrist_norm[0]:.4f}, {wrist_norm[1]:.4f}) [should be ≈ (0, 0)]")
    print(f"  Raw:        ({wrist_raw[0]:.4f}, {wrist_raw[1]:.4f}) [varies with position]")
    
    # 3. Right Hand Analysis (should also use left wrist as origin)
    print("\n[3] RIGHT HAND COORDINATES (should be relative to LEFT wrist)")
    print("-" * 80)
    right_cols = [col for col in coord_cols if col.endswith("_R")]
    
    right_norm_vals = df_norm[right_cols].values.flatten()
    right_raw_vals = df_raw[right_cols].values.flatten()
    
    print(f"Right hand value ranges:")
    print(f"  Normalized - Min: {np.min(right_norm_vals):>8.4f}, Max: {np.max(right_norm_vals):>8.4f}")
    print(f"  Raw         - Min: {np.min(right_raw_vals):>8.4f}, Max: {np.max(right_raw_vals):>8.4f}")
    
    # 4. Hand-to-hand Distance
    print("\n[4] HAND-TO-HAND DISTANCE ANALYSIS")
    print("-" * 80)
    
    left_wrist_norm = df_norm[["x1_L", "y1_L"]].values  # Should all be (0, 0)
    right_wrist_norm = df_norm[["x1_R", "y1_R"]].values  # Distance from left wrist
    
    left_wrist_raw = df_raw[["x1_L", "y1_L"]].values
    right_wrist_raw = df_raw[["x1_R", "y1_R"]].values
    
    # Distance between wrists
    dist_norm = np.sqrt(np.sum((right_wrist_norm - left_wrist_norm)**2, axis=1))
    dist_raw = np.sqrt(np.sum((right_wrist_raw - left_wrist_raw)**2, axis=1))
    
    print(f"Wrist-to-wrist distance (all frames):")
    print(f"  Normalized - Mean: {np.mean(dist_norm):.4f}, Std: {np.std(dist_norm):.4f}")
    print(f"  Raw         - Mean: {np.mean(dist_raw):.4f}, Std: {np.std(dist_raw):.4f}")
    print(f"  💡 Normalized std should be LOW (consistent hand geometry)")
    print(f"  💡 Raw std could be HIGH (varies with hand position)")
    
    # 5. Normalization Validation
    print("\n[5] NORMALIZATION VALIDATION")
    print("-" * 80)
    
    # Check if left wrist is always (0, 0) in normalized
    wrist_x_vals = df_norm["x1_L"].values
    wrist_y_vals = df_norm["y1_L"].values
    
    all_zero = np.allclose(wrist_x_vals, 0.0) and np.allclose(wrist_y_vals, 0.0)
    
    if all_zero:
        print("✅ Left wrist always at (0, 0) - Translation working correctly")
    else:
        print("❌ Left wrist NOT at (0, 0) - Translation may have failed")
        print(f"   X range: {np.min(wrist_x_vals):.6f} to {np.max(wrist_x_vals):.6f}")
        print(f"   Y range: {np.min(wrist_y_vals):.6f} to {np.max(wrist_y_vals):.6f}")
    
    # Check if normalized values are in smaller range (due to scaling)
    norm_range = np.max(norm_vals) - np.min(norm_vals)
    raw_range = np.max(raw_vals) - np.min(raw_vals)
    
    print(f"\nCoordinate range sizes:")
    print(f"  Normalized range: {norm_range:.4f}")
    print(f"  Raw range:        {raw_range:.4f}")
    
    if norm_range < raw_range:
        print(f"  ✅ Scaling working correctly (normalized is compressed by factor ~{raw_range/norm_range:.1f}x)")
    else:
        print(f"  ⚠️  Scaling may not be applied (ranges are similar)")
    
    return metrics

def sample_frame_comparison(df_norm, df_raw, frame_num=0):
    """Show detailed comparison for a specific frame."""
    print("\n" + "="*80)
    print(f"SAMPLE FRAME COMPARISON (Frame {frame_num})")
    print("="*80)
    
    norm_row = df_norm.iloc[frame_num]
    raw_row = df_raw.iloc[frame_num]
    
    print(f"\nLabel: {norm_row['Label']}")
    print("\n" + "-"*80)
    print(f"{'Landmark':<15} {'Normalized':<25} {'Raw':<25} {'Difference':<20}")
    print("-"*80)
    
    coord_cols = [col for col in df_norm.columns if col != "Label"]
    
    for i in range(0, len(coord_cols), 2):
        x_col = coord_cols[i]
        y_col = coord_cols[i+1]
        
        norm_x = norm_row[x_col]
        norm_y = norm_row[y_col]
        raw_x = raw_row[x_col]
        raw_y = raw_row[y_col]
        
        diff_x = abs(norm_x - raw_x)
        diff_y = abs(norm_y - raw_y)
        
        landmark_name = x_col.replace("x", "").replace("_L", "L").replace("_R", "R")
        
        norm_str = f"({norm_x:>7.4f}, {norm_y:>7.4f})"
        raw_str = f"({raw_x:>7.4f}, {raw_y:>7.4f})"
        diff_str = f"({diff_x:>7.4f}, {diff_y:>7.4f})"
        
        print(f"{landmark_name:<15} {norm_str:<25} {raw_str:<25} {diff_str:<20}")
    
    return norm_row, raw_row

def print_summary():
    """Print normalization technique summary."""
    print("\n" + "="*80)
    print("NORMALIZATION TECHNIQUES VALIDATION")
    print("="*80)
    print("""
1. GLOBAL COORDINATE REFERENCE
   ✓ Left wrist (Landmark 0) serves as origin (0, 0)
   ✓ All 42 landmarks relative to this single point
   ✓ Preserves hand-to-hand spatial relationships

2. TRANSLATION
   ✓ Formula: rel_x = landmark_x - left_wrist_x
   ✓ Effect: Left wrist always at (0, 0) in normalized data
   ✓ Validation: Check if x1_L and y1_L are all 0.0

3. SCALING BY PALM SIZE
   ✓ Formula: norm = rel / palm_size (where palm_size = wrist→mcp distance)
   ✓ Effect: Normalized values compressed into smaller range
   ✓ Validation: Normalized range << Raw range

4. SMOOTHING (EMA)  
   ✓ Formula: smooth = 0.3 × current + 0.7 × previous
   ✓ Effect: Reduces jitter (lower std in stable frames)
   ✓ Applied to both normalized and raw data

5. STABILITY
   ✓ Only frames with exactly 2 hands accepted
   ✓ Hand count stability validated (no flickering)
   ✓ Left hand must always be present (reference required)
    """)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare_normalize_data.py <gesture_label> [recording_number]")
        print("Example: python compare_normalize_data.py Tiger 1")
        sys.exit(1)
    
    gesture_label = sys.argv[1]
    recording_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"\n📊 Comparing Normalized vs Raw Data")
    print(f"   Gesture: {gesture_label}")
    print(f"   Recording: #{recording_num}\n")
    
    df_norm, df_raw = load_csv_files(gesture_label, recording_num)
    
    if df_norm is None or df_raw is None:
        sys.exit(1)
    
    print(f"✅ Loaded {len(df_norm)} frames from both files")
    
    # Perform analysis
    metrics = analyze_coordinate_differences(df_norm, df_raw)
    
    # Show sample frame
    if len(df_norm) > 0:
        sample_frame_comparison(df_norm, df_raw, frame_num=0)
    
    # Print summary
    print_summary()
    
    print("\n" + "="*80)
    print("✅ Analysis complete! Check output above to validate normalization.")
    print("="*80)
