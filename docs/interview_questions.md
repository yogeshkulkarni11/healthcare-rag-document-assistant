# Interview Questions

## 1. Why is this advanced RAG rather than basic RAG?
It adds query rewriting, metadata-aware retrieval, relevance filtering, and a more explicit evidence-to-answer safety boundary.

## 2. Why rewrite a query?
Users may use abbreviations or incomplete wording. Expansion improves semantic retrieval without requiring the original document to contain the exact phrase.

## 3. Why metadata?
Metadata enables filtering by topic, source, document type, department, date, or other business dimensions.

## 4. Why relevance filtering?
Top-K alone can return weak matches. A relevance threshold reduces unsupported context reaching the LLM.

## 5. Why not fine-tune?
For changing enterprise knowledge, RAG is usually easier to update because the knowledge source can be refreshed without retraining the model.

## 6. How would you productionize this?
Use Azure Blob/ADLS, Azure AI Search hybrid/vector search, Azure OpenAI, managed identity, Key Vault, observability, evaluation, access control, audit logging, and PHI/security controls.

## 7. What would you evaluate?
Retrieval precision/recall, groundedness, citation correctness, answer relevance, latency, token usage, refusal quality, and safety.
