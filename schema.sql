PRAGMA foreign_keys = ON;

-- USERS TABLE
-- Stores login credentials (user_id + pin)
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT UNIQUE NOT NULL,
  pin TEXT NOT NULL,
  active INTEGER DEFAULT 1
);

-- QUESTIONS TABLE
-- Each row is one question with four options and the correct answer
CREATE TABLE IF NOT EXISTS questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  option_a TEXT NOT NULL,
  option_b TEXT NOT NULL,
  option_c TEXT NOT NULL,
  option_d TEXT NOT NULL,
  correct_option TEXT NOT NULL CHECK (correct_option IN ('A','B','C','D'))
);

-- SESSIONS TABLE
-- Stores each exam attempt: which questions were chosen, user answers, score, and timestamps
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  question_ids TEXT NOT NULL,  -- JSON array string of 50 question IDs
  answers TEXT,                -- JSON object string {question_id: 'A'|'B'|'C'|'D'}
  score INTEGER,
  started_at TEXT,
  submitted_at TEXT,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

DROP TABLE IF EXISTS questions;
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL
);

DROP TABLE IF EXISTS answers;
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);
