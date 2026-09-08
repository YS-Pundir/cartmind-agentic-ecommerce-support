# Nimbus Commerce RAG Triad Evaluation — Insights

## 1. Purpose

This report analyzes **Task 13: Evaluate with the RAG triad at scale** using the same 15-query test set under two evaluation strategies:

1. **`MOCK_LLM` judge evaluation** — the required capstone evaluation mode.
2. **Real-LLM judge evaluation** — an additional best-practice evaluation performed to obtain a second semantic-quality signal.

The three evaluated dimensions are **context relevance, groundedness, and answer relevance**, each scored on a 1–5 scale.

> **Evaluation status:** The `MOCK_LLM` results are the authoritative Task 13 results because the specification requires the LLM-as-judge prompt to run under `MOCK_LLM`. The real-LLM results are supplementary engineering evidence and do not replace the required evaluation.

---

## 2. Test-Set Coverage

The 15-query evaluation contains:

- **12 in-scope policy queries**, covering the required KB topics.
- **1 compound edge-case query**, combining several policy areas.
- **2 deliberately out-of-scope queries**, testing scope handling and hallucination resistance.

This composition provides coverage of normal retrieval, multi-policy reasoning, and unsupported/out-of-domain requests.

---

## 3. Executive Summary

| Strategy | Context Relevance | Groundedness | Answer Relevance | Overall |
|---|---:|---:|---:|---:|
| **Required `MOCK_LLM`** | **4.47/5** | **5.00/5** | **3.93/5** | **4.47/5** |
| **Real LLM judge** | **3.93/5** | **4.80/5** | **4.60/5** | **4.44/5** |

### Overall conclusion

The strongest characteristic of the RAG pipeline is **groundedness**. The system generally stays within retrieved knowledge-base evidence.

The main improvement opportunity is **answer completeness and synthesis**, particularly for questions containing multiple policy dimensions. The real-LLM evaluation makes this weakness more visible than the deterministic `MOCK_LLM` evaluation.

---

## 4. Required `MOCK_LLM` Evaluation

The explicit 1–5 query scores produce:

| Metric | Average |
|---|---:|
| Context relevance | **4.47/5** |
| Groundedness | **5.00/5** |
| Answer relevance | **3.93/5** |
| Overall | **4.47/5** |

The JSON result also records normalized aggregate values:

| Metric | Normalized value |
|---|---:|
| Context relevance | **0.6271** |
| Groundedness | **0.9360** |
| Answer relevance | **0.4768** |
| Overall | **0.6800** |

### 4.1 Groundedness is the strongest result

All 15 queries receive **5/5 groundedness** in the `MOCK_LLM` results.

This indicates that the generation stage is strongly constrained by retrieved evidence. Even when retrieval is incomplete or an answer is not fully responsive, the system does not appear to compensate by inventing unsupported policy information.

For a policy-support agent, this is a significant strength.

### 4.2 Retrieval is strong for direct policy questions

The 12 in-scope queries average **4.75/5** for context relevance.

The strongest cases occur when the question maps closely to a dedicated policy document containing the required information.

### 4.3 Answer relevance is the main quality gap

The 12 in-scope queries average **4.08/5** for answer relevance.

This is lower than the perfect groundedness score.

The result demonstrates an important RAG distinction:

> **A response can be grounded in the correct evidence while still being incomplete, repetitive, or insufficiently direct.**

The generated answers sometimes reproduce retrieved policy text rather than synthesizing the evidence into a concise customer-facing response.

---

## 5. Results by Query Type

| Query group | Context | Groundedness | Answer Relevance |
|---|---:|---:|---:|
| In-scope (1–12) | **4.75** | **5.00** | **4.08** |
| Edge case (13) | **5.00** | **5.00** | **5.00** |
| Out-of-scope (14–15) | **2.50** | **5.00** | **2.50** |

The out-of-scope queries show an important safety characteristic: when the requested information is not represented in the policy KB, the system does not need to hallucinate an answer in order to remain grounded.

---

## 6. Real-LLM Judge Evaluation

The supplementary real-LLM evaluation produces:

