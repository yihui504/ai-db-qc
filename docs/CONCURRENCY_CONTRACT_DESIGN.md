# Concurrency Contract Design for ai-db-qc

**Version:** 1.0  
**Date:** 2026-03-17  
**Author:** ai-db-qc framework team  

---

## 1. Background and Motivation

Vector databases are increasingly deployed in high-concurrency production environments where
multiple clients simultaneously write, update, and query the same collection. Despite this,
the correctness of these systems under concurrent workloads is poorly understood and rarely
tested by existing benchmark frameworks, which focus almost exclusively on sequential
single-client scenarios.

The CAP theorem establishes that a distributed data store cannot simultaneously guarantee
Consistency, Availability, and Partition tolerance. In practice, the four systems tested by
ai-db-qc occupy different points on this spectrum:

- **pgvector (PostgreSQL)** provides strong consistency via MVCC and serialisable snapshot
  isolation. Write operations are immediately durable and visible to all subsequent reads on
  the same or other connections.
- **Qdrant** provides strong consistency for single-node deployments. The default write mode
  is synchronous; a successful `upsert` is immediately visible to reads.
- **Weaviate** provides strong consistency for single-node deployments with the default
  consistency level (`ONE`). Distributed configurations may exhibit stale reads.
- **Milvus** provides eventual consistency. Writes are first committed to a WAL/message broker
  (Pulsar/Kafka) and subsequently indexed. A flush operation is required to make new data
  visible to search, and compaction is an asynchronous background process.

These differences mean that concurrency contracts must be evaluated against database-specific
consistency guarantees rather than a universal baseline. The contracts defined below are
designed to be parameterisable: a PASS verdict on Milvus may require a flush call that is
not required on pgvector.

---

## 2. Concurrency Contract Specifications

### CONC-001: Write Isolation Contract

**Informal statement:** Concurrent writes from independent threads must not corrupt each
other's data. After all writers complete, the collection must contain exactly the union of
all inserted vectors.

**Precondition:** An empty collection `C` with dimension `d` exists.

**Test procedure:**
1. Launch $N_{w}$ writer threads. Thread $i$ inserts a disjoint batch of $B$ vectors with IDs
   in the range $[i \cdot B, (i+1) \cdot B)$ and scalar payload `{"writer_id": i}`.
2. All writers execute concurrently without explicit synchronisation.
3. After all writers complete, optionally trigger a flush (required for Milvus).
4. Issue `count_entities` and compare to $N_{w} \times B$.

**Oracle (CCO):**

$$\text{observed\_count} = N_w \times B$$

A deviation of more than $\epsilon_{\text{count}}$ (default: 0) triggers LIKELY\_BUG.
On Milvus, a temporary deviation before flush is expected (AMBIGUOUS); a persistent
deviation after flush is LIKELY\_BUG.

**Expected behaviour by database:**
| Database | Expected verdict | Notes |
|----------|-----------------|-------|
| pgvector | PASS | Strong consistency; count is exact immediately |
| Qdrant | PASS | Synchronous writes |
| Weaviate | PASS (single-node) | |
| Milvus | AMBIGUOUS before flush, PASS after flush | Lazy compaction |

---

### CONC-002: Batch Atomicity Contract

**Informal statement:** A batch insert operation is atomic: either all vectors in the batch
are persisted, or none are. No intermediate state (partial batch visible) should be observable
by concurrent readers.

**Precondition:** An empty collection `C` exists.

**Test procedure:**
1. One writer thread submits a single batch of $B_{\text{large}}$ vectors (default: 500).
2. While the writer is executing, $N_{r}$ reader threads continuously poll `count_entities`.
3. After the writer completes, record all `count_entities` values observed by readers.

**Oracle:**

The set of observed count values must contain only 0 and $B_{\text{large}}$. Any intermediate
value $0 < c < B_{\text{large}}$ indicates a partial-visibility violation:

$$\forall c \in \text{observed\_counts}: c = 0 \;\vee\; c = B_{\text{large}}$$

Violation → LIKELY\_BUG. Note that on Milvus, observed counts are expected to remain 0
until flush; the batch atomicity guarantee is evaluated post-flush.

**Expected behaviour by database:**
| Database | Expected verdict | Notes |
|----------|-----------------|-------|
| pgvector | PASS | Transaction-level atomicity |
| Qdrant | PASS | Batch upsert is atomic within a single shard |
| Weaviate | PASS | Batch object import is atomic |
| Milvus | PASS post-flush | Pre-flush count is 0 (not partial) |

---

### CONC-003: Read-After-Write Contract

**Informal statement:** After a successful write on a given connection (or immediately after
a flush for eventually-consistent backends), the written data must be retrievable by ANN search
using the exact same vector as the query.

**Precondition:** An empty collection `C` with dimension `d` exists.

**Test procedure (per trial):**
1. Generate a random unit vector $\mathbf{v}$ and a unique integer ID.
2. Insert $\mathbf{v}$ with ID. On Milvus, issue a flush immediately after.
3. Issue an ANN search with query $\mathbf{v}$ and top-$k = 1$.
4. Assert that the returned result has ID equal to the inserted ID and distance = 0.0
   (or $< \epsilon_{\text{dist}}$ for floating-point tolerance, default $10^{-6}$).
5. Repeat for $N_{\text{trials}}$ independent trials (default: 10).

**Oracle:**

$$\text{result}[0].\text{id} = \text{inserted\_id} \;\wedge\; \text{result}[0].\text{distance} < \epsilon_{\text{dist}}$$

Failure in any trial → LIKELY\_BUG.

**Expected behaviour by database:**
| Database | Expected verdict | Notes |
|----------|-----------------|-------|
| pgvector | PASS | Immediate read-after-write consistency |
| Qdrant | PASS | Immediate read-after-write consistency |
| Weaviate | PASS | Immediate read-after-write consistency |
| Milvus | PASS post-flush | Pre-flush: vector may be invisible (DEF-002) |

---

## 3. Known Limitations

1. **Single-node only.** These contracts were designed for and validated against single-node
   deployments. Distributed configurations may exhibit additional anomalies (replica lag,
   split-brain scenarios) not covered here.

2. **No linearisability testing.** The contracts above test eventual-consistency properties
   (final count, final visibility). They do not test linearisability or serializability in
   the sense of verifying that concurrent reads observe a consistent total order of writes.

3. **Milvus flush dependency.** CONC-001 and CONC-003 require an explicit flush on Milvus to
   produce meaningful verdicts. The flush latency is not measured and may vary across
   workload sizes.

4. **Race condition sensitivity.** CONC-002 relies on timing: if the batch insert completes
   faster than the reader thread's first `count_entities` call, no intermediate state will be
   observed. The test is probabilistic for very fast backends on low-latency hardware.
