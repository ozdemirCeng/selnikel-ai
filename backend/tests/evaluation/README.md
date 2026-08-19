# Selnikel AI — RAG & Retrieval Evaluation Suite

This directory contains the ground truth dataset and evaluation harness for measuring RAG quality across:
1. **Context Relevance (Retrieval Precision)**: Are retrieved chunks containing the required answer?
2. **Citation Accuracy**: Does the system cite the exact expected document and page number?
3. **Answer Faithfulness (Groundedness)**: Does the generated answer match ground truth facts without hallucination?

## Dataset Format (`questions.json`)
Each evaluation sample contains:
- `id`: Unique identifier
- `category`: Domain area (`boiler_specifications`, `burner_maintenance`, `engineering_standards`, etc.)
- `question`: Real engineer query
- `expected_document`: Target filename expected to contain the source facts
- `expected_page`: Specific page number in the source PDF
- `expected_keywords`: Key technical terms/numbers required in retrieved chunks
- `ground_truth_answer`: Verified engineering answer
