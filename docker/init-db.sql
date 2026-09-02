-- Create the pgvector extension and the document_intelligence database role/objects.
-- pgvector image already enables the extension on the default DB; this ensures it exists
-- for the app database.
CREATE EXTENSION IF NOT EXISTS vector;
