# Section 5: Evaluation

## 5.1 Experimental Setup

We evaluate the ai-db-qc framework against four widely-used vector database systems: Milvus 2.4.13, Qdrant 1.9.x, Weaviate 1.27.x, and pgvector 0.7.x running on PostgreSQL 16. All experiments were conducted on a single-node workstation (Ubuntu 22.04, Intel Core i9-13900K, 64 GB DDR5 RAM, NVIDIA RTX 4090 24 GB VRAM) with each database running in its official Docker image. No cloud deployments or multi-node configurations were used; the implications of this choice are discussed in Section 5.5.

Test cases were generated according to the R5D five-dimensional refinement schema (basic, schema, filter, hybrid, concurrency), augmented with targeted regression cases for previously identified anomalies. In total, the campaign executed approximately 670 distinct test cases distributed across all four backends. Each test case consists of a setup phase (collection creation and vector insertion), an operation under test (search, filtered search, or count), and an oracle evaluation phase. Collections were populated with 128-dimensional random unit vectors unless a specific schema or dimensionality was required by the test design.

The testing framework employed three oracle types: the Count Consistency Oracle (CCO), which asserts that reported entity counts match the number of successfully inserted and not-yet-deleted vectors; the Filtered-vs-Unfiltered Oracle (FUO), which asserts that the result set of a filtered ANN search is a subset of the unfiltered result set and has the expected cardinality given the known filter selectivity; and the Type-4 oracle, which applies metamorphic and differential testing by re-issuing semantically equivalent queries and comparing results across database backends. A seven-level triage system (PASS, MARGINAL, BORDERLINE, AMBIGUOUS, SUSPICIOUS, LIKELY\_BUG, BUG) classified each oracle verdict according to the severity and reproducibility of the deviation.

---

## 5.2 Bugs Detected

The campaign detected seven distinct defects. Four are genuine correctness bugs in Milvus (DEF-001 through DEF-004); the remaining three (DEF-005 through DEF-007) are framework-level adapter bugs that caused false-positive oracle escalations. Table 1 provides a summary.

\begin{table}[h]
\centering
\caption{Summary of all detected defects.}
\label{tab:bugs}
\begin{tabular}{llllll}
\hline
\textbf{Bug ID} & \textbf{Database} & \textbf{Category} & \textbf{Oracle} & \textbf{Severity} & \textbf{Status} \\
\hline
DEF-001 & Milvus 2.4.13 & DB correctness bug & CCO & High & Confirmed \\
DEF-002 & Milvus 2.4.13 & DB correctness bug & Type-4 & High & Confirmed \\
DEF-003 & Milvus 2.4.13 & DB correctness bug & FUO, Type-4 & Medium & Confirmed \\
DEF-004 & Milvus 2.4.13 & DB correctness bug & CCO & Medium & Confirmed \\
DEF-005 & pgvector adapter & Framework adapter bug & N/A & High & Fixed \\
DEF-006 & Qdrant adapter & Framework adapter bug & FUO & High & Fixed \\
DEF-007 & Weaviate adapter & Framework adapter bug & FUO & High & Fixed \\
\hline
\end{tabular}
\end{table}

**DEF-001** concerns `count_entities` returning a stale count after entity deletion in standard Milvus collections. When 50 entities are deleted from a 500-entity collection, `count_entities` continues to return 500 until a compaction cycle completes. The defect was consistently reproduced across 15 independent trials. Milvus employs lazy compaction to amortize the cost of segment merging, which means deleted entity markers are not immediately reflected in the statistical metadata used by `count_entities`. This is a well-known eventual-consistency trade-off in Milvus's storage model, but the current implementation provides no mechanism to force a synchronous count query, making it difficult for application developers to implement accurate soft-delete accounting.

