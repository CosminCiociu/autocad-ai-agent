#!/usr/bin/env python3
"""
Quick start script - Runs all preparation steps in sequence.
Usage: python quick_start.py
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*70}")
    print(f"🚀 {description}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"\n⚠️  Command failed with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("🎯 FINE-TUNING QUICK START - Fire Safety CAD Assistant")
    print("="*70)
    
    scripts_dir = Path(__file__).parent
    
    steps = [
        (
            [sys.executable, str(scripts_dir / "extract_payloads.py")],
            "Step 1: Extract payloads from ai-server"
        ),
        (
            [sys.executable, str(scripts_dir / "annotate_dataset.py")],
            "Step 2: Generate annotation tasks and show guide"
        ),
    ]
    
    for cmd, description in steps:
        if not run_command(cmd, description):
            print(f"\n❌ Stopped at: {description}")
            return 1
    
    print("\n" + "="*70)
    print("✅ QUICK START COMPLETE")
    print("="*70)
    
    print(r"""
📋 Next steps:

1. ANNOTATION PHASE (Manual work - 2-3 days)
   ├─ Open: E:\Ai agent\fine-tuning\processed_data\annotation_tasks.jsonl
   ├─ For each task, fill in:
   │  ├─ output.action_type (find_entities, count_entities, extract_text_data, analyze_block_attributes)
   │  ├─ output.action_args (specific arguments for the action)
   │  ├─ annotation.difficulty (easy/medium/hard)
   │  ├─ annotation.confidence (0.0-1.0)
   │  ├─ annotation.domain_tags (list of tags)
   │  └─ annotation.notes (clarifications)
   └─ Save as: annotation_tasks_labeled.jsonl

2. VALIDATION PHASE (Run once labeled)
   └─ python scripts/validate_dataset.py
      ├─ Checks quality
      ├─ Verifies distribution
      └─ Generates report

3. FINE-TUNING PHASE (When validation passes)
   └─ python scripts/fine_tune.py
      ├─ Setup LoRA config
      ├─ Load model
      ├─ Train
      └─ Save checkpoint

4. INTEGRATION (Deploy new model)
   └─ Export to GGUF
   └─ Create Ollama model
   └─ Update ai-server

📚 Documentation:
   - Read: E:\Ai agent\FINE_TUNING_GUIDE.md (complete reference)
   - Check: E:\Ai agent\fine-tuning\results\validation_report.json (after validation)

💡 Tips:
   - Start with 20-30 examples before full annotation
   - Aim for 80%+ high-confidence examples (0.8+)
   - Balance action types and difficulties
   - Add domain-specific notes for edge cases

🎯 Success criteria:
   - 85%+ accuracy on test set
   - Correctly identifies text patterns (BI.1.1, etc)
   - Understands fire safety context
   - 50%+ improvement vs baseline

Good luck! 🚀
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
