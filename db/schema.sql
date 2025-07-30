CREATE TABLE IF NOT EXISTS "migrations" (version varchar(128) primary key);
CREATE TABLE accounts (
    discord_user_id INTEGER,
    discord_guild_id INTEGER,
    access_level INTEGER,
    PRIMARY KEY(discord_user_id, discord_guild_id)
);
CREATE TABLE settings (
    name,
    discord_user_id INTEGER,
    discord_guild_id INTEGER,
    discord_channel_id INTEGER,
    value,
    UNIQUE(name, discord_user_id, discord_guild_id, discord_channel_id)
);
CREATE TABLE messages (
    discord_message_id INTEGER,
    discord_guild_id INTEGER,
    discord_channel_id INTEGER,
    discord_created_at TEXT,
    discord_user_id INTEGER,
    content TEXT,
    content_clean TEXT,
    deleted BOOLEAN DEFAULT false,
    PRIMARY KEY(discord_message_id)
);
CREATE TABLE messages_word_count (
    word TEXT,
    discord_guild_id INTEGER,
    discord_channel_id INTEGER,
    discord_user_id INTEGER,
    count INTEGER,
    PRIMARY KEY(word, discord_guild_id, discord_channel_id, discord_user_id)
);
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind INTEGER,
  discord_user_id INTEGER,
  discord_guild_id INTEGER,
  related_transaction_id INTEGER,
  amount REAL,
  timestamp TEXT
);
-- Dbmate schema migrations
INSERT INTO "migrations" (version) VALUES
  ('20250717070747'),
  ('20250727203847');
