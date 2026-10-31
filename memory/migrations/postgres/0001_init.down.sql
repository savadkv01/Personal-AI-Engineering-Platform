-- Reverts 0001_init (PostgreSQL). Destroys all memory + session data.
DROP TABLE IF EXISTS session_turn;
DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS memory_item;
