# Multi-DB Differential Campaign Report

**Run ID**: multidb-diff-20260316-232329  
**Date**: 2026-03-16 23:23:51  
**Databases**: milvus, qdrant, weaviate, pgvector  
**Vectors**: 500 × dim=64  

## Contract Status Matrix

| Contract | milvus | qdrant | weaviate | pgvector |
|----------|---------|---------|---------|---------|
| R1A | PASS + | PASS + | PASS + | VIOLATION ! |
| R1B | PASS + | PASS + | PASS + | PASS + |
| R2A | SKIP | PASS + | PASS + | PASS + |
| R2B | PASS + | PASS + | PASS + | PASS + |
| R3A | PASS + | PASS + | PASS + | PASS + |
| R3B | VIOLATION ! | PASS + | PASS + | PASS + |

## Divergences (2 found)

- **R1A**: milvus=PASS, qdrant=PASS, weaviate=PASS, pgvector=VIOLATION
- **R3B**: milvus=VIOLATION, qdrant=PASS, weaviate=PASS, pgvector=PASS

## Per-Database Detail

### milvus

- **R1A** [PASS]  
- **R1B** [PASS]  top10 subset of top20
- **R2A** [SKIP]  filter not supported: <MilvusException: (code=1100, message=failed to create query plan: cannot parse 
- **R2B** [PASS]  search returned 10/10 results
- **R3A** [PASS]  
- **R3B** [VIOLATION]  count 500 != expected 480

### qdrant

- **R1A** [PASS]  
- **R1B** [PASS]  top10 subset of top20
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 10/10 results
- **R3A** [PASS]  
- **R3B** [PASS]  

### weaviate

- **R1A** [PASS]  
- **R1B** [PASS]  top10 subset of top20
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 10/10 results
- **R3A** [PASS]  
- **R3B** [PASS]  

### pgvector

- **R1A** [VIOLATION]  recall 0.185 < 0.7
- **R1B** [PASS]  top10 subset of top20
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 10/10 results
- **R3A** [PASS]  
- **R3B** [PASS]  

## Summary

| Database | PASS | VIOLATION | SKIP |
|----------|------|-----------|------|
| milvus | 4 | 1 | 1 |
| qdrant | 6 | 0 | 0 |
| weaviate | 6 | 0 | 0 |
| pgvector | 5 | 1 | 0 |