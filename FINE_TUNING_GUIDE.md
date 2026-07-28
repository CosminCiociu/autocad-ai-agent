# Fine-Tuning qwen2.5:7b pentru Desenele de Incendiu

## Faza 1: PREPARARE DATASET

### 1.1 Colectare Date - Ce Trebuie

```
Directory structure:
E:\Ai agent\fine-tuning\
├── raw_data/
│   ├── drawings/          # Desenele tale .dwg
│   ├── legislation/       # PDF-uri legislații (EN 54-x, ISO 7240-x)
│   └── payloads/         # Payload-uri din E:\Ai agent\ai-server\payloads\
├── processed_data/
│   ├── training.jsonl    # Training set (80%)
│   ├── validation.jsonl  # Validation set (10%)
│   └── test.jsonl        # Test set (10%)
├── scripts/
│   ├── extract_payloads.py
│   ├── annotate_dataset.py
│   ├── validate_dataset.py
│   └── fine_tune.py
├── models/
│   └── qwen2.5-7b-finetuned/
└── results/
    ├── training_metrics.json
    └── evaluation_report.json
```

### 1.2 Ce Trebuie Colectat

**A. Payload-uri existente** (deja ai 4, trebuie min 100-200):

- Request payloads (context + mesaj utilizator)
- Response payloads (action plan generat)
- Logs cu raw_response din model

**B. Legislații:**

- EN 54-1: General requirements (architecture)
- EN 54-2: Control and indicating equipment
- EN 54-4: Power supply
- EN 54-5: Heat detectors
- EN 54-7: Smoke detectors
- EN 54-8: Manual call points
- EN 54-10: Alarm devices
- EN 54-12: Emergency voice alarm system
- ISO 7240-x: Fire detection / Alarm system specifics

**C. Din desenele tale:**

- Block names (FA-D1, FA-B1, etc.)
- Text patterns (BI.1.1, BI.2.1, etc.)
- Layer names
- Attribute meanings

---

## Faza 2: DATASET ANNOTATION (Labeling)

### 2.1 Format Dataset - JSONL Line Format

Fiecare linie = 1 training example:

```json
{
  "instruction": "Gaseste textele care contin 'BI.1' in desenul de incendiu",
  "input": {
    "context": {
      "drawing_name": "ICS01_ICS02_Plan incendiu.dwg",
      "blocks_count": 90,
      "texts_count": 96,
      "texts_sample": [
        { "value": "BI.1.1", "layer": "GRINZI" },
        { "value": "BI.1.2", "layer": "GRINZI" }
      ]
    },
    "conversation_history": [
      { "role": "user", "content": "Identifica blocuriile" },
      { "role": "assistant", "content": "Identific..." }
    ]
  },
  "output": {
    "action_type": "find_entities",
    "action_args": {
      "entity_type": "text",
      "text_contains": "BI.1"
    },
    "summary": "Identific textele care au 'BI.1' in continut"
  },
  "source": "drawing_ICS01_ICS02",
  "difficulty": "medium",
  "domain_tags": ["fire_safety", "text_search", "pattern_matching"]
}
```

### 2.2 Clase de Acțiuni (Action Classes)

Modelul trebuie să ofere pentru desenele tale:

```python
ACTION_CLASSES = {
    "find_entities": {
        "description": "Search for entities matching criteria",
        "args": {
            "entity_type": ["block", "text", "line", "polyline"],
            "text_contains": "string pattern",
            "layer": "layer name",
            "block_name": "block definition"
        }
    },
    "count_entities": {
        "description": "Count entities by type/criteria",
        "args": {
            "entity_type": ["block", "text"],
            "filter_by": ["layer", "text_pattern", "name_pattern"]
        }
    },
    "extract_text_data": {
        "description": "Extract text values matching pattern (BI.x.x format)",
        "args": {
            "pattern": "regex or simple pattern",
            "layers": ["layer_names"]
        }
    },
    "analyze_block_attributes": {
        "description": "Analyze block attributes for compliance",
        "args": {
            "block_type": "FA-D1 | FA-B1 | etc",
            "attribute_tags": ["ADRESA", "custom tags"]
        }
    }
}
```

