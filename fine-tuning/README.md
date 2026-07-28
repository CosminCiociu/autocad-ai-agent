# Fine-Tuning Setup Complete ✅

Bun venit în proces de fine-tuning a modelului qwen2.5:7b pentru desenele de incendiu!

## Quick Start (5 min)

```bash
# Navigate to fine-tuning directory
cd E:\Ai agent\fine-tuning\scripts

# Run quick start (automatically runs extract + annotate + guide)
python quick_start.py
```

## What Just Happened

✅ **Directories created:**

```
E:\Ai agent\fine-tuning\
├── raw_data/              # Your source files
│   ├── drawings/          # Place your .dwg files here
│   ├── legislation/       # Place EN 54-x PDFs here
│   └── payloads/          # Auto-synced from ai-server
├── processed_data/        # Generated datasets
│   ├── raw_extracted.jsonl        # Auto-generated
│   └── annotation_tasks.jsonl     # For manual labeling
├── scripts/               # Automation scripts
│   ├── extract_payloads.py        # Payload extraction
│   ├── annotate_dataset.py        # Annotation guide + tasks
│   ├── validate_dataset.py        # Quality validation
│   ├── quick_start.py             # Run this first
│   └── fine_tune.py              # (To be created)
├── models/                # Trained models storage
└── results/               # Metrics & reports
```

✅ **Scripts created:**

- `extract_payloads.py` - Converts ai-server payloads to training format
- `annotate_dataset.py` - Generates annotation tasks + shows labeling guide
- `validate_dataset.py` - Checks dataset quality before training
- `quick_start.py` - Runs all above steps in sequence

✅ **Output files:**

- `processed_data/raw_extracted.jsonl` - Extracted examples from your payloads
- `processed_data/annotation_tasks.jsonl` - Template for manual annotation

## Step-by-Step Timeline

### Phase 1: Data Extraction (Automated - 5 min)

```bash
python scripts/extract_payloads.py
```

**Output:** `raw_extracted.jsonl` with all payloads converted to training format
**Current state:** You have 4 payloads → Will extract 4 examples

### Phase 2: Annotation (Manual - 2-3 days)

```
For each line in annotation_tasks.jsonl:
1. Read the instruction (user question)
2. Look at the context (drawing entities)
3. Determine the correct action type:
   - find_entities: "Gaseste textele cu BI.1"
   - count_entities: "Cate blocuri au BI in nume"
   - extract_text_data: "Extrage toate numerele BI.x.x"
   - analyze_block_attributes: "Verifica daca au adrese"
4. Fill in action_args based on the context
5. Rate difficulty (easy/medium/hard)
6. Set confidence (0.0-1.0)
7. Add domain tags
```

Save annotated file as: `annotation_tasks_labeled.jsonl`

### Phase 3: Validation (Automated - 5 min)

```bash
python scripts/validate_dataset.py
```

**Output:** `results/validation_report.json`
**Checks:**

- ✅ Action types are valid
- ✅ Difficulty distribution is balanced
- ✅ Confidence scores are reasonable
- ✅ No missing required fields

### Phase 4: Training (Automated - 2-4 hours)

```bash
python scripts/fine_tune.py
```

**Requirements:**

- Python 3.10+
- CUDA 11.8+ (GPU with 8GB+ VRAM)
- ~50GB disk space

**Output:** `models/qwen2.5-7b-finetuned/`

### Phase 5: Integration (Manual - 30 min)

Update ai-server to use new model

## Getting More Training Data

### Option A: Generate More Examples (Recommended for start)

From each payload pair, create variations:

```json
{
  "original": "Gaseste textele cu BI.1",
  "variations": [
    "Find texts containing BI.1",
    "Identifica care texte au BI.1",
    "List all BI.1 texts",
    "Show me texts with BI.1 pattern"
  ]
}
```

### Option B: Add Domain Knowledge

From EN 54 legislation, create synthetic examples:

```json
{
  "instruction": "Verifica daca detectoarele contin adresa conform EN 54-7",
  "context": {block definitions from drawing},
  "output": {synthetic action plan for compliance check}
}
```

### Option C: Create More Real Examples

Use the plugin in AutoCAD:

1. Ask 20-30 different questions
2. Capture payloads
3. Extract using extract_payloads.py
4. Annotate

**Target: 150-300 total examples (50% more than you have now)**

## File Descriptions

### `FINE_TUNING_GUIDE.md` (Main Reference)

- Complete technical guide (7 phases)
- Hardware requirements
- Success criteria
- Example code

### `extract_payloads.py`

Converts HTTP payloads from ai-server into training format:

```
Input:  E:\Ai agent\ai-server\payloads\*_{request,response}.json
Output: E:\Ai agent\fine-tuning\processed_data\raw_extracted.jsonl
```

### `annotate_dataset.py`

Creates annotation tasks and shows labeling guide:

```
- Prints ACTION TYPES and examples
- Prints DIFFICULTY guidelines
- Prints DOMAIN TAGS reference
- Generates annotation_tasks.jsonl template
```

### `validate_dataset.py`

Validates annotated data before training:

```
Checks:
- All required fields present
- Action types are valid
- Difficulty distribution (20-60% medium recommended)
- Confidence scores 0.0-1.0
- Domain tags present
```

### `quick_start.py`

Runs steps 1-2 automatically

## Common Issues & Solutions

### ❌ "Module not found: torch"

```bash
pip install torch transformers datasets peft
```

### ❌ "CUDA not available"

Fine-tuning will still work on CPU (slower). For faster training, install CUDA 11.8+

### ❌ "Out of memory during training"

Reduce batch size in fine_tune.py:

```python
per_device_train_batch_size=2,  # Instead of 4
gradient_accumulation_steps=2,
```

### ❌ "Annotation file not found"

Make sure you've run `annotate_dataset.py` and saved the file as:
`E:\Ai agent\fine-tuning\processed_data\annotation_tasks_labeled.jsonl`

## Success Metrics to Track

After fine-tuning, check:

```json
{
  "baseline_accuracy": 0.45, // Original qwen2.5:7b on your domain
  "finetuned_accuracy": 0.85, // After fine-tuning
  "improvement": "89%", // (0.85-0.45)/0.45 * 100
  "latency_ms": 450, // Response time
  "domain_understanding": "High" // Qualitative assessment
}
```

## Next Actions (Pick One)

1. **Start Small** (Recommended)

   ```bash
   # Manually annotate 20 examples from raw_extracted.jsonl
   # Test validation
   # Then scale up
   ```

2. **Go Full Speed**

   ```bash
   # Annotate all payloads
   # Download EN 54 legislation PDFs
   # Create synthetic examples from legislation
   # Run full training pipeline
   ```

3. **Get Help**
   - Read: E:\Ai agent\FINE_TUNING_GUIDE.md
   - Check: annotation_tasks.jsonl for examples
   - Run: python annotate_dataset.py --guide

## Questions?

Check these in order:

1. `FINE_TUNING_GUIDE.md` - Complete reference
2. `scripts/*.py` - Well-commented code
3. `results/validation_report.json` - After validation
4. Console output from scripts - Usually very clear

---

**Status:** ✅ Setup complete - Ready for Phase 1

**Current data:** 4 payload pairs extracted

**Next step:** Run `python quick_start.py` to see results and annotation guide

Good luck! 🚀
