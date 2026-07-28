# RAG Knowledge Base

This folder is indexed automatically by the AI server retriever.

## What to place here

- Romanian fire safety legislation notes in Markdown
- Block catalog descriptions and symbol conventions
- Internal project procedures and validation rules
- Normalized extracts from PDFs (optional)

Supported formats:

- .md
- .txt
- .json
- .csv
- .log
- .pdf

## Recommended structure

- legislation/
- symbols/
- procedures/
- examples/

## Workflow

1. Add or update files.
2. Reindex:
   - POST /rag/reindex
3. Test retrieval:
   - GET /rag/search?q=detector%20fum%20P118&k=4

## Notes

- The planner injects retrieved snippets into prompt under KNOWLEDGE_BASE_CONTEXT.
- If no relevant chunks are found, planning still works from DWG context and conversation history.
