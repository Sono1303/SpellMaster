import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import time
from pathlib import Path
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report
)

class GestureModelBattle:
    def __init__(self, data_file="final_train.csv", test_size=0.2, random_state=42):
        """
        Initialize the gesture model trainer and comparison system.
        
        Args:
            data_file: Path to final_train.csv
            test_size: Test set ratio (default 20%)
            random_state: Random seed for reproducibility
        """
        self.data_dir = Path(__file__).parent
        self.data_file = self.data_dir / data_file
        self.test_size = test_size
        self.random_state = random_state
        
        # Model storage
        self.models = {}
        self.results = {}
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
        # Visualization outputs
        self.plots_dir = self.data_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)
        
        # Models outputs
        self.models_dir = self.data_dir / "models"
        self.models_dir.mkdir(exist_ok=True)
    
    def load_and_split_data(self):
        """Load and split the training data."""
        print("\n" + "=" * 70)
        print("LOADING AND SPLITTING DATA")
        print("=" * 70)
        
        try:
            df = pd.read_csv(self.data_file)
            print(f"[+] Loaded data from {self.data_file.name}")
            print(f"    Total samples: {len(df)}")
            print(f"    Total features: {len(df.columns) - 1}")  # Exclude label
            
        except FileNotFoundError:
            print(f"[ERROR] File not found: {self.data_file}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load data: {str(e)}")
            return False
        
        # Extract features and labels
        X = df.drop('Label', axis=1)
        y = df['Label']
        
        print(f"\n[+] Data split:")
        print(f"    Training set: {int(len(df) * (1 - self.test_size))} samples ({int((1-self.test_size)*100)}%)")
        print(f"    Test set: {int(len(df) * self.test_size)} samples ({int(self.test_size*100)}%)")
        
        # Stratified split to maintain label distribution
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )
        
        print(f"\n[+] Label distribution in training set:")
        train_dist = self.y_train.value_counts().sort_values(ascending=False)
        for label, count in train_dist.items():
            pct = count / len(self.y_train) * 100
            print(f"    {label}: {count} samples ({pct:.1f}%)")
        
        return True
    
    def train_models(self):
        """Train all models."""
        print("\n" + "=" * 70)
        print("TRAINING MODELS")
        print("=" * 70)
        
        models_config = {
            'Random Forest': RandomForestClassifier(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=-1
            ),
            'SVM (RBF)': SVC(
                kernel='rbf',
                probability=True,
                random_state=self.random_state
            ),
            'K-Nearest Neighbors': KNeighborsClassifier(
                n_neighbors=5
            ),
            'MLP Neural Network': MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=500,
                random_state=self.random_state,
                early_stopping=True,
                validation_fraction=0.1
            )
        }
        
        for model_name, model in models_config.items():
            print(f"\n[*] Training {model_name}...")
            start_time = time.time()
            
            try:
                model.fit(self.X_train, self.y_train)
                train_time = time.time() - start_time
                
                print(f"    [+] Training completed in {train_time:.2f} seconds")
                self.models[model_name] = model
                
            except Exception as e:
                print(f"    [ERROR] Failed to train: {str(e)}")
    
    def evaluate_models(self):
        """Evaluate all trained models."""
        print("\n" + "=" * 70)
        print("EVALUATING MODELS")
        print("=" * 70)
        
        for model_name, model in self.models.items():
            print(f"\n[*] Evaluating {model_name}...")
            
            # Make predictions
            y_pred = model.predict(self.X_test)
            
            # Calculate metrics
            accuracy = accuracy_score(self.y_test, y_pred)
            f1_weighted = f1_score(self.y_test, y_pred, average='weighted', zero_division=0)
            
            # Calculate inference time
            start_time = time.time()
            num_inferences = 100
            for _ in range(num_inferences):
                model.predict(self.X_test.iloc[:1])
            inference_time_ms = (time.time() - start_time) / num_inferences * 1000
            
            # Store results
            self.results[model_name] = {
                'accuracy': accuracy,
                'f1_score': f1_weighted,
                'inference_time': inference_time_ms,
                'y_pred': y_pred,
                'confusion_matrix': confusion_matrix(self.y_test, y_pred)
            }
            
            print(f"    Accuracy: {accuracy * 100:.2f}%")
            print(f"    F1-Score (Weighted): {f1_weighted:.4f}")
            print(f"    Inference Time: {inference_time_ms:.3f} ms")
    
    def calculate_balanced_score(self, accuracy, inference_time):
        """
        Calculate a balanced score considering both accuracy and inference time.
        Prioritizes inference time for real-time applications (SpellMaster).
        
        Formula: accuracy_score * speed_score
        - accuracy_score: normalized accuracy (0-1)
        - speed_score: normalized inverse of inference time
        """
        # Normalize accuracy to 0-1 range
        accuracy_score = accuracy
        
        # Normalize inference time: faster = higher score
        # Using inverse: lower inference time = higher speed score
        # Reference: 20ms for good responsiveness
        speed_score = 20.0 / (inference_time + 1.0)  # +1 to avoid division issues
        speed_score = min(speed_score, 1.0)  # Cap at 1.0
        
        # Weight: 70% accuracy, 30% speed (for real-time gesture recognition)
        balanced_score = (accuracy_score * 0.7) + (speed_score * 0.3)
        
        return balanced_score
    
    def print_comparison_table(self):
        """Print detailed comparison table with balanced scoring."""
        print("\n" + "=" * 70)
        print("MODEL COMPARISON RESULTS")
        print("=" * 70)
        
        # Create comparison dataframe with balanced scores
        comparison_data = []
        for model_name, metrics in self.results.items():
            balanced_score = self.calculate_balanced_score(
                metrics['accuracy'],
                metrics['inference_time']
            )
            comparison_data.append({
                'Model': model_name,
                'Accuracy (%)': f"{metrics['accuracy'] * 100:.2f}",
                'F1-Score': f"{metrics['f1_score']:.4f}",
                'Inference Time (ms)': f"{metrics['inference_time']:.3f}",
                'Balanced Score': f"{balanced_score:.4f}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        print("\n" + comparison_df.to_string(index=False))
        
        # Find models by different criteria
        best_accuracy_model = max(self.results.items(), key=lambda x: x[1]['accuracy'])
        fastest_model = min(self.results.items(), key=lambda x: x[1]['inference_time'])
        
        # Find best balanced model (best for real-time applications)
        best_balanced_model = max(
            self.results.items(),
            key=lambda x: self.calculate_balanced_score(x[1]['accuracy'], x[1]['inference_time'])
        )
        
        print("\n" + "-" * 70)
        print(f"[+] Best Accuracy: {best_accuracy_model[0]}")
        print(f"    Accuracy: {best_accuracy_model[1]['accuracy'] * 100:.2f}%")
        
        print(f"\n[+] Fastest Model: {fastest_model[0]}")
        print(f"    Inference Time: {fastest_model[1]['inference_time']:.3f} ms")
        
        print(f"\n[+] Best for Real-Time (Balanced Score): {best_balanced_model[0]}")
        balanced_score = self.calculate_balanced_score(
            best_balanced_model[1]['accuracy'],
            best_balanced_model[1]['inference_time']
        )
        print(f"    Accuracy: {best_balanced_model[1]['accuracy'] * 100:.2f}%")
        print(f"    Inference Time: {best_balanced_model[1]['inference_time']:.3f} ms")
        print(f"    Balanced Score: {balanced_score:.4f}")
        print(f"    Reasoning: 70% accuracy weight + 30% speed weight")
        
        return best_balanced_model
    
    def plot_comparison(self):
        """Create comparison plots."""
        print("\n[*] Creating comparison plots...")
        
        model_names = list(self.results.keys())
        accuracies = [self.results[m]['accuracy'] * 100 for m in model_names]
        inference_times = [self.results[m]['inference_time'] for m in model_names]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Accuracy comparison
        colors_acc = ['#2ecc71' if acc == max(accuracies) else '#3498db' for acc in accuracies]
        axes[0].bar(model_names, accuracies, color=colors_acc, edgecolor='black', linewidth=1.5)
        axes[0].set_ylabel('Accuracy (%)', fontsize=12, fontweight='bold')
        axes[0].set_title('Model Accuracy Comparison', fontsize=13, fontweight='bold')
        axes[0].set_ylim([0, 105])
        axes[0].grid(axis='y', alpha=0.3, linestyle='--')
        for i, (name, acc) in enumerate(zip(model_names, accuracies)):
            axes[0].text(i, acc + 2, f'{acc:.1f}%', ha='center', fontweight='bold')
        axes[0].tick_params(axis='x', rotation=15)
        
        # Inference time comparison
        colors_time = ['#e74c3c' if t == min(inference_times) else '#f39c12' for t in inference_times]
        axes[1].bar(model_names, inference_times, color=colors_time, edgecolor='black', linewidth=1.5)
        axes[1].set_ylabel('Inference Time (ms)', fontsize=12, fontweight='bold')
        axes[1].set_title('Model Inference Time Comparison', fontsize=13, fontweight='bold')
        axes[1].grid(axis='y', alpha=0.3, linestyle='--')
        for i, (name, time_ms) in enumerate(zip(model_names, inference_times)):
            axes[1].text(i, time_ms + 0.05, f'{time_ms:.3f}ms', ha='center', fontweight='bold')
        axes[1].tick_params(axis='x', rotation=15)
        
        plt.tight_layout()
        comparison_file = self.plots_dir / "model_comparison.png"
        plt.savefig(comparison_file, dpi=300, bbox_inches='tight')
        print(f"[+] Saved comparison plot to {comparison_file.name}")
        
        return fig
    
    def plot_confusion_matrix(self, best_model_name):
        """Plot confusion matrix for best model."""
        print(f"\n[*] Creating confusion matrix for {best_model_name}...")
        
        cm = self.results[best_model_name]['confusion_matrix']
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=self.y_test.unique(),
            yticklabels=self.y_test.unique(),
            cbar_kws={'label': 'Count'},
            ax=ax,
            linewidths=0.5,
            linecolor='gray'
        )
        
        ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
        ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
        ax.set_title(f'Confusion Matrix - {best_model_name}', fontsize=13, fontweight='bold')
        
        plt.tight_layout()
        cm_file = self.plots_dir / "confusion_matrix.png"
        plt.savefig(cm_file, dpi=300, bbox_inches='tight')
        print(f"[+] Saved confusion matrix to {cm_file.name}")
        
        return fig
    
    def save_best_model(self, best_model_name):
        """Save the best model."""
        print(f"\n[*] Saving best model...")
        
        best_model = self.models[best_model_name]
        model_file = self.models_dir / "best_spell_model.pkl"
        
        try:
            joblib.dump(best_model, model_file)
            print(f"[+] Model saved to models/{model_file.name}")
            print(f"[+] Model {best_model_name} has won and been saved!")
            
        except Exception as e:
            print(f"[ERROR] Failed to save model: {str(e)}")
    
    def print_detailed_report(self, best_model_name):
        """Print detailed classification report for best model."""
        print("\n" + "=" * 70)
        print(f"DETAILED REPORT - {best_model_name.upper()}")
        print("=" * 70)
        
        y_pred = self.results[best_model_name]['y_pred']
        
        print("\nClassification Report:")
        print(classification_report(self.y_test, y_pred))
    
    def save_model_statistics(self, best_model_name):
        """Save detailed model comparison statistics to markdown file."""
        print(f"\n[*] Saving model statistics to markdown...")
        
        stats_file = self.models_dir / "model_statistics.md"
        
        content = []
        content.append("# Gesture Spell Model Comparison Report\n\n")
        content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Overview
        content.append("## Model Performance Summary\n\n")
        content.append(f"**Best Model (Balanced Score):** {best_model_name}\n\n")
        content.append(f"**Accuracy:** {self.results[best_model_name]['accuracy'] * 100:.2f}%\n\n")
        content.append(f"**F1-Score (Weighted):** {self.results[best_model_name]['f1_score']:.4f}\n\n")
        content.append(f"**Inference Time:** {self.results[best_model_name]['inference_time']:.3f} ms\n\n")
        
        # Balanced score explanation
        balanced_score = self.calculate_balanced_score(
            self.results[best_model_name]['accuracy'],
            self.results[best_model_name]['inference_time']
        )
        content.append(f"**Balanced Score:** {balanced_score:.4f}\n\n")
        content.append("### Selection Logic\n\n")
        content.append("The best model is selected using a **balanced scoring system** that considers both:")
        content.append("\n- **Accuracy (70% weight):** Model precision for gesture recognition")
        content.append("\n- **Speed (30% weight):** Response time for real-time spell casting")
        content.append("\n\nThis weighted approach optimizes for SpellMaster use case where both accuracy and real-time responsiveness are crucial.\n\n")
        
        # Detailed comparison table
        content.append("## Detailed Model Comparison\n\n")
        content.append("| Model | Accuracy (%) | F1-Score | Inference Time (ms) |\n")
        content.append("|-------|--------------|----------|---------------------|\n")
        
        for model_name, metrics in sorted(self.results.items(), 
                                         key=lambda x: x[1]['accuracy'], 
                                         reverse=True):
            winner_mark = " (WINNER)" if model_name == best_model_name else ""
            content.append(
                f"| {model_name}{winner_mark} | {metrics['accuracy'] * 100:.2f}% | "
                f"{metrics['f1_score']:.4f} | {metrics['inference_time']:.3f} |\n"
            )
        
        content.append("\n")
        
        # Best and Fastest models
        best_acc_model = max(self.results.items(), key=lambda x: x[1]['accuracy'])
        fastest_model = min(self.results.items(), key=lambda x: x[1]['inference_time'])
        
        content.append("## Rankings\n\n")
        content.append(f"**Highest Accuracy:** {best_acc_model[0]} "
                      f"({best_acc_model[1]['accuracy'] * 100:.2f}%)\n\n")
        content.append(f"**Fastest Inference:** {fastest_model[0]} "
                      f"({fastest_model[1]['inference_time']:.3f} ms)\n\n")
        
        # Data statistics
        content.append("## Training Data Statistics\n\n")
        content.append(f"**Total Samples:** {len(self.X_train) + len(self.X_test)}\n\n")
        content.append(f"**Training Set:** {len(self.X_train)} samples ({int(len(self.X_train)/(len(self.X_train)+len(self.X_test))*100)}%)\n\n")
        content.append(f"**Test Set:** {len(self.X_test)} samples ({int(len(self.X_test)/(len(self.X_train)+len(self.X_test))*100)}%)\n\n")
        content.append(f"**Number of Features:** {len(self.X_train.columns)}\n\n")
        
        # Label distribution
        content.append("### Label Distribution (Training Set)\n\n")
        train_dist = self.y_train.value_counts().sort_values(ascending=False)
        for label, count in train_dist.items():
            pct = count / len(self.y_train) * 100
            content.append(f"- {label}: {count} samples ({pct:.1f}%)\n")
        
        content.append("\n")
        
        # Classification report for best model
        content.append("## Detailed Classification Report (Best Model)\n\n")
        content.append("```\n")
        y_pred = self.results[best_model_name]['y_pred']
        report = classification_report(self.y_test, y_pred)
        content.append(report)
        content.append("```\n\n")
        
        # Model descriptions
        content.append("## Model Descriptions\n\n")
        content.append("**Random Forest:** Ensemble method with 100 decision trees. "
                      "Good for overall accuracy and feature importance.\n\n")
        content.append("**SVM (RBF):** Support Vector Machine with Radial Basis Function kernel. "
                      "Powerful for non-linear classification with balanced performance.\n\n")
        content.append("**K-Nearest Neighbors:** Instance-based learning algorithm (k=5). "
                      "Simple but can be slow for inference.\n\n")
        content.append("**MLP Neural Network:** Multi-layer perceptron with hidden layers (64, 32). "
                      "Often fastest inference time, good for real-time applications.\n\n")
        
        # Save to file
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                f.writelines(content)
            print(f"[+] Model statistics saved to models/model_statistics.md")
        except Exception as e:
            print(f"[ERROR] Failed to save statistics: {str(e)}")
    
    def run(self):
        """Main execution function."""
        print("\n" + "=" * 70)
        print("GESTURE SPELL MODEL BATTLE & TRAINER")
        print("=" * 70)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Load and split data
        if not self.load_and_split_data():
            return False
        
        # Step 2: Train models
        self.train_models()
        
        if not self.models:
            print("\n[ERROR] No models were trained successfully")
            return False
        
        # Step 3: Evaluate models
        self.evaluate_models()
        
        # Step 4: Print comparison
        best_model_name, best_metrics = self.print_comparison_table()
        
        # Step 5: Create visualizations
        self.plot_comparison()
        self.plot_confusion_matrix(best_model_name)
        
        # Step 6: Save best model
        self.save_best_model(best_model_name)
        
        # Step 7: Print detailed report
        self.print_detailed_report(best_model_name)
        
        # Step 8: Save model statistics
        self.save_model_statistics(best_model_name)
        
        print("\n" + "=" * 70)
        print("BATTLE COMPLETED")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")
        
        return True


if __name__ == "__main__":
    trainer = GestureModelBattle(
        data_file="final_train.csv",
        test_size=0.2,
        random_state=42
    )
    
    success = trainer.run()
    
    # Display plots
    if success:
        plt.show()