| Metric | Average |
|---|---:|
| Context relevance | **3.93/5** |
| Groundedness | **4.80/5** |
| Answer relevance | **4.60/5** |
| Overall | **4.44/5** |

The real-LLM evaluation should be interpreted as an **additional quality diagnostic**.

It is useful because a real judge can assess whether an answer actually fulfills the semantic intent of the question, including whether the response addresses all requested components.

This evaluation is not a replacement for `MOCK_LLM`; it is an additional layer of validation.

---

## 7. Direct Comparison

| Metric | `MOCK_LLM` | Real LLM | Difference (Real − Mock) |
|---|---:|---:|---:|
| Context relevance | 4.47 | 3.93 | -0.53 |
| Groundedness | 5.00 | 4.80 | -0.20 |
| Answer relevance | 3.93 | 4.60 | +0.67 |
| Overall | 4.47 | 4.44 | -0.02 |

### Interpretation

The two strategies provide complementary evidence.

**`MOCK_LLM` is valuable for:**
- satisfying the explicit Task 13 requirement;
- deterministic and reproducible evaluation;
- avoiding external API dependencies;
- producing the required per-query and aggregate scores.

**Real-LLM judging is valuable for:**
- independent semantic assessment;
- identifying incomplete answers;
- evaluating customer-facing usefulness;
- exposing weaknesses in compound questions.

The evaluations therefore should not be presented as competing implementations. The real-LLM evaluation is best described as an **additional best-practice validation layer**.

---

## 8. Detailed Query Insights

### Query 1 — Return window by product category

The query maps directly to a dedicated category-specific return policy containing explicit return windows.

**Finding:** Strong retrieval is achieved when the query terminology closely matches a well-structured policy document.

---

### Query 2 — COD refund timeline

The KB contains the refund-initiation timeline and the subsequent bank-posting period.

The result demonstrates strong retrieval and grounding, while answer relevance is lower under the more discriminating evaluation.

**Finding:** The evidence is available; the generation stage should prioritize the exact requested timeline instead of reproducing surrounding policy content.

---

### Query 3 — Delivery SLAs

The KB contains detailed domestic delivery SLAs by shipping method. The question also asks whether SLAs differ by destination.

This makes the query broader than a simple shipping-method lookup.

**Finding:** The weakness is primarily **retrieval completeness**, not grounding.

**Improvement:** Decompose the question into shipping-method and destination components and retrieve evidence for both.

---

### Query 4 — Reverse-pickup eligibility

The dedicated reverse-pickup policy covers eligibility, postal areas, carrier coverage, parcel dimensions, packaging and remote-area handling.

**Finding:** Dedicated policy documents are highly effective when they contain most of the information requested by the query.

---

### Query 8 — Payment failure/retry policy

The KB specifies a retry sequence and advises against indefinite repeated attempts, but it does not reduce the policy to a single simple maximum-attempt number.

**Finding:** The system should not invent a numeric limit that is not explicitly supported.

A future KB revision should distinguish clearly between the retry sequence and any actual maximum-attempt business rule.

---

### Query 11 — International shipping restrictions

The question contains two separate requirements:

1. restricted products/destinations;
2. what happens when international shipment cannot proceed.

**Finding:** Multi-part questions require retrieval to cover every requested policy dimension, rather than only the dominant semantic topic.

---

### Query 13 — Compound edge case

This query combines:

- international shipping,
- COD,
- damaged-item handling,
- delivery SLA,
- reverse pickup,
- refund eligibility,
- support escalation.

The `MOCK_LLM` evaluation scores this query **5/5 across all three metrics**, whereas the real-LLM evaluation is more conservative.

This difference is an important diagnostic signal. The query requires evidence from multiple policy areas, so a single top-k retrieval operation can struggle to provide complete evidence for every component.

**Finding:** Compound queries are the clearest case for introducing multi-intent detection and targeted retrieval.

---

### Queries 14–15 — Out-of-scope questions

These deliberately request information outside the Nimbus Commerce policy KB.

The system's conservative behavior is desirable for a policy-only RAG path: it does not need to fabricate unsupported information.

If the broader product is expected to answer general questions, these requests should instead be routed to an appropriate general-purpose capability.

