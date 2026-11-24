CREATE TABLE IF NOT EXISTS rag_documents (
    id TEXT PRIMARY KEY,
    collection TEXT,
    source_type TEXT NOT NULL,
    published_at TEXT,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_articles (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    article_order INTEGER NOT NULL,
    data TEXT NOT NULL,

    FOREIGN KEY (document_id)
        REFERENCES rag_documents(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    data TEXT NOT NULL,

    FOREIGN KEY (document_id)
        REFERENCES rag_documents(id)
        ON DELETE CASCADE,

    FOREIGN KEY (article_id)
        REFERENCES rag_articles(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rag_documents_collection
    ON rag_documents(collection);

CREATE INDEX IF NOT EXISTS idx_rag_articles_document
    ON rag_articles(document_id, article_order);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
    ON rag_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_article
    ON rag_chunks(article_id, chunk_index);
