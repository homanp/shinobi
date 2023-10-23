from typing import Callable, List

import requests
from decouple import config


def create_vector_embeddings(
    type: str, model: str, filter_id: str, url: str = None, content: str = None
) -> List:
    from nagato.service.embedding import EmbeddingService

    embedding_service = EmbeddingService(type=type, content=content, url=url)
    documents = embedding_service.generate_documents()
    nodes = embedding_service.generate_chunks(documents=documents)
    embedding_service.generate_embeddings(nodes=nodes, filter_id=filter_id, model=model)
    return nodes


def create_finetuned_model(
    provider: str,
    base_model: str,
    type: str,
    url: str = None,
    content: str = None,
    webhook_url: str = None,
    num_questions_per_chunk: int = 10,
) -> dict:
    from nagato.service.embedding import EmbeddingService
    from nagato.service.finetune import get_finetuning_service

    embedding_service = EmbeddingService(type=type, url=url, content=content)
    documents = embedding_service.generate_documents()
    nodes = embedding_service.generate_chunks(documents=documents)
    finetunning_service = get_finetuning_service(
        nodes=nodes,
        provider=provider,
        batch_size=5,
        base_model=base_model,
        num_questions_per_chunk=num_questions_per_chunk,
    )
    training_file = finetunning_service.generate_dataset()
    formatted_training_file = finetunning_service.validate_dataset(
        training_file=training_file
    )
    finetune = finetunning_service.finetune(
        training_file=formatted_training_file, webhook_url=webhook_url
    )
    if provider == "OPENAI":
        requests.post(webhook_url, json=finetune)
    finetunning_service.cleanup(training_file=finetune.get("training_file"))
    return finetune


def predict(
    provider: str, model: str, callback: Callable = None, enable_streaming: bool = False
) -> dict:
    from nagato.service.query import get_query_service

    query_service = get_query_service(provider=provider, model=model)
    output = query_service.predict(
        input="Hello world", callback=callback, enable_streaming=enable_streaming
    )
    return output


def query_embedding(
    query: str,
    model: str = "all-minilm-l6-v2",
    provider: str = "pinecone",
    filter_id: str = None,
) -> dict:
    from sentence_transformers import SentenceTransformer

    from nagato.service.embedding import get_vector_service

    embedding_model = SentenceTransformer(model, use_auth_token=config("HF_API_KEY"))
    vectordb = get_vector_service(
        provider=provider,
        index_name=model,
        filter_id=filter_id,
        dimension=384,
    )
    embedding = embedding_model.encode([query]).tolist()
    return vectordb.query(queries=embedding, top_k=5, include_metadata=True)
