# Multi-DB Differential Campaign Report

**Run ID**: multidb-diff-20260317-113458  
**Date**: 2026-03-17 11:35:09  
**Databases**: qdrant, weaviate, pgvector  
**Vectors**: 300 × dim=64  

## Contract Status Matrix

| Contract | qdrant | weaviate | pgvector |
|----------|---------|---------|---------|
| R1A | PASS + | PASS + | PASS + |
| R1B | PASS + | PASS + | PASS + |
| R2A | PASS + | PASS + | PASS + |
| R2B | PASS + | PASS + | PASS + |
| R3A | PASS + | PASS + | PASS + |
| R3B | PASS + | PASS + | PASS + |

## Divergences (0 found)

_No divergences found — all databases agree on all contracts._

## Per-Database Detail

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

- **R1A** [PASS]  
- **R1B** [PASS]  top10 subset of top20
- **R2A** [PASS]  impossible filter returned empty result
- **R2B** [PASS]  search returned 10/10 results
- **R3A** [PASS]  
- **R3B** [PASS]  

## Summary

| Database | PASS | VIOLATION | SKIP |
|----------|------|-----------|------|
| qdrant | 6 | 0 | 0 |
| weaviate | 6 | 0 | 0 |
| pgvector | 6 | 0 | 0 |