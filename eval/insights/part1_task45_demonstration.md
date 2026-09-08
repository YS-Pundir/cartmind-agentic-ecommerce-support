# Task 4–5: Grounded Generation and Chunking Strategy Evaluation

## Overview

This evaluation compares the two RAG chunking strategies used by Nimbus Commerce:

* **Fixed-Size** chunks — collection: `kb_fixed_size`
* **Sentence-Based** chunks — collection: `kb_sentence_based`

The evaluation uses the same set of queries for both collections. For each query, the system retrieves the top-3 chunks, calculates the top-1 cosine similarity, and uses the mock LLM to produce a grounded response from the retrieved context.

Under `MOCK_LLM`, no real LLM is used for generation. Retrieval similarity is therefore the primary signal used to determine whether sufficient relevant context exists.

---

# Task 4 — Grounded Generation

## Similarity Threshold Calibration

The threshold was calibrated using measured top-1 cosine similarities rather than using a predefined tutorial value.

### In-scope queries

| Query                                                       | Top-1 cosine similarity | Result   |
| ----------------------------------------------------------- | ----------------------: | -------- |
| What is the return window for electronics?                  |                  0.4907 | Grounded |
| How long does a COD refund take after a return is approved? |                  0.6309 | Grounded |
| What happens if my payment fails while placing an order?    |                  0.5795 | Grounded |
| What is the policy for redeeming loyalty points?            |                  0.7444 | Grounded |
| What should I do if I receive a damaged item?               |                  0.5540 | Grounded |

The measured in-scope similarity range was therefore:

**0.4907 – 0.7444**

The lowest observed in-scope value was **0.4907**.

### Deliberately out-of-scope queries

| Query                                   | Top-1 cosine similarity | Result   |
| --------------------------------------- | ----------------------: | -------- |
| How do I bake a chocolate cake?         |                  0.0368 | Fallback |
| What will the weather be like tomorrow? |                  0.1656 | Grounded |

The measured out-of-scope similarity values were **0.0368** and **0.1656**.

## Empirical Threshold Selection

The observed clusters were:

* **Out-of-scope:** 0.0368, 0.1656
* **In-scope:** 0.4907, 0.5540, 0.5795, 0.6309, 0.7444

There is a clear gap between the highest observed out-of-scope score and the lowest observed in-scope score:

```text
Highest out-of-scope = 0.1656
Lowest in-scope      = 0.4907
```

A threshold selected between these two measured clusters is:

**Chosen threshold = 0.3282**

This value is approximately the midpoint between `0.1656` and `0.4907`.

Therefore:

```text
similarity >= 0.3282  → generate grounded answer
similarity <  0.3282  → return "I don't know"
```

This threshold is based on the observed evaluation data rather than a preset value such as `0.5`, `0.6`, or `0.7`.

### Important calibration observation

The original evaluation output recorded a threshold of `0.1`. However, `0.1` is **not between the two observed similarity clusters**, because the second out-of-scope query has a similarity of `0.1656`.

Therefore, `0.1` should not be described as the empirically calibrated threshold for this evaluation. A threshold around `0.3282` better satisfies the stated calibration requirement.

---

# Task 4 — Grounded Generation Demonstration

Five real in-scope queries were tested.

### 1. Electronics return window

**Query:**

> What is the return window for electronics?

**Top-1 similarity:** `0.4907`

**Decision:** Grounded

The mock response retrieved the Nimbus Commerce return-policy context and correctly identified that electronics have a **14-day standard return window**.

---

### 2. COD refund timeline

**Query:**

> How long does a COD refund take after a return is approved?

**Top-1 similarity:** `0.6309`

**Decision:** Grounded

The retrieved context states that for an approved COD return, Nimbus Commerce normally initiates the refund within **3 business days after return inspection is completed**.

---

### 3. Failed payment

**Query:**

> What happens if my payment fails while placing an order?

**Top-1 similarity:** `0.5795`

**Decision:** Grounded

The retrieved context explains that a failed payment does not necessarily mean an order was successfully created and that a temporary bank authorization may still appear.

---

### 4. Loyalty points

**Query:**

> What is the policy for redeeming loyalty points?

**Top-1 similarity:** `0.7444`

**Decision:** Grounded

The retrieved context contains the Nimbus Rewards loyalty-points redemption policy and explains that points can be redeemed for eligible discounts or benefits.

---

### 5. Damaged item

**Query:**

> What should I do if I receive a damaged item?

**Top-1 similarity:** `0.5540`

**Decision:** Grounded

The retrieved context contains the damaged-item claim process and instructs customers with damaged or defective products to contact Nimbus Commerce promptly.

---

## Out-of-Scope Fallback Demonstration

**Query:**

> How do I bake a chocolate cake?

**Top-1 similarity:** `0.0368`

Because the similarity is below the calibrated threshold of `0.3282`, the system should return:

> I don't know — I don't have enough information in the knowledge base to answer that.

The recorded result already demonstrates this fallback behavior.

This demonstrates that the system can reject a clearly unrelated query rather than inventing an answer.

---

# Additional Out-of-Scope Calibration Observation

The query:

> What will the weather be like tomorrow?

produced a similarity of `0.1656`.

With the originally recorded threshold of `0.1`, the query was incorrectly classified as **Grounded**, even though its Precision@3 and Recall@3 were both `0.0`. The mock response retrieved unrelated weather/delivery-disruption text rather than answering the actual weather question.