---

## 9. Primary Strengths

### Strong grounding

The `MOCK_LLM` results show perfect groundedness across the complete 15-query evaluation.

### Strong direct-policy retrieval

Most dedicated policy topics retrieve highly relevant source material.

### Good scope discipline

Out-of-scope questions do not cause unsupported policy claims to be fabricated.

### Safe handling of incomplete evidence

The system is generally more conservative than speculative when the knowledge base does not provide a direct answer.

---

## 10. Primary Weaknesses

### Retrieval completeness

A single similarity search can prioritize one aspect of a multi-part query while missing another.

### Answer synthesis

Some responses repeat retrieved content instead of converting it into a concise, direct answer.

### Compound-query handling

Queries that combine multiple policies are harder than single-topic questions and expose limitations in a standard top-k retrieval strategy.

### Explicit policy limits

Where the KB describes an operational process but does not specify a simple numeric limit, the system needs to remain cautious.

---

## 11. Recommended Improvements

### 11.1 Multi-intent query decomposition

Detect when a query contains several policy intents.

For Query 13, for example, retrieve separately for:

1. international shipping;
2. damaged-item claims;
3. reverse pickup;
4. COD refunds;
5. delivery SLA;
6. support escalation.

Then synthesize the final response from the combined evidence.

### 11.2 Retrieval-completeness validation

Before generation, verify that every major component of the user's question has supporting context.

If an important component is missing, perform a second retrieval pass rather than immediately generating an answer.

### 11.3 Improved generation instructions

The generation prompt should require:

- a direct answer first;
- every requested component to be addressed;
- concise bullets for multi-part questions;
- no unnecessary copying of source text;
- no repetition;
- explicit acknowledgement of missing information.

### 11.4 Better knowledge-base specificity

Where an exact limit or threshold exists, represent it explicitly in the KB and distinguish it from general operational guidance.

### 11.5 Retain both evaluation modes

The recommended structure is:

```text
Task 13
|
+-- Required evaluation
|   +-- MOCK_LLM
|   +-- 15 queries
|   +-- 3 scores per query
|   +-- 3 aggregate averages
|
+-- Additional validation
    +-- Real LLM judges
    +-- Same 15 queries
    +-- Independent semantic-quality signal
```

This demonstrates both **strict capstone compliance** and **additional engineering validation**.

---

## 12. Suggested Engineering Quality Gates

These are proposed future engineering targets, not official capstone grading thresholds.

| Quality gate | Suggested target |
|---|---:|
| Overall triad average | ≥ 4.5/5 |
| Context relevance | ≥ 4.2/5 |
| Groundedness | ≥ 4.7/5 |
| Answer relevance | ≥ 4.7/5 |
| In-scope groundedness | ≥ 4.8/5 |
| In-scope answer relevance | ≥ 4.8/5 |
| Critical hallucination cases | 0 |
| Compound-query average | ≥ 4.0/5 |

---

## 13. Final Assessment

The evaluation demonstrates that the Nimbus Commerce RAG pipeline has a **strong grounding foundation** and generally effective retrieval for direct policy questions.

The required `MOCK_LLM` evaluation establishes the deterministic Task 13 baseline. The supplementary real-LLM evaluation adds a second perspective and identifies quality issues that are especially important for real customer-facing behavior.

The key lesson from both evaluations is:

> **High groundedness does not automatically mean high answer quality.**

The system can correctly restrict itself to the retrieved evidence while still failing to provide a complete and concise response to a multi-part question.

Therefore, the recommended optimization order is:

1. **Improve multi-intent retrieval.**
2. **Add retrieval-completeness validation.**
3. **Improve final-answer synthesis.**
4. **Keep the existing grounding constraints.**
5. **Retain real-LLM judging as supplementary validation.**

### Bottom line

> **The RAG system is strongest at staying grounded and answering direct policy questions. Its main opportunity is to retrieve and synthesize all evidence required by complex, multi-part questions.**

The two strategies complement each other: `MOCK_LLM` provides the required, reproducible Task 13 evaluation, while real-LLM judges provide additional semantic validation and a stronger signal for production-quality answer completeness.

