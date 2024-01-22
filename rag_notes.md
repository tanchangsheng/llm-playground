# RAG Knobs to Tune

## Baseline
- Embedding models
    - open source/commercial models
    - fine-tune embedding models

## Query Transformation
- HyDE - [Hypothetical Document Embeddings](https://boston.lti.cs.cmu.edu/luyug/HyDE/HyDE.pdf)
    - generates hypothetical documents for an incoming query, embeds them, and uses them in retrieval (see paper). The idea is that these simulated documents may have more similarity to the desired source documents than the question.
- [Rewrite-Retrieve-Read](https://arxiv.org/pdf/2305.14283.pdf) Query Rewriting for Retrieval-Augmented Large Language Models
- Multi Query Retrieval
    - Generate multiple search queries of different perspectives. These search queries can then be executed in parallel, and the retrieved results passed in altogether. This is really useful when a single question may rely on multiple sub questions.

## Routing
- Find the right data source among a diverse range of data sources (multiple vector indices, dbs, multimodal) using LLM agents or traditional classifiers.
- Deciding on the appropriate course of action. E.g. whether to do summarization, semantic search or interacting with other agents or tools. Typically agent based.

## Indexing
- Experiment with chunk size/overlap.
- Document enrichment with metadata.
    - metadata can be used for filtering rules or be part of document embeddings.

## Retrieval
- Hybrid search
    - Experiment with text-embedding weighting.
    - Can be done natively with vectore stores that support text-embeddings.
- Ensemble retrieval 
    - Query multiple different data stores(separate indices that may use different embedding/indexing stragegies, text indices) then combine results and re-rank results.
- Experiment with number of retrieved chunks K.

## Post-Processing (post retrieval)
- Re-ranking
    - Scores and re-orders the retrieved contexts.
    - Using LLMs, sentence-transformer cross-encoders (question-retrieved chunks similarity score)
    - Reciprocal Rerank Fusion | [paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) | [algo](https://github.com/Raudaschl/rag-fusion/blob/master/main.py)
        - Take the retrieved documents from multiple retrieval methods(ensemble), assign a reciprocal rank score to each document in the results, and then combining the scores to create a new ranking. The concept is that documents appearing in the top positions across multiple search methods are likely to be more relevant and should be ranked higher in the combined result.
        - [llama_index example](https://docs.llamaindex.ai/en/stable/examples/retrievers/reciprocal_rerank_fusion.html)
- Filtering
    - Based on metadata, re-rank similarity scores

## Response Generation 
- Generation: Fine-tuning LLM for specific tasks (higher effort and resource)
- Classification Step
    - Classify retrieved document then chose a different prompt depending on the classification. This could make the answer more relevant based on the retrieved context.
- Prompt Selection / Engineering
    - In context learning (Zero/Few shot)

## Agent / Tools
- [ReAct Prompting](https://arxiv.org/abs/2210.03629)
    - used to generate both reasoning traces and task-specific actions in an interleaved manner.
    - allow LLMs to interact with external tools to retrieve additional information that leads to more reliable and factual responses.
    - [llama_index example](https://docs.llamaindex.ai/en/stable/examples/agent/react_agent_with_query_engine.html)