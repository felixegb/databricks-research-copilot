CREATE EXTENSION IF NOT EXISTS vector;
 
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
 
CREATE TABLE learning_goals (
  goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active',        -- active | completed | archived
  created_at TIMESTAMP DEFAULT now()
);
 
CREATE TABLE papers (
  paper_id TEXT PRIMARY KEY,           -- ej: 'openalex:W123...' o 'arxiv:2501.12345'
  source TEXT NOT NULL,                -- 'openalex' | 'arxiv'
  source_id TEXT NOT NULL,             -- id nativo en la fuente
  title TEXT NOT NULL,
  abstract TEXT,
  publication_year INT,
  doi TEXT,
  oa_url TEXT,
  topics JSONB,
  embedding VECTOR(1536),
  created_at TIMESTAMP DEFAULT now(),
  UNIQUE(source, source_id)
);
 
CREATE TABLE authors (
  author_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  institution TEXT
);
 
CREATE TABLE paper_authors (
  paper_id TEXT REFERENCES papers(paper_id) ON DELETE CASCADE,
  author_id TEXT REFERENCES authors(author_id) ON DELETE CASCADE,
  PRIMARY KEY (paper_id, author_id)
);
 
CREATE TABLE collections (
  collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  goal_id UUID REFERENCES learning_goals(goal_id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
 
CREATE TABLE collection_papers (
  collection_id UUID REFERENCES collections(collection_id) ON DELETE CASCADE,
  paper_id TEXT REFERENCES papers(paper_id) ON DELETE CASCADE,
  added_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (collection_id, paper_id)
);
 
CREATE TABLE reading_progress (
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  paper_id TEXT REFERENCES papers(paper_id) ON DELETE CASCADE,
  status TEXT DEFAULT 'not_started',   -- not_started | reading | done
  updated_at TIMESTAMP DEFAULT now(),
  PRIMARY KEY (user_id, paper_id)
);
 
CREATE TABLE notes (
  note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
  paper_id TEXT REFERENCES papers(paper_id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);
