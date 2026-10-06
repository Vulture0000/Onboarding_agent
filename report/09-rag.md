# 9. RAG for Policy Answers

## 9.1 Knowledge Ingestion

The policy corpus is ingested through a two-layer architecture, because document loading and document representation are different problems and are solved separately.

**Loading.** Five `.txt` policy documents are read from `backend/data/policies/` at startup. `pypdf` is present for PDF ingestion but is unused by the current corpus, which is plain text by design so that ingestion has no failure mode to debug.

**Representation.** The pipeline is LangChain's `RecursiveCharacterTextSplitter`, with the following parameters:

| Parameter | Value | Reason |
|---|---|---|
| `chunk_size` | 500 | Policy documents are short. 1,000–1,500 byte documents split into 2–3 chunks. Larger chunks would exceed the retrieved context without improving relevance. |
| `chunk_overlap` | 50 | Preserves a sentence that begins at a chunk boundary — material when the answer is a specific number, such as a leave entitlement. |
| Separators | `\n\n`, `\n`, `. ` | Paragraph, then line, then sentence. Section boundaries are the strongest topical signal in these documents. |

The resulting corpus is roughly 12–15 chunks across 5 documents. Chunk count is deliberately small: every chunk is retrieved with source attribution, and a corpus this size allows the *whole* policy set to fit in a context window, which is precisely why the unanswerable-query behaviour is a meaningful test (Section 11.3) rather than a formality.

**Embeddings.** `GeminiEmbeddings` with `models/text-embedding-004`, persisting the index to disk via `save_local` so the index is not rebuilt on every process start.

## 9.2 Retrieval Strategy

The retriever is a **hybrid design with an explicit degradation path**, and the two halves deserve separate treatment because one worked as designed and one did not.

### 9.2.1 Primary path — FAISS vector retrieval (attempted, unavailable in this environment)

Embeddings are generated, the index is built with `FAISS.from_documents`, and queries are matched by `similarity_search` with `k=3`. This is the intended primary strategy: it is scale-appropriate, in-process, and requires no service dependency.

**In the current environment it does not execute.** The configured embedding model `models/text-embedding-004` returns `404 NOT_FOUND` from the Gemini API. Index construction therefore raises, and the system falls back. This is reported as a factual result rather than a design choice, and it has a consequence that must be stated plainly: **the semantic retrieval path is implemented and correct in structure, but is unverified in this deployment, and none of the performance figures below should be attributed to FAISS.**

### 9.2.2 Fallback path — keyword retrieval (active)

When embedding construction fails, the system switches to keyword matching:

- Query terms tokenised, lowercased, filtered of stopwords
- Each chunk scored by **term overlap**, weighted by inverse document frequency so that a match on a distinctive term ("reimbursement", "bereavement") outranks a match on a common one ("days", "leave")
- Top `k=3` chunks returned, each carrying its source filename
- A **relevance floor** is applied: if the top score is below the threshold, the system returns nothing and declares the question unanswerable

The relevance floor is the most important element. Without it, a keyword retriever will always return its three best chunks — and a RAG layer that always receives context will always answer. The floor is what makes the refusal behaviour in Section 9.4 possible.

**Why this fallback exists as a design, not a patch.** The R11 requirement is that the system functions with no LLM API key. A key that is absent, an account with no access, and a model that has been deprecated all present differently and are all recoverable conditions. A hard dependency on one specific embedding model would fail the requirement for reasons outside the system's control. The keyword path is a genuine, if weaker, retrieval mechanism — and on a five-document corpus where the queries contain the distinctive terms, it performs well, which is exactly what Section 11.3 shows.

## 9.3 Grounding and Relevance

Grounding is enforced by construction, and it is worth being precise about what "grounded" means here, because the term is used loosely.

**The model's role is to phrase an answer from supplied chunks, not to supply an answer.** The prompt instructs the model to answer *only* from the provided context, to cite the source document, and to state that the information is unavailable if the context does not contain it. But a prompt instruction is a request, not a guarantee, and a model can be talked out of it.

**The guarantee comes from the retrieval side.** Three conditions must hold for an answer to be produced at all:

1. The query must clear the relevance floor, or nothing is retrieved.
2. If nothing clears the floor, the request returns a refusal response — the model is never called.
3. The sources are returned alongside the answer, from the retrieval metadata, not from the model's text.

**The two-layer test.** Section 11.3 measures both layers separately, because they fail differently. A retrieval failure is silent and looks like a confident wrong answer. A generation failure is visible. The system also has a keyword-availability check on the returned answer: if a question's distinctive term is absent from the retrieved context, the system flags the answer as insufficiently grounded. This catches the failure mode where retrieval returns *technically* relevant but *practically* unhelpful chunks, and the model bridges the gap from memory.

## 9.4 Refusal Behaviour

Refusal is a first-class outcome with a defined contract, not an error state or an apology.

| Condition | System response |
|---|---|
| Query in corpus, chunks found | Answer generated from chunks, with source filenames |
| Query outside corpus, below relevance floor | Explicit refusal stating the policies do not cover the topic, and naming what *is* available |
| Embeddings unavailable | Keyword path used transparently; no user-visible degradation message required |
| LLM unavailable entirely | Refusal with the available policy documents listed, so the employee knows where to look |

**The employee-facing value of refusal is high precisely because employees cannot evaluate policy answers.** As noted in Section 3.1, a new hire has no way to tell a grounded answer from a confident fabrication. A system that always answers gives that employee no signal. A system that sometimes says "this is not covered by the policy documents" gives them a reliable one — and, as Section 9.3's second test shows, the employee is then routed to a human instead of acting on a wrong number.

The policy summary is also available to users who prefer to read: `/api/policy/summary` returns the set of available topics, so the refusal response is a redirect to a real destination rather than a dead end.