### 2.3 Niveluri de Dificultate

```
Easy (30%):
  - Simple entity counting
  - Single pattern match
  - Example: "Cate blocuri sunt in desen?"

Medium (50%):
  - Pattern matching (BI.1.1)
  - Multi-step reasoning
  - Example: "Gaseste textele cu BI.1 in ele"

Hard (20%):
  - Complex reasoning
  - Multi-layer analysis
  - Compliance checking
  - Example: "Verifica daca detectoarele de fum sunt pe fiecare etaj"
```

---

## Faza 3: DATASET CREATION TOOLS

### 3.1 Script: Extract & Convert Payloads

```python
# fine-tuning/scripts/extract_payloads.py

import json
from pathlib import Path

def extract_payload_pair(request_file, response_file):
    """Convert payload pair to training format"""
    with open(request_file) as f:
        req = json.load(f)
    with open(response_file) as f:
        resp = json.load(f)

    return {
        "instruction": req.get("messages", [{}])[-1].get("content", ""),
        "input": {
            "context": req.get("context", {}),
            "conversation_history": req.get("messages", [])
        },
        "output": {
            "action_type": "find_entities",  # Need to infer from response
            "summary": resp.get("assistant_message", "")
        },
        "source": "autocad_payload",
        "difficulty": "auto",  # To be labeled manually
        "domain_tags": ["fire_safety"]
    }

def generate_training_dataset():
    payloads_dir = Path("E:\\Ai agent\\ai-server\\payloads")
    training_data = []

    for req_file in sorted(payloads_dir.glob("*_request.json")):
        resp_file = req_file.parent / req_file.name.replace("_request", "_response")
        if resp_file.exists():
            example = extract_payload_pair(req_file, resp_file)
            training_data.append(example)

    return training_data

if __name__ == "__main__":
    data = generate_training_dataset()
    # Save to training.jsonl
    with open("processed_data/training.jsonl", "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"Generated {len(data)} examples")
```

### 3.2 Manual Annotation Template

Pentru fiecare payload, trebuie completat:

```json
{
  "instruction": "...",  # User's actual question
  "input": {...},
  "output": {
    "action_type": "find_entities|count_entities|extract_text_data|analyze_block_attributes",
    "action_args": {
      // Specific arguments
    },
    "summary": "...",
    "expected_actions": [
      {
        "id": "action-1",
        "type": "find_entities",
        "args": {"entity_type": "text", "text_contains": "BI.1"}
      }
    ]
  },
  "metadata": {
    "annotated_by": "username",
    "annotation_date": "2026-07-23",
    "confidence": 0.95,
    "notes": "Clear domain-specific request"
  }
}
```

---

## Faza 4: QUANTITY REQUIREMENTS

### 4.1 Minimum Dataset Size

```
Total Examples Needed: 150-300 examples
  - Training (70%):   105-210 examples
  - Validation (15%):  22-45 examples
  - Test (15%):        22-45 examples

Distribution by Difficulty:
  - Easy: 45-90 examples (30%)
  - Medium: 75-150 examples (50%)
  - Hard: 30-60 examples (20%)

Distribution by Action Type:
  - find_entities: 60-100 examples (40%)
  - count_entities: 30-60 examples (20%)
  - extract_text_data: 30-60 examples (20%)
  - analyze_block_attributes: 30-80 examples (20%)
```

### 4.2 How to Generate Examples from Your Data

**From existing payloads (4 → 20):**

```
Per payload, create 5 variations:
1. Original request
2. Paraphrased request (different wording, same intent)
3. Follow-up question (depends on previous)
4. Error case (common mistake)
5. Edge case (boundary condition)
```

**From legislations (EN 54-x):**

