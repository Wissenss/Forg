-- migrate:up
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

-- migrate:down
DROP TABLE accounts;
DROP TABLE settings;
DROP TABLE messages;
DROP TABLE messages_word_count;