"""Questions to the knowledge graph, answered by a local small language model (SDD §6.15, 2026-11-20).

- index.py: the passages (item cards, text chunks, entities, communities, ideas, glossary) with their vectors
  and the full-text index, all inside the SQLite store, so a copy of `insight.db` is the whole index;
- retrieve.py: the hybrid retrieval (dense + BM25 + personalized PageRank over the entity graph + direct
  mentions, fused by reciprocal rank and reranked by a cross-encoder) and the facts computed from the graph;
- answer.py: the SLM behind an OpenAI-compatible endpoint (Ollama, llama.cpp, LM Studio, vLLM) and the checks
  on what it wrote (citations that exist, numbers that are in the sources)."""
