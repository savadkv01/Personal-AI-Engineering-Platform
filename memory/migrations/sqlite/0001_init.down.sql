-- Reverts 0001_init (SQLite). Destroys all memory + session data.
DROP TABLE IF EXISTS memory_vector;
DROP TABLE IF EXISTS session_turn;
DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS memory_item;
