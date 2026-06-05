CREATE TABLE flows (
  id INTEGER PRIMARY KEY,
  plan_id TEXT UNIQUE,
  name TEXT,
  status TEXT DEFAULT 'pending',
  goal TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE flow_steps (
  id INTEGER PRIMARY KEY,
  flow_id INTEGER REFERENCES flows(id),
  step_number INTEGER,
  description TEXT,
  status TEXT DEFAULT 'pending',
  agent TEXT,
  started_at TEXT,
  completed_at TEXT,
  error TEXT
);
