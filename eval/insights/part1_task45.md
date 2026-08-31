# Part 1 — Task 4 & Task 5 Evaluation

## Task 4 — Grounded Generation

The RAG system was evaluated using two ChromaDB collections:

* `kb_fixed_size`
* `kb_sentence_based`

A similarity threshold of **0.1** was selected for the grounded-generation decision. Queries with a top-1 similarity below this threshold trigger the fallback response instead of generating an answer.

### Results

| Query                         |        Fixed-Size |    Sentence-Based |
| ----------------------------- | ----------------: | ----------------: |
| Return window for electronics | 0.2797 — Grounded | 0.2964 — Grounded |
| COD refund timeline           | 0.4780 — Grounded | 0.6389 — Grounded |
| Payment failure               | 0.4053 — Grounded | 0.5348 — Grounded |
| Loyalty point redemption      | 0.6385 — Grounded | 0.5351 — Grounded |
| Damaged item                  | 0.3693 — Grounded | 0.3063 — Grounded |

The deliberately out-of-scope queries correctly triggered the fallback. For example, the chocolate-cake query produced a similarity of **-0.3622** for Fixed-Size and **-0.3560** for Sentence-Based, both below the 0.1 threshold. The weather query also triggered the fallback.

---

## Task 5 — Chunking Strategy Comparison

Precision@3 and Recall@3 were calculated at the **parent-document level** after mapping retrieved chunks to their source documents.

### Fixed-Size

| Query              | Precision@3 | Recall@3 |
| ------------------ | ----------: | -------: |
| Electronics return |      0.3333 |   1.0000 |
| COD refund         |      0.3333 |   1.0000 |
| Payment failure    |      0.3333 |   1.0000 |
| Loyalty points     |      0.3333 |   1.0000 |
| Damaged item       |      0.3333 |   1.0000 |

**Average Precision@3: 0.3333**
**Average Recall@3: 1.0000**

### Sentence-Based

| Query              | Precision@3 | Recall@3 |
| ------------------ | ----------: | -------: |
| Electronics return |      0.0000 |   0.0000 |
| COD refund         |      0.3333 |   1.0000 |
| Payment failure    |      0.3333 |   1.0000 |
| Loyalty points     |      0.3333 |   1.0000 |
| Damaged item       |      0.3333 |   1.0000 |

**Average Precision@3: 0.2666**
**Average Recall@3: 0.8000**

For the electronics-return query, Sentence-Based retrieval returned an irrelevant severe-damage document despite having a similarity of 0.2964, while Fixed-Size retrieved the relevant return-window information.

## Conclusion

**Fixed-Size chunking is selected for deployment.** It achieved higher average Precision@3 (**0.3333 vs. 0.2666**) and higher average Recall@3 (**1.0000 vs. 0.8000**) than Sentence-Based chunking. Therefore, the downstream RAG agent will use the `kb_fixed_size` collection.
