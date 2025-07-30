-- migrate:up
CREATE TABLE transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind INTEGER,
  discord_user_id INTEGER,
  discord_guild_id INTEGER,
  related_transaction_id INTEGER,
  amount REAL,
  timestamp TEXT
);

-- migrate:down
DROP TABLE transactions;