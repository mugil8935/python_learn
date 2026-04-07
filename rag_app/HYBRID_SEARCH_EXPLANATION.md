# Hybrid Search Implementation: RRF (Reciprocal Rank Fusion)

## Overview

Your RAG chatbot now uses **Hybrid Search** combining **text search** and **vector (semantic) search** with **Reciprocal Rank Fusion (RRF)** to provide the most accurate results.

Why Hybrid? Because:
- **Text search** excels at matching exact keywords and phrases
- **Vector search** excels at understanding meaning and context
- Together = best of both worlds

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Query                           │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ├─────────────────────────┬──────────────────┐
                 ▼                         ▼                  ▼
        ┌─────────────────┐      ┌──────────────────┐   ┌──────────────┐
        │ Generate        │      │ Get              │   │              │
        │ Embedding       │      │ Query Vector     │   │              │
        │ (OpenAI)        │      │                  │   │              │
        └────────┬────────┘      └────────┬─────────┘   │              │
                 │                         │             │              │
                 └────────────────────┬────┘             │              │
                                      │                 │              │
        ┌───────────────────────────┬─┴──────────────────┼──────────┐   │
        │                           │    Elasticsearch   │          │   │
        ▼                           ▼                    ▼          ▼   ▼
    ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ Text Search     │   │ Vector Search    │   │                  │
    │ (Match Query)   │   │ (KNN)            │   │                  │
    │                 │   │                  │   │                  │
    │ Returns:        │   │ Returns:         │   │                  │
    │ Rank 1, 2, 3... │   │ Rank 1, 2, 3...  │   │                  │
    └────────┬────────┘   └────────┬─────────┘   │                  │
             │                     │             │                  │
             └─────────────┬───────┘             │                  │
                           │                     │                  │
                    ┌──────▼──────────────────────┴──────────────┐   │
                    │  RRF (Reciprocal Rank Fusion)             │   │
                    │  Combines results intelligently            │   │
                    │  result_score = 1/(k + rank_text)         │   │
                    │                + 1/(k + rank_vector)      │   │
                    │  (k = 60 by default)                      │   │
                    └──────┬────────────────────────────────────┘   │
                           │                                        │
                    ┌──────▼────────────────────────────────────┐   │
                    │ Merged & Ranked Results                  │   │
                    │ Top N documents with RRF scores          │   │
                    └───────────────────────────────────────────┘   │
                                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## How RRF Works

### The Problem with Simple Score Combination
If you just add text search scores + vector search scores:
- Issue: Scores are on different scales (0-100 vs 0-1)
- Issue: One method might dominate the other
- Result: Unpredictable, inconsistent ranking

### The RRF Solution
RRF uses **rank positions** instead of raw scores:

```
RRF Score = 1/(k + rank)

Where:
  k = 60 (constant, prevents division by zero)
  rank = position in result list (1, 2, 3, ...)
```

**Example:**
```
Text Search Results:        Vector Search Results:
Rank 1: Doc A (score: 85)   Rank 1: Doc E (score: 0.92)
Rank 2: Doc B (score: 72)   Rank 2: Doc A (score: 0.88)
Rank 3: Doc C (score: 68)   Rank 3: Doc B (score: 0.85)

RRF Calculation:
Doc A: 1/(60+1) + 1/(60+2) = 0.01639 + 0.01613 = 0.03252  ← Best!
Doc B: 1/(60+2) + 1/(60+3) = 0.01613 + 0.01587 = 0.03200
Doc E: 1/(60+1)           = 0.01639

Final Ranking:
1. Doc A (0.03252) - Won because it ranked well in BOTH searches
2. Doc B (0.03200)
3. Doc E (0.01639) - Only in vector search
4. Doc C (0.01587) - Only in text search
```

### Why RRF is Better
✓ **Scale-invariant**: Ranks don't depend on score magnitude
✓ **Robust**: One outlier doesn't dominate
✓ **Proven**: Used by Google, Twitter, and academia
✓ **Intuitive**: Combines voting from different signals
✓ **Stable**: Consistent results across different query types

---

## Implementation Details

### Step 1: Text Search
```python
# Match query terms in text field
{
    "query": {
        "match": {
            "text": {
                "query": query,           # "What is machine learning?"
                "fuzziness": "AUTO"       # Handles typos
            }
        }
    },
    "size": num_results * 2  # Get extra to merge with vector results
}
```

**Tuning:**
- `fuzziness: AUTO` - tolerates misspellings
- `operator: or` - matches ANY term (or "and" for ALL terms)
- `boost` - increase weight of text search (not used in current RRF)

### Step 2: Vector Search
```python
# Semantic similarity using embeddings
{
    "query": {
        "knn": {
            "field": "embedding",        # Vector field
            "query_vector": embedding,   # Query embedding
            "k": num_results * 2        # Get top k similar
        }
    }
}
```

**Fallback chain:**
1. Try native KNN (Elasticsearch 8.0+)
2. If fails, use cosineSimilarity script
3. Both find semantically similar documents

