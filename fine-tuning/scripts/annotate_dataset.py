#!/usr/bin/env python3
"""
Annotation template and manual labeling guide.
Run after extract_payloads.py to create annotation tasks.
"""

import json
import sys
from pathlib import Path
from enum import Enum

class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ActionType(Enum):
    FIND_ENTITIES = "find_entities"
    COUNT_ENTITIES = "count_entities"
    EXTRACT_TEXT_DATA = "extract_text_data"
    ANALYZE_BLOCK_ATTRIBUTES = "analyze_block_attributes"

# Action type definitions for fire safety drawings
ACTION_DEFINITIONS = {
    "find_entities": {
        "description": "Search for entities matching criteria",
        "examples": [
            "Gaseste textele care contin 'BI.1'",
            "Find all blocks named 'FA-D1'",
            "List entities on layer 'GI - INCENDIU'"
        ]
    },
    "count_entities": {
        "description": "Count entities by type or criteria",
        "examples": [
            "Cate blocuri sunt in total?",
            "How many texts contain 'BI.'?",
            "Count detectors on each floor"
        ]
    },
    "extract_text_data": {
        "description": "Extract and process text values",
        "examples": [
            "Extract all BI.x.x patterns",
            "List all text values from layer X",
            "Get detector addresses"
        ]
    },
    "analyze_block_attributes": {
        "description": "Analyze block attributes for compliance",
        "examples": [
            "Verify EN 54-4 compliance for power supply",
            "Check if all detectors have addresses",
            "Analyze block placement per floor"
        ]
    }
}

def create_annotation_template():
    """Create empty annotation template."""
    return {
        "instruction": "",
        "input": {
            "context": {
                "drawing_name": "",
                "blocks_count": 0,
                "texts_count": 0,
            },
            "conversation_history": []
        },
        "output": {
            "action_type": "",  # one of ACTION_TYPES
            "action_args": {},
            "summary": ""
        },
        "annotation": {
            "annotator": "username",
            "difficulty": "",  # easy, medium, hard
            "confidence": 0.0,  # 0.0 to 1.0
            "domain_tags": [],  # fire_safety, pattern_matching, text_search, etc
            "notes": ""
        }
    }

def print_annotation_guide():
    """Print guide for manual annotation."""
    print("=" * 70)
    print("ANNOTATION GUIDE - Fine-Tuning Fire Safety CAD Assistant")
    print("=" * 70)
    
    print("\n📋 ACTION TYPES:\n")
    for action_name, definition in ACTION_DEFINITIONS.items():
        print(f"  {action_name.upper()}")
        print(f"    Description: {definition['description']}")
        print(f"    Examples:")
        for example in definition['examples']:
            print(f"      - {example}")
        print()
    
    print("\n⏱️  DIFFICULTY LEVELS:\n")
    print("  EASY (30%)")
    print("    - Simple entity counting")
    print("    - Single pattern match")
    print("    - Direct questions")
    print("    Example: 'Cate blocuri sunt in desen?'")
    print()
    print("  MEDIUM (50%)")
    print("    - Pattern matching (BI.1.1 format)")
    print("    - Requires understanding context")
    print("    - Multi-step reasoning")
    print("    Example: 'Gaseste textele cu BI.1 in ele'")
    print()
    print("  HARD (20%)")
    print("    - Complex reasoning")
    print("    - Multi-layer analysis")
    print("    - Compliance checking")
    print("    Example: 'Verifica daca detectoarele contin adresa valida'")
    
    print("\n🏷️  DOMAIN TAGS:\n")
    tags = [
        "fire_safety - General fire safety context",
        "pattern_matching - Requires regex/pattern logic",
        "text_search - Search in text entities",
        "block_analysis - Analysis of block definitions",
        "compliance - EN 54 or building code compliance",
        "counting - Simple counting operations",
        "multi_layer - Requires understanding relationships",
        "attribute_checking - Block attribute analysis"
    ]
    for tag in tags:
        print(f"  - {tag}")
    
    print("\n💡 CONFIDENCE LEVELS:\n")
    print("  1.0 - Absolutely certain")
    print("  0.8 - Very confident")
    print("  0.6 - Reasonably confident")
    print("  0.4 - Somewhat uncertain")
    print("  0.2 - Very uncertain but best guess")
    
    print("\n" + "=" * 70)

def generate_annotation_tasks():
    """Generate annotation tasks from extracted payloads."""
    input_file = Path(r"E:\Ai agent\fine-tuning\processed_data\raw_extracted.jsonl")
    output_file = Path(r"E:\Ai agent\fine-tuning\processed_data\annotation_tasks.jsonl")
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        print("   Run extract_payloads.py first!")
        return 1
    
    print(f"📝 Generating annotation tasks...\n")
    
    tasks = []
    with open(input_file, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            try:
                example = json.loads(line)
                task = create_annotation_template()
                
                # Copy fields from extracted example
                task["instruction"] = example["instruction"]
                task["input"] = example["input"]
                
                # Output summary (already filled from response)
                if example.get("output", {}).get("summary"):
                    task["output"]["summary"] = example["output"]["summary"]
                
                tasks.append(task)
            except json.JSONDecodeError as e:
                print(f"⚠️  Error parsing line {i}: {e}")
    
    # Save tasks
    with open(output_file, "w", encoding='utf-8') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    
    print(f"✅ Generated {len(tasks)} annotation tasks")
    print(f"📁 Saved to: {output_file}\n")
    
    print("📋 Next steps:")
    print("   1. Open annotation_tasks.jsonl")
    print("   2. For each task, fill in:")
    print("      - output.action_type (see guide above)")
    print("      - output.action_args (specific arguments)")
    print("      - annotation.difficulty (easy/medium/hard)")
    print("      - annotation.confidence (0.0-1.0)")
    print("      - annotation.domain_tags (list of tags)")
    print("      - annotation.notes (any clarifications)")
    print("   3. Save as annotation_tasks_labeled.jsonl")
    print("   4. Run validate_dataset.py to check quality")
    
    return 0

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--guide":
        print_annotation_guide()
        return 0
    
    print_annotation_guide()
    print("\n\n")
    return generate_annotation_tasks()

if __name__ == "__main__":
    sys.exit(main())
