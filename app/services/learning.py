import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FAQSuggestion, KnowledgeDocument, RegressionCase, Tenant

STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "i",
    "you",
    "to",
    "for",
    "of",
    "and",
    "do",
    "does",
    "what",
    "how",
    "can",
    "my",
}


class LearningService:
    def register_unresolved(self, db: Session, tenant: Tenant, question: str) -> FAQSuggestion:
        cluster_key = self._cluster_key(question)
        existing = db.scalar(
            select(FAQSuggestion).where(
                FAQSuggestion.tenant_id == tenant.id,
                FAQSuggestion.cluster_key == cluster_key,
            )
        )
        if existing:
            existing.count += 1
            return existing
        suggestion = FAQSuggestion(
            tenant_id=tenant.id,
            cluster_key=cluster_key,
            representative_question=question,
            count=1,
            status="pending",
        )
        db.add(suggestion)
        db.flush()
        return suggestion

    def approve(
        self, db: Session, tenant: Tenant, suggestion: FAQSuggestion, answer: str
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            tenant_id=tenant.id,
            title=f"Approved FAQ: {suggestion.representative_question[:80]}",
            source=f"learning-loop:suggestion-{suggestion.id}",
            content=answer,
            approved=True,
        )
        db.add(document)
        db.flush()
        suggestion.status = "approved"
        suggestion.suggested_answer = answer
        suggestion.approved_document_id = document.id
        db.add(
            RegressionCase(
                tenant_id=tenant.id,
                name=f"FAQ suggestion {suggestion.id}",
                utterance=suggestion.representative_question,
                expected_intent="faq",
                expected_contains=answer.split()[0],
                active=True,
            )
        )
        return document

    @staticmethod
    def _cluster_key(question: str) -> str:
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", question.lower())
            if token not in STOPWORDS
        ]
        common = [token for token, _ in Counter(tokens).most_common(5)]
        return "-".join(sorted(common)) or "unknown"