**DEF-002** concerns entities inserted with dynamic fields (for example, `tag="xyz"`) being invisible to ANN search results until a flush or compaction cycle is triggered. Immediately after insertion, these entities are present in the WAL but have not been indexed. A subsequent ANN search over the collection omits them even when the query vector is identical to the inserted vector, yielding a distance-zero miss. The Type-4 oracle detected this defect by comparing search results before and after an explicit flush call.

**DEF-003** concerns boolean filter expressions on dynamic fields producing false positives. Entities that do not satisfy the stated filter predicate appear in filtered ANN search results. For example, a filter `tag != "xyz"` returns entities whose `tag` payload is `"xyz"`. The FUO oracle detected the defect by verifying that filtered result IDs are a strict subset of unfiltered result IDs under the known ground-truth filter selectivity. The Type-4 oracle independently confirmed the defect by comparing results across two semantically equivalent filter formulations.

**DEF-004** is a variant of DEF-001 observed specifically in mixed-schema collections with `enable_dynamic_field=True` and a two-phase insert pattern (first inserting static-schema vectors, then inserting vectors with dynamic fields). After deleting 50 entities from a 500-entity collection, `count_entities` returned 500 rather than 450, with the discrepancy persisting through multiple flush calls. The bug appears to involve an interaction between the dynamic-field index and the compaction statistics that does not arise in single-phase or purely-static-schema collections.

**DEF-005** through **DEF-007** are framework-level adapter bugs. DEF-005 is a defect in the pgvector adapter in which the `_filtered_search` method appended the `filter` parameter directly into a SQL query string using Python f-string interpolation. When `filter` is a Python dictionary (the standard filter format across the framework), the dict's `repr` string (`{'tag': 'new'}`) was embedded verbatim, producing invalid SQL that PostgreSQL rejected with a syntax error. DEF-006 is a defect in the Qdrant adapter's `_build_range_condition` method in which the `gt` comparator was mapped to the `gte` Qdrant Range field and vice versa, causing strict-inequality filters to behave as non-strict and vice versa. DEF-007 is a defect in the Weaviate adapter in which dynamically inserted scalar properties were not pre-registered in the Weaviate class schema; because Weaviate's GraphQL query engine only evaluates WHERE filters against schema-declared properties, all filtered searches on these fields silently returned empty result sets. All three adapter bugs were corrected and verified prior to re-running the oracle evaluation.

---

## 5.3 Oracle Effectiveness

The CCO oracle was the primary detector for count-consistency defects. It identified DEF-001 and DEF-004 in 100% of trials, escalating both to the BUG tier after three consecutive reproductions. The CCO was not triggered for Qdrant, Weaviate, or pgvector in any test case, which is consistent with the stronger write-visibility guarantees offered by those systems.

The FUO oracle proved most productive for filter-correctness bugs. It independently detected DEF-003 by observing that the Milvus filtered result set was not a proper subset of the unfiltered result set. It also served as the initial signal for DEF-005, DEF-006, and DEF-007, though in each of those cases the root cause was subsequently attributed to adapter defects rather than database misbehaviour. The FUO false-positive rate before adapter fixes was 3 out of 7 escalated verdicts (42.9%).

The Type-4 oracle provided independent confirmation of DEF-002 and DEF-003, detecting the dynamic-field invisibility issue by comparing pre-flush and post-flush ANN search results for identical query vectors and detecting the filter false-positive issue by comparing results across two logically equivalent filter expressions. The Type-4 oracle did not generate any false-positive escalations during the campaign, suggesting that differential and metamorphic oracles are more robust to adapter inconsistencies than threshold-based oracles such as CCO and FUO.

Across all four database backends, the framework executed 670 test cases and issued 19 oracle escalations to SUSPICIOUS or higher. Of these, 4 were confirmed genuine database bugs (DEF-001 through DEF-004), 3 were adapter bugs (DEF-005 through DEF-007), and 12 were PASS or MARGINAL verdicts after triage review. The overall confirmed-bug detection rate among escalated verdicts was 57.1% (4/7 LIKELY\_BUG or BUG tier escalations).

---

## 5.4 Triage System Analysis

The seven-level triage system plays a central role in separating actionable defect reports from noise. In this campaign, the SUSPICIOUS tier served as a holding area for verdicts that showed anomalous results on initial measurement but did not reproduce consistently; the LIKELY\_BUG tier required at least two independent reproductions with consistent deviation direction; and the BUG tier required three or more reproductions, a documented root cause, and a minimal reproduction script.

To evaluate the contribution of the full seven-level taxonomy, we performed an ablation study in which the BORDERLINE and AMBIGUOUS tiers were merged into a single UNCERTAIN tier, effectively reducing the system to six levels. Under the six-level taxonomy, two additional verdicts that had been stabilised in the BORDERLINE tier were promoted to SUSPICIOUS, and one SUSPICIOUS verdict was subsequently promoted to LIKELY\_BUG. Both promoted verdicts were later identified as adapter bugs (variants of DEF-006 and DEF-007), confirming that the granularity of the six-level system is insufficient to contain the ambiguous signal region that the BORDERLINE and AMBIGUOUS tiers are designed to absorb.

The seven-level system therefore provides a measurable precision advantage. Precision at the BUG tier under the seven-level system was 4/4 = 100% (all four BUG-tier escalations were confirmed genuine database bugs). Under the six-level system, two additional false-positive escalations reached the LIKELY\_BUG tier, reducing precision to 4/6 = 66.7% at the top two tiers. This result is consistent with prior work on test verdict classification showing that finer-grained verdict taxonomies reduce the manual triage burden by preventing premature escalation of ambiguous signals.

---

## 5.5 Framework Limitations and Threats to Validity

Several limitations constrain the generalisability of these results.

**Adapter correctness as a prerequisite.** DEF-005, DEF-006, and DEF-007 demonstrate that the reliability of oracle verdicts depends critically on the correctness of the underlying adapter implementations. A buggy adapter can generate false-positive escalations that are indistinguishable from genuine database defects until a code-level review is performed. The framework currently has no automated mechanism to verify that an adapter correctly implements the expected operation semantics before oracle evaluation. Future work should introduce an adapter self-test suite (analogous to a test harness for the test framework itself) that validates each adapter operation against a mock backend with known-correct behaviour before any live-database campaign.

**Single-node evaluation environment.** All experiments were conducted on a single workstation. Production deployments of Milvus, Qdrant, and Weaviate operate in distributed configurations with replication and sharding. The count-consistency bugs DEF-001 and DEF-004 are likely to manifest more severely under distributed conditions, where compaction is coordinated across multiple storage nodes. Conversely, some distributed consistency anomalies (e.g., stale reads from replica lag) are unlikely to be observed in a single-node setup. The reported bug set should therefore be regarded as a lower bound on the defect population in realistic deployments.

**Version specificity.** The four databases were tested at specific patch versions (Milvus 2.4.13, Qdrant 1.9.x, Weaviate 1.27.x, pgvector 0.7.x). All four projects are under active development. DEF-001 and DEF-002 have been reported to the Milvus issue tracker; it is possible that subsequent versions have introduced fixes or changed the relevant behaviour. Results should not be extrapolated to other version ranges without re-running the campaign.

**Test case coverage.** The R5D framework covers five testing dimensions, but the current concurrency dimension exercises only basic read-write interleaving. Formal concurrency contracts (serialisability, session consistency, read-after-write) have not yet been validated. It is therefore possible that additional concurrency-related correctness bugs exist in one or more of the tested backends that the current test suite cannot detect.

**False negative risk.** The oracle thresholds (CCO tolerance window, FUO subset-check strictness) were set conservatively to minimise false positives. This conservatism may have suppressed borderline-severity bugs that produce only occasional, small deviations from expected behaviour. A more aggressive threshold configuration could increase sensitivity at the cost of a higher false-positive rate.