With the empirically selected threshold of **0.3282**, this query would correctly trigger the fallback.

This is an important result because it demonstrates why the threshold must be calibrated against deliberately out-of-scope examples instead of using a low preset value.

---

# Task 5 — Chunking Strategy Evaluation

The same five in-scope queries were evaluated against both collections.

For document-level Precision@3 and Recall@3, retrieved chunks are mapped back to their parent documents and duplicate chunks from the same parent document are deduplicated before calculating the metrics.

## Fixed-Size Strategy

Collection:

`kb_fixed_size`

### Per-query results

| Query                     | Precision@3 | Recall@3 | Arithmetic                                                                                                       |
| ------------------------- | ----------: | -------: | ---------------------------------------------------------------------------------------------------------------- |
| Electronics return window |      0.3333 |   1.0000 | 1 relevant parent / 3 retrieved parents = 0.3333; 1 relevant parent retrieved / 1 relevant parent expected = 1.0 |
| COD refund timeline       |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                                                                      |
| Failed payment            |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                                                                      |
| Loyalty points            |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                                                                      |
| Damaged item              |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                                                                      |

The recorded evaluation results show `Precision@3 = 0.3333` and `Recall@3 = 1.0` for all five in-scope queries.

### Aggregate result

**Average Precision@3 = 0.3333**

**Average Recall@3 = 1.0000**

---

# Sentence-Based Strategy

Collection:

`kb_sentence_based`

### Per-query results

| Query                     | Precision@3 | Recall@3 | Arithmetic                                                    |
| ------------------------- | ----------: | -------: | ------------------------------------------------------------- |
| Electronics return window |      0.3333 |   1.0000 | 1 relevant parent / 3 retrieved parents = 0.3333; 1 / 1 = 1.0 |
| COD refund timeline       |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                   |
| Failed payment            |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                   |
| Loyalty points            |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                   |
| Damaged item              |      0.3333 |   1.0000 | 1 / 3 = 0.3333; 1 / 1 = 1.0                                   |

The Sentence-Based collection produced exactly the same Precision@3 and Recall@3 values for all five queries.

### Aggregate result

**Average Precision@3 = 0.3333**

**Average Recall@3 = 1.0000**

---

# Chunking Strategy Comparison

| Metric                            | Fixed-Size | Sentence-Based |
| --------------------------------- | ---------: | -------------: |
| Average Precision@3               |     0.3333 |         0.3333 |
| Average Recall@3                  |     1.0000 |         1.0000 |
| In-scope queries tested           |          5 |              5 |
| Queries with Recall@3 = 1.0       |        5/5 |            5/5 |
| Queries with Precision@3 = 0.3333 |        5/5 |            5/5 |

## The two strategies produced **identical retrieval metrics** on this five-query evaluation set.

# Recommendation

Based on the measured results, **neither Fixed-Size nor Sentence-Based chunking demonstrates a retrieval-quality advantage on this test set**. Both achieved an average Precision@3 of **0.3333** and an average Recall@3 of **1.0000**, meaning both consistently retrieved the relevant parent document but also returned two additional parent documents in the top three.

Since the retrieval metrics are identical, the current evaluation does not provide evidence that one strategy is superior. Therefore, either strategy is defensible for deployment based strictly on these numbers; a larger or more diverse evaluation set would be needed to establish a meaningful preference.

---

# Overall Insights

1. **Grounded generation worked for all five in-scope queries.**
   All five domain questions produced grounded responses and had top-1 similarities ranging from `0.4907` to `0.7444`.

2. **The similarity threshold needs empirical calibration.**
   The observed in-scope cluster begins at `0.4907`, while the out-of-scope examples were `0.0368` and `0.1656`. Therefore, a threshold of approximately `0.3282` lies between the observed clusters.

3. **The original `0.1` threshold is too low for these results.**
   It allows the weather query with similarity `0.1656` to pass through as grounded even though the retrieval metrics for that query are `0.0`.

4. **The mock LLM remained grounded when relevant context was available.**
   The recorded responses are derived from the retrieved Nimbus Commerce knowledge-base context, and the RAG-triad groundedness scores for the five in-scope queries were high, ranging from `0.8696` to `0.9700`.

5. **Both chunking strategies performed identically on this test set.**
   Fixed-Size and Sentence-Based chunking each achieved `0.3333` average Precision@3 and `1.0000` average Recall@3.

6. **The main retrieval weakness is precision, not recall.**
   A Recall@3 of `1.0` means the relevant parent document was consistently recovered. Precision@3 of `0.3333` indicates that only one of the three retrieved parent documents was relevant for each tested query.

---

# Final Task 4–5 Conclusion

The grounded-generation pipeline successfully answered five in-scope Nimbus Commerce questions using retrieved context and correctly fell back for the clearly unrelated chocolate-cake query. Empirical similarity measurements show a separation between the observed in-scope and out-of-scope examples, supporting a threshold of approximately **0.3282** rather than the originally recorded `0.1`.

For chunking, **Fixed-Size and Sentence-Based strategies were tied on the current evaluation set**, both achieving **Precision@3 = 0.3333** and **Recall@3 = 1.0000**. Consequently, the present evidence does not establish a performance-based winner between the two strategies.