### Step 3: RRF Combination
```python
def _apply_reciprocal_rank_fusion(text_results, vector_results, rrf_k=60):
    combined = {}
    rrf_scores = {}
    
    # Score text search results
    for rank, hit in enumerate(text_results['hits']['hits'], 1):
        doc_id = hit['_id']
        rrf_score = 1.0 / (rrf_k + rank)
        combined[doc_id] = hit
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
    
    # Add vector search results (also adds their RRF scores)
    for rank, hit in enumerate(vector_results['hits']['hits'], 1):
        doc_id = hit['_id']
        rrf_score = 1.0 / (rrf_k + rank)
        if doc_id not in combined:
            combined[doc_id] = hit
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
    
    # Sort by combined RRF scores
    sorted_docs = sorted(rrf_scores.items(), 
                        key=lambda x: x[1], reverse=True)
    return sorted_docs, combined
```

---

## Configuration & Tuning

### Adjustable Parameters

**1. RRF k value** (currently 60)
```python
# In _apply_reciprocal_rank_fusion
rrf_k = 60  # Increase for smoother results, decrease for sharper ranking
```

Effects:
- Higher k (e.g., 100) → documents need better ranks to win
- Lower k (e.g., 40) → strong ranks matter more

**2. Result multiplier** (currently 2x)
```python
# In retrieve_context
"size": num_results * 2  # Fetch 2x to merge with other method
```

Effects:
- Higher multiplier → more diverse results, better merged ranking
- Lower multiplier → faster, but loses some documents

**3. Text search fuzziness**
```python
"fuzziness": "AUTO"  # Typo tolerance
```

Options: "AUTO", "0", "1", "2"

### Performance Optimization

Current approach gets `num_results * 2` from each method:
- For `num_results=10`: 20 text results + 20 vector results
- Return top 10 after RRF merge
- Balances quality and performance

---

## Search Quality Comparison

### Before (Vector Only)
```
Query: "How do neural networks work?"

Results: Only semantic matches
- Doc with embeddings similar to query
- Misses documents with exact keyword matches
- Sometimes too narrow (doesn't find "deep learning")
```

### After (Hybrid + RRF)
```
Query: "How do neural networks work?"

Results: Smart combination
✓ Semantic matches (from vector search)
✓ Exact keyword matches (from text search)
✓ "neural" + "networks" exact phrase matches
✓ Misspellings tolerated ("neural network" vs "neurel netowrk")
✓ Related concepts ranked higher
```

---

## Error Handling & Fallbacks

The implementation includes intelligent fallbacks:

```
1. Try Hybrid Search (Text + Vector with RRF)
         ↓ (if fails)
2. Try Native KNN only
         ↓ (if fails)
3. Try CosineSimilarity script
         ↓ (if fails)
4. Return empty results + error log
```

Each fallback is logged, so you can see what worked.

---

## Logging

All operations are logged for debugging:

```
INFO - Retrieving context for query: 'What is AI?'
INFO - Step 1: Performing text-based search...
INFO - Text search returned 18 results
INFO - Step 2: Performing vector-based search...
INFO - Vector search (KNN) returned 20 results
INFO - Step 3: Combining results with Reciprocal Rank Fusion...
DEBUG - Text result rank 1: doc_abc (RRF: 0.016393)
DEBUG - Vector result rank 1: doc_xyz (RRF: 0.016393)
DEBUG - Final result (RRF: 0.032787, ES: 0.95): Row 42
INFO - [OK] Hybrid search (RRF) retrieved 10 documents
```

Look at `chatbot.log` for complete trace.

---

## Result Structure

Each retrieved document includes:
```python
{
    "text": "...",              # Document content
    "row_id": 42,               # Source row ID
    "chunk_index": 0,           # Chunk number
    "score": 0.95,              # Elasticsearch score
    "rrf_score": 0.032787       # Combined RRF score
}
```

The `rrf_score` shows how well the document scored across both text and vector searches.

---

## Metrics & Evaluation

To measure search quality:

1. **Coverage**: Are relevant documents being found?
2. **Rank quality**: Do best documents rank highest?
3. **Speed**: Response time acceptable?

Current metrics logged:
- Results returned by each method
- RRF scores for each result
- Elasticsearch scores for comparison

---

## Further Optimizations

Possible future improvements:

1. **Weighted RRF**: Give more weight to one signal
   ```python
   rrf_score = 2.0/(k+rank_text) + 1.0/(k+rank_vector)
   ```

2. **Normalization**: Normalize to 0-1 range for blending

3. **BM25 tuning**: Optimize Elasticsearch BM25 parameters

4. **Query expansion**: Use synonyms for text search

5. **Learning to Rank**: ML model to learn best weights

---

## Summary

| Aspect | Details |
|--------|---------|
| **Why Hybrid?** | Text + Vector = complete retrieval |
| **Why RRF?** | Combines ranks intelligently, robust, proven |
| **Benefits** | Better accuracy, more diverse results |
| **Performance** | ~2x Elasticsearch queries per search |
| **Fallbacks** | Handles failures gracefully |
| **Configuration** | Tunable k, multiplier, fuzziness |

Your chatbot now has production-ready search that beats single-method approaches! 🚀
