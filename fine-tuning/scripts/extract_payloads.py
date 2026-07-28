#!/usr/bin/env python3
"""
Extract payload pairs and convert to training format.
Usage: python extract_payloads.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
PAYLOADS_DIR = Path(r"E:\Ai agent\ai-server\payloads")
OUTPUT_DIR = Path(r"E:\Ai agent\fine-tuning\raw_data\payloads")
PROCESSED_DIR = Path(r"E:\Ai agent\fine-tuning\processed_data")

def extract_payload_pair(request_file, response_file):
    """Convert request+response payload pair to training format."""
    try:
        with open(request_file, encoding='utf-8') as f:
            req = json.load(f)
        with open(response_file, encoding='utf-8') as f:
            resp = json.load(f)
        
        # Extract user command from messages
        messages = req.get("messages", [])
        user_command = ""
        if messages:
            user_command = messages[-1].get("content", "")
        
        # Get context
        context = req.get("context", {})
        
        return {
            "instruction": user_command,
            "input": {
                "context": {
                    "drawing_name": context.get("drawing", {}).get("name", "unknown"),
                    "schema_version": context.get("schema_version", "1.0.0"),
                    "blocks_count": len(context.get("blocks", [])),
                    "texts_count": len(context.get("texts", [])),
                    "lines_count": len(context.get("lines", [])),
                    "polylines_count": len(context.get("polylines", [])),
                },
                "conversation_history": messages[:-1] if len(messages) > 1 else []
            },
            "output": {
                "summary": resp.get("assistant_message", ""),
                "action_plan": resp.get("action_plan", {}),
            },
            "metadata": {
                "source": "autocad_plugin_payload",
                "request_id": req.get("request_id", ""),
                "response_id": resp.get("request_id", ""),
                "timestamp": req.get("timestamp", datetime.now().isoformat()),
                "difficulty": "auto",  # To be labeled manually
                "domain_tags": ["fire_safety", "cad_analysis"]
            }
        }
    except Exception as e:
        print(f"Error processing {request_file}: {e}")
        return None

def extract_request_id_from_filename(filename):
    """Extract request_id from filename: timestamp_req-UUID_type.json"""
    # Format: YYYY-MM-DD_HH-MM-SS-fff_req-{UUID}_{type}.json
    parts = filename.replace('.json', '').split('_req-')
    if len(parts) == 2:
        # Get UUID part (between req- and _request/_response)
        uuid_and_type = parts[1]
        uuid_part = '_'.join(uuid_and_type.split('_')[:-1])  # Remove type suffix
        return uuid_part
    return None

def main():
    print("🔄 Extracting payloads...")
    print(f"   Source: {PAYLOADS_DIR}")
    print(f"   Output: {OUTPUT_DIR}\n")
    
    if not PAYLOADS_DIR.exists():
        print(f"❌ Payloads directory not found: {PAYLOADS_DIR}")
        return 1
    
    # Find all request files
    request_files = sorted(PAYLOADS_DIR.glob("*_request.json"))
    print(f"Found {len(request_files)} request files\n")
    
    # Build map of request_id -> response file
    all_files = list(PAYLOADS_DIR.glob("*.json"))
    response_map = {}
    for f in all_files:
        if "_response.json" in f.name:
            req_id = extract_request_id_from_filename(f.name)
            if req_id:
                response_map[req_id] = f
    
    training_examples = []
    success_count = 0
    error_count = 0
    
    for req_file in request_files:
        req_id = extract_request_id_from_filename(req_file.name)
        
        if req_id and req_id in response_map:
            resp_file = response_map[req_id]
            example = extract_payload_pair(req_file, resp_file)
            if example:
                training_examples.append(example)
                success_count += 1
                print(f"✓ {req_file.name}")
                print(f"  └─ {resp_file.name}")
        else:
            error_count += 1
            print(f"⚠ Missing response for request_id: {req_id}")
    
    print(f"\n✅ Processed {success_count} payload pairs")
    if error_count > 0:
        print(f"⚠️  {error_count} errors/missing files")
    
    if not training_examples:
        print("❌ No examples extracted!")
        return 1
    
    # Save as JSONL
    output_file = PROCESSED_DIR / "raw_extracted.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding='utf-8') as f:
        for example in training_examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    
    print(f"\n📊 Saved {len(training_examples)} examples to: {output_file}")
    
    # Print statistics
    print("\n📈 Statistics:")
    print(f"   Total examples: {len(training_examples)}")
    print(f"   Avg messages per example: {sum(len(e['input']['conversation_history']) for e in training_examples) / len(training_examples):.1f}")
    
    # Print sample
    if training_examples:
        print("\n📋 Sample example:")
        sample = training_examples[0]
        print(f"   Instruction: {sample['instruction'][:60]}...")
        print(f"   Context: {sample['input']['context']['drawing_name']}")
        print(f"   Output summary: {sample['output']['summary'][:60]}...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
