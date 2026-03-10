# R6A-001 Campaign Plan

**Campaign ID**: R6A-001
**Campaign Name**: r6a_consistency_visibility
**Target Database**: Milvus
**Date**: 2026-03-10
**Status**: PLANNING

---

## Goal

Verify write visibility / query visibility / basic consistency semantics in Milvus v2.6.10. First slice focuses on deterministic, observable timing behaviors around insert, flush, load, and search operations.

---

## Contract Family

**Primary Family**: CONS

MVP Note: This campaign focuses on the CONS contract family.

---

## Campaign Scope

**Mode**: REAL
**Max Cases**: 6
**Runtime Budget**: 30m

**Required Operations**:
- create_collection
- insert
- flush
- load
- search
- count_entities

---

## TODO

- [ ] Define specific test cases
- [ ] Set up capability validation
- [ ] Define success criteria