```
Extract domain knowledge:
1. "What are the requirements for fire detectors?" → extract_text_data
2. "On which layers should FA-D1 blocks be?" → analyze_block_attributes
3. "How many alarm devices per floor?" → count_entities
4. "Find all smoke detectors (type FA-B1)" → find_entities
```

**From drawing analysis:**

```
Per drawing, create:
1. "Count X entities" queries
2. "Find Y with pattern Z" queries
3. "Verify compliance with EN 54-4" queries
4. "List all entities on layer X" queries
```

---

## Faza 5: FINE-TUNING EXECUTION

### 5.1 Local Fine-Tuning Setup

```bash
# Install required packages
pip install torch transformers datasets peft

# Directory structure
E:\Ai agent\fine-tuning\
├── venv/                    # Virtual environment
├── scripts/
│   ├── fine_tune.py        # Main training script
│   └── evaluate.py         # Evaluation script
└── models/
    └── qwen2.5-7b-finetuned/
```

### 5.2 Training Script Template

```python
# fine-tuning/scripts/fine_tune.py

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_dataset
from peft import get_peft_model, LoraConfig, TaskType
import torch

def fine_tune_qwen():
    # 1. Load base model
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    # 2. Setup LoRA (efficient fine-tuning)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=["q_proj", "v_proj"]
    )
    model = get_peft_model(model, lora_config)

    # 3. Load dataset
    dataset = load_dataset(
        "json",
        data_files={
            "train": "processed_data/training.jsonl",
            "validation": "processed_data/validation.jsonl"
        }
    )

    # 4. Tokenize
    def preprocess_function(examples):
        inputs = tokenizer(
            examples["instruction"],
            max_length=512,
            truncation=True,
            padding="max_length"
        )
        return inputs

    tokenized_datasets = dataset.map(
        preprocess_function,
        batched=True,
        num_proc=4
    )

    # 5. Training configuration
    training_args = TrainingArguments(
        output_dir="./models/qwen2.5-7b-finetuned",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        warmup_steps=100,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        fp16=True,
        gradient_checkpointing=True,
    )

    # 6. Train
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    trainer.train()

    # 7. Save
    model.save_pretrained("./models/qwen2.5-7b-finetuned")
    tokenizer.save_pretrained("./models/qwen2.5-7b-finetuned")

if __name__ == "__main__":
    fine_tune_qwen()
```

---

## Faza 6: VALIDATION & TESTING

### 6.1 Evaluation Metrics

```python
def evaluate_model(model, test_dataset):
    metrics = {
        "action_type_accuracy": 0.0,      # Corect action type?
        "argument_accuracy": 0.0,         # Corect args?
        "summary_bleu": 0.0,              # Text quality?
        "compliance_score": 0.0,          # Domain knowledge?
        "latency_ms": 0.0,
        "perplexity": 0.0
    }

    for example in test_dataset:
        # Test model
        output = model.predict(example["input"])

        # Compare with expected
        metrics["action_type_accuracy"] += (
            output["action_type"] == example["output"]["action_type"]
        ) / len(test_dataset)

        # Add more metrics...

    return metrics
```

### 6.2 A/B Testing

```
Baseline (qwen2.5:7b original):
  - Test on 20 domain-specific queries
  - Measure: accuracy, latency, clarity

Fine-tuned (qwen2.5:7b-finetuned):
  - Same 20 queries
  - Measure improvement %

Example comparison:
Query: "Gaseste textele cu BI.1 in desen"

Baseline:
  ❌ Wrong: Searching in blocks, not texts
  Response: "0 blocuri contin BI.1"

Fine-tuned:
  ✅ Correct: Search in texts first
  Response: "4 texte contin BI.1"
```

---

## Faza 7: INTEGRATION WITH OLLAMA

### 7.1 Deploy Fine-Tuned Model to Ollama

```bash
# 1. Export to GGUF format (optimized for Ollama)
python scripts/export_to_gguf.py

# 2. Create Modelfile
cat > Modelfile.finetuned << 'EOF'
FROM ./models/qwen2.5-7b-finetuned.gguf

SYSTEM """
You are a CAD planning assistant specialized in fire safety systems.
You understand:
- EN 54 standards for fire detection and alarm systems
- Block naming (FA-D1, FA-B1, etc.)
- Text patterns (BI.1.1, BI.2.1, etc.)
- Layer organization in AutoCAD
- Compliance requirements

When asked about drawings:
1. Search texts FIRST for patterns
2. Then check blocks for definitions
3. Consider layers and relationships
4. Provide actionable results
"""

PARAMETER temperature 0.1
PARAMETER top_k 40
PARAMETER top_p 0.9
EOF

# 3. Create Ollama model
ollama create qwen2.5-7b-finetuned-incendiu -f Modelfile.finetuned

# 4. Test
ollama run qwen2.5-7b-finetuned-incendiu "Gaseste textele cu BI.1"

# 5. Update server to use new model
# Edit: ai-server/ollama_client.py
# Change: model="Qwen/Qwen2.5-7B-Instruct"
# To: model="qwen2.5-7b-finetuned-incendiu"
```

---

## TIMELINE ESTIMATE

| Faza                        | Timp           | Effort                                  |
| --------------------------- | -------------- | --------------------------------------- |
| 1. Colectare date           | 2-3 zile       | Mediu (70% automat)                     |
| 2. Annotation manual        | 3-5 zile       | Ridicat (require subject matter expert) |
| 3. Dataset validation       | 1-2 zile       | Mediu (automated checks)                |
| 4. Setup fine-tuning        | 1 zi           | Mic                                     |
| 5. Training                 | 4-8 ore        | Dependent pe hardware                   |
| 6. Validation               | 1-2 zile       | Mediu                                   |
| 7. Integration & deployment | 1 zi           | Mic                                     |
| **TOTAL**                   | **12-16 zile** | -                                       |

---

## HARDWARE REQUIREMENTS

```
Minimum:
- GPU: 8GB VRAM (NVIDIA RTX 3060 / RTX 4060)
- RAM: 32GB system RAM
- Storage: 50GB SSD

Recommended:
- GPU: 24GB VRAM (RTX 4090 / A100)
- RAM: 64GB system RAM
- Storage: 100GB NVMe SSD
```

---

## NEXT STEPS

### Immediate (Today):

- [ ] Create directory structure: E:\Ai agent\fine-tuning\
- [ ] Start collecting payload pairs (target: 20-30 pairs)
- [ ] Download EN 54 legislation (2-3 standards)

### Week 1:

- [ ] Generate training examples from payloads
- [ ] Extract domain knowledge from legislation
- [ ] Create annotation guidelines
- [ ] Annotate 50-100 examples manually

### Week 2:

- [ ] Validate dataset quality
- [ ] Setup fine-tuning environment
- [ ] Run first training iteration (small dataset)
- [ ] Evaluate baseline metrics

### Week 3-4:

- [ ] Scale training to full dataset (150-300 examples)
- [ ] A/B testing vs baseline model
- [ ] Fine-tune hyperparameters based on results
- [ ] Export to GGUF and integrate with Ollama

---

## SUCCESS CRITERIA

✅ Model should achieve:

- 85%+ accuracy on domain-specific queries
- 50%+ improvement vs baseline on fire safety tasks
- <500ms latency per request
- Clear, actionable responses with entity details

Example success case:

```
Input: "Gaseste textele cu BI.1 in desen"
Output:
{
  "action_type": "find_entities",
  "args": {"entity_type": "text", "text_contains": "BI."},
  "summary": "Identific 4 texte care contin 'BI.1': BI.1.1, BI.1.2, BI.1.3, BI.1.4",
  "entities_found": [
    {"handle": "2E85D0", "value": "BI.1.1", "layer": "GRINZI"},
    ...
  ]
}
```
