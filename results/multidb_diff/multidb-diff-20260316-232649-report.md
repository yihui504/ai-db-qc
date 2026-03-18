# Multi-DB Differential Campaign Report

**Run ID**: multidb-diff-20260316-232649  
**Date**: 2026-03-16 23:27:09  
**Databases**: milvus, qdrant, weaviate, pgvector  
**Vectors**: 1000 × dim=128  

## Contract Status Matrix

| Contract | milvus | qdrant | weaviate | pgvector |
|----------|---------|---------|---------|---------|
| R1A | PASS + | PASS + | PASS + | PASS + |
| R1B | PASS + | PASS + | PASS + | PASS + |
| R2A | SKIP | PASS + | PASS + | PASS + |
| R2B | PASS + | PASS + | PASS + | PASS + |
| R3A | PASS + | PASS + | PASS + | PASS + |
| R3B | VIOLATION ! | PASS + | PASS + | PASS + |

## Divergences (1 found)

- **R3B**: milvus=VIOLATION, qdrant=PASS, weaviate=PASS, pgvector=PASS

## Per-Database Detail

### milvus

- **R1A** [PASS]  
- **R1B** [PASS]  top20 subset of top40
- **R2A** [SKIP]  filter not supported: <MilvusException: (code=1100, message=failed to create query plan: cannot parse 
- **R2B** [PASS]  search returned 20/20 results
- **R3A** [PASS]  
- **R3B** [VIOLATION]  count 1000 != expected 980

### qdrant

- **R1A** [PASS]  
- **R1B** [PASS]  top20 subset of top40
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 20/20 results
- **R3A** [PASS]  
- **R3B** [PASS]  

### weaviate

- **R1A** [PASS]  
- **R1B** [PASS]  top20 subset of top40
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 20/20 results
- **R3A** [PASS]  
- **R3B** [PASS]  

### pgvector

- **R1A** [PASS]  
- **R1B** [PASS]  top20 subset of top40
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 20/20 results
- **R3A** [PASS]  
- **R3B** [PASS]  

## Summary

| Database | PASS | VIOLATION | SKIP |
|----------|------|-----------|------|
| milvus | 4 | 1 | 1 |
| qdrant | 6 | 0 | 0 |
| weaviate | 6 | 0 | 0 |
| pgvector | 6 | 0 | 0 |