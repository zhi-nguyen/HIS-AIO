-- Enable pgvector extension for PostgreSQL
-- Run this SQL script before running Django migrations

CREATE EXTENSION IF NOT EXISTS vector;

-- Create index for faster vector similarity search
-- This will be created automatically by Django migrations, but listed here for reference
-- CREATE INDEX ON ai_engine_vectordocument USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
