import pandas as pd
import glob
import os
from pathlib import Path
from datetime import datetime

class GestureDataMerger:
    def __init__(self, input_dir="csv", output_filename="final_train.csv"):
        """
        Initialize the gesture data merger.
        
        Args:
            input_dir: Directory containing CSV files (relative to data folder)
            output_filename: Name of the output merged CSV file
        """
        self.data_dir = Path(__file__).parent
        self.input_dir = self.data_dir / input_dir
        self.output_file = self.data_dir / output_filename
        self.summary_file = self.data_dir / "merge_summary.md"
        
        # Statistics
        self.total_samples = 0
        self.label_counts = {}
        self.files_merged = 0
        self.skipped_files = 0
    
    def get_csv_files(self):
        """Get all CSV files from input directory."""
        if not self.input_dir.exists():
            print(f"Error: Input directory not found: {self.input_dir}")
            return []
        
        csv_files = sorted(list(self.input_dir.glob("*.csv")))
        
        if not csv_files:
            print(f"Warning: No CSV files found in {self.input_dir}")
            return []
        
        print(f"Found {len(csv_files)} CSV files in {self.input_dir}")
        return csv_files
    
    def validate_dataframe(self, df, filename):
        """
        Validate that dataframe has correct structure (85 columns).
        
        Args:
            df: DataFrame to validate
            filename: Name of the file being validated
        
        Returns:
            Valid dataframe or None if invalid
        """
        expected_columns = 85
        actual_columns = len(df.columns)
        
        if actual_columns != expected_columns:
            print(f"  Skipped {filename}: Expected {expected_columns} columns, got {actual_columns}")
            self.skipped_files += 1
            return None
        
        # Check if first column is Label
        if df.columns[0] != "Label":
            print(f"  Skipped {filename}: First column should be 'Label', got '{df.columns[0]}'")
            self.skipped_files += 1
            return None
        
        return df
    
    def has_both_hands(self, row):
        """
        Check if a row has valid data for BOTH hands (not all zeros for either hand).
        
        Args:
            row: DataFrame row
        
        Returns:
            True if both hands have data, False otherwise
        """
        # Columns 1-42: Left hand (x1_L, y1_L, ..., x21_L, y21_L)
        left_hand_cols = row.iloc[1:43].values
        
        # Columns 43-84: Right hand (x1_R, y1_R, ..., x21_R, y21_R)
        right_hand_cols = row.iloc[43:85].values
        
        # Check if both hands have at least some non-zero values
        left_has_data = (left_hand_cols != 0).any()
        right_has_data = (right_hand_cols != 0).any()
        
        return left_has_data and right_has_data
    
    def merge_csv_files(self):
        """
        Merge all CSV files into a single dataframe.
        
        Returns:
            Merged dataframe or None if no valid files found
        """
        csv_files = self.get_csv_files()
        
        if not csv_files:
            print("No CSV files to merge")
            return None
        
        dataframes = []
        rows_removed_per_label = {}
        
        print("\nProcessing files:")
        print("-" * 70)
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                
                # Validate dataframe
                df = self.validate_dataframe(df, csv_file.name)
                if df is None:
                    continue
                
                # Remove empty rows
                df = df.dropna(how='all')
                
                # Remove rows where all coordinate columns are 0 (invalid frames)
                coord_cols = [col for col in df.columns if col != "Label"]
                if len(df) > 0:
                    df = df[(df[coord_cols] != 0).any(axis=1)]
                
                # Remove rows that don't have BOTH hands (critical check)
                initial_count = len(df)
                df = df[df.apply(self.has_both_hands, axis=1)]
                removed_incomplete = initial_count - len(df)
                
                if removed_incomplete > 0:
                    # Track which labels had incomplete data
                    for label in df['Label'].unique():
                        if label not in rows_removed_per_label:
                            rows_removed_per_label[label] = 0
                    print(f"  [!] {csv_file.name:<30} -> Removed {removed_incomplete} rows (incomplete hands)")
                
                if len(df) > 0:
                    dataframes.append(df)
                    samples_in_file = len(df)
                    print(f"  [+] {csv_file.name:<30} -> {samples_in_file:>5} samples (valid)")
                    self.files_merged += 1
                else:
                    print(f"  [x] {csv_file.name:<30} -> No valid data (skipped)")
                    self.skipped_files += 1
            
            except Exception as e:
                print(f"  [ERROR] {csv_file.name}: {str(e)}")
                self.skipped_files += 1
        
        print("-" * 70)
        
        if not dataframes:
            print("No valid dataframes to merge")
            return None
        
        # Concatenate all dataframes
        print(f"\nMerging {len(dataframes)} valid files...")
        merged_df = pd.concat(dataframes, ignore_index=True)
        
        print(f"[+] Merge successful!")
        print(f"    Total samples: {len(merged_df)}")
        
        return merged_df
    
    def generate_statistics(self, df):
        """
        Generate statistics from merged dataframe.
        
        Args:
            df: Merged dataframe
        """
        if df is None or len(df) == 0:
            return
        
        self.total_samples = len(df)
        
        # Count samples per label
        label_value_counts = df['Label'].value_counts().sort_values(ascending=False)
        
        for label, count in label_value_counts.items():
            self.label_counts[label] = count
    
    def print_statistics(self):
        """Print statistics to terminal."""
        print("\n" + "=" * 70)
        print("DATA MERGE SUMMARY")
        print("=" * 70)
        
        print(f"\nStatistics:")
        print(f"  Total samples merged: {self.total_samples}")
        print(f"  Files successfully merged: {self.files_merged}")
        print(f"  Files skipped: {self.skipped_files}")
        
        print(f"\nSamples per gesture (Label):")
        print(f"  {'-' * 65}")
        
        if self.label_counts:
            # Sort by count descending
            sorted_labels = sorted(self.label_counts.items(), key=lambda x: x[1], reverse=True)
            
            max_label_len = max(len(label) for label, _ in sorted_labels)
            
            for label, count in sorted_labels:
                percentage = (count / self.total_samples * 100) if self.total_samples > 0 else 0
                bar_length = int(percentage / 2)  # 50 chars max
                bar = "█" * bar_length + "░" * (50 - bar_length)
                
                print(f"  {label:<{max_label_len}} | {count:>6} samples ({percentage:>5.1f}%) | {bar}")
            
            print(f"  {'-' * 65}")
            
            # Check for balance
            if self.label_counts:
                max_count = max(self.label_counts.values())
                min_count = min(self.label_counts.values())
                balance_ratio = max_count / min_count if min_count > 0 else 0
                
                print(f"\nBalance Analysis:")
                print(f"  Most frequent label: {max_count} samples")
                print(f"  Least frequent label: {min_count} samples")
                print(f"  Imbalance ratio: {balance_ratio:.2f}x")
                
                if balance_ratio > 2.0:
                    print(f"  WARNING: Dataset is IMBALANCED (ratio > 2.0)")
                    print(f"           Consider collecting more data for underrepresented gestures")
                else:
                    print(f"  OK: Dataset is well-balanced (ratio <= 2.0)")
        
        print("\n" + "=" * 70)
    
    def save_statistics_to_markdown(self):
        """Save statistics to markdown file."""
        if self.total_samples == 0:
            return
        
        content = []
        content.append("# Gesture Data Merge Summary\n")
        content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overview
        content.append("## Overview\n")
        content.append(f"- **Total samples merged:** {self.total_samples}\n")
        content.append(f"- **Files successfully merged:** {self.files_merged}\n")
        content.append(f"- **Files skipped:** {self.skipped_files}\n")
        content.append(f"- **Output file:** `final_train.csv`\n\n")
        
        # Per-label statistics
        content.append("## Samples per Gesture\n\n")
        content.append("| Gesture | Count | Percentage | Distribution |\n")
        content.append("|---------|-------|------------|---------------|\n")
        
        if self.label_counts:
            sorted_labels = sorted(self.label_counts.items(), key=lambda x: x[1], reverse=True)
            
            for label, count in sorted_labels:
                percentage = (count / self.total_samples * 100) if self.total_samples > 0 else 0
                bar_length = int(percentage / 5)  # 20 chars max for markdown
                bar = "█" * bar_length
                
                content.append(f"| {label} | {count} | {percentage:.1f}% | {bar} |\n")
        
        content.append("\n")
        
        # Balance analysis
        if self.label_counts:
            max_count = max(self.label_counts.values())
            min_count = min(self.label_counts.values())
            balance_ratio = max_count / min_count if min_count > 0 else 0
            
            content.append("## Balance Analysis\n\n")
            content.append(f"- **Most frequent gesture:** {max_count} samples\n")
            content.append(f"- **Least frequent gesture:** {min_count} samples\n")
            content.append(f"- **Imbalance ratio:** {balance_ratio:.2f}x\n\n")
            
            if balance_ratio > 2.0:
                content.append(" **WARNING:** Dataset is imbalanced. Consider collecting more data for underrepresented gestures.\n")
            else:
                content.append("✓ **Dataset is well-balanced.**\n")
        
        # Write to file
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            f.writelines(content)
        
        print(f"\n✓ Summary saved to: {self.summary_file.name}")
    
    def run(self):
        """Main execution function."""
        print("\n" + "=" * 60)
        print(" GESTURE DATA MERGER")
        print("=" * 60)
        
        # Merge CSV files
        merged_df = self.merge_csv_files()
        
        if merged_df is None or len(merged_df) == 0:
            print("\n Merge failed: No valid data to save")
            return False
        
        # Generate statistics
        self.generate_statistics(merged_df)
        
        # Print statistics
        self.print_statistics()
        
        # Save merged data
        print(f"\n Saving merged data to {self.output_file.name}...")
        try:
            merged_df.to_csv(self.output_file, index=False)
            print(f"✓ Successfully saved: {self.output_file.name}")
        except Exception as e:
            print(f" Error saving file: {str(e)}")
            return False
        
        # Save statistics
        self.save_statistics_to_markdown()
        
        # Final confirmation
        print("\n" + "=" * 60)
        print(f"✓ ✓ ✓ SUCCESS ✓ ✓ ✓")
        print(f"Created final_train.csv with {self.total_samples} total samples")
        print("=" * 60 + "\n")
        
        return True


if __name__ == "__main__":
    # Configuration (modify these if needed)
    INPUT_DIRECTORY = "csv"                    # Folder containing CSV files
    OUTPUT_FILENAME = "final_train.csv"        # Output filename
    
    # Run merger
    merger = GestureDataMerger(
        input_dir=INPUT_DIRECTORY,
        output_filename=OUTPUT_FILENAME
    )
    merger.run()
