import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import KnowledgeDocument, Tenant
from app.services.embeddings import cosine_similarity, embed_text


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: int
    title: str
    source: str
    content: str
    score: float


class RAGService:
    """Retrieval layer with pgvector in Postgres and a deterministic local fallback."""

    def ingest(self, db: Session, tenant: Tenant, title: str, source: str, content: str) -> int:
        document = KnowledgeDocument(
            tenant_id=tenant.id,
            title=title,
            source=source,
            content=content,
            approved=True,
        )
        db.add(document)
        db.flush()
        if self._is_postgres(db):
            self._ensure_pgvector_schema(db)
            for index, chunk in enumerate(self._chunks(content)):
                embedding = self._vector_literal(embed_text(chunk))
                db.execute(
                    text(
                        """
                        INSERT INTO kb_chunks
                            (tenant_id, document_id, chunk_index, title, source, content, embedding)
                        VALUES
                            (:tenant_id, :document_id, :chunk_index, :title, :source, :content,
                             CAST(:embedding AS vector))
                        ON CONFLICT (document_id, chunk_index)
                        DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding
                        """
                    ),
                    {
                        "tenant_id": tenant.id,
                        "document_id": document.id,
                        "chunk_index": index,
                        "title": title,
                        "source": source,
                        "content": chunk,
                        "embedding": embedding,
                    },
                )
        return document.id

    def retrieve(
        self, db: Session, tenant: Tenant, query: str, top_k: int = 3
    ) -> list[RetrievedChunk]:
        if self._is_postgres(db):
            self._ensure_pgvector_schema(db)
            rows = db.execute(
                text(
                    """
                    SELECT document_id, title, source, content,
                           1 - (embedding <=> CAST(:embedding AS vector)) AS score
                    FROM kb_chunks
                    WHERE tenant_id = :tenant_id
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                    """
                ),
                {
                    "embedding": self._vector_literal(embed_text(query)),
                    "tenant_id": tenant.id,
                    "top_k": top_k,
                },
            ).mappings()
            return [
                RetrievedChunk(
                    document_id=int(row["document_id"]),
                    title=str(row["title"]),
                    source=str(row["source"]),
                    content=str(row["content"]),
                    score=float(row["score"]),
                )
                for row in rows
            ]

        documents = db.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.tenant_id == tenant.id,
                KnowledgeDocument.approved.is_(True),
            )
        ).all()
        query_embedding = embed_text(query)
        ranked: list[RetrievedChunk] = []
        for document in documents:
            for chunk in self._chunks(document.content):
                lexical = self._lexical_overlap(query, chunk)
                score = 0.8 * lexical + 0.2 * cosine_similarity(
                    query_embedding, embed_text(chunk)
                )
                ranked.append(
                    RetrievedChunk(
                        document_id=document.id,
                        title=document.title,
                        source=document.source,
                        content=chunk,
                        score=score,
                    )
                )
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _lexical_overlap(query: str, content: str) -> float:
        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        content_tokens = set(re.findall(r"[a-z0-9]+", content.lower()))
        if not query_tokens:
            return 0.0
        return len(query_tokens & content_tokens) / len(query_tokens)

    @staticmethod
    def _is_postgres(db: Session) -> bool:
        return bool(db.bind and db.bind.dialect.name == "postgresql")

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"

    @staticmethod
    def _ensure_pgvector_schema(db: Session) -> None:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS kb_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id INTEGER NOT NULL,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(64) NOT NULL,
                    UNIQUE(document_id, chunk_index)
                )
                """
            )
        )
        db.execute(text("CREATE INDEX IF NOT EXISTS kb_chunks_tenant_idx ON kb_chunks (tenant_id)"))

    @staticmethod
    def _chunks(content: str, max_chars: int = 700) -> list[str]:
        paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
        if not paragraphs:
            return [content[:max_chars]]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip()
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = paragraph
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks
