CREATE TABLE public.achievements
(
    id serial,
    name text DEFAULT 'Achievement name placeholder',
    description text DEFAULT 'Achievement description placeholder',
    thumbnail text DEFAULT 'https://cdn.discordapp.com/attachments/774698479981297664/774700936958312468/placeholder.png',
    rep_boost integer DEFAULT 0,
    PRIMARY KEY (id)
);

ALTER TABLE public.achievements
    OWNER to postgres;


CREATE TABLE public.casino
(
    user_id bigint,
    cash bigint DEFAULT 0,
    e_cash bigint DEFAULT 0,
    credits json DEFAULT '{"user_credit_story":[]}'::json
);

ALTER TABLE public.casino
    OWNER to postgres;


CREATE TABLE public.durka_stats
(
    user_id bigint,
    available_durka_uses smallint DEFAULT 3,
    received_durka_calls bigint DEFAULT 0,
    sent_durka_calls bigint DEFAULT 0
);

ALTER TABLE public.durka_stats
    OWNER to postgres;


CREATE TABLE public.fn_profiles
(
    user_id bigint,
    nickname text,
    platform text
);

ALTER TABLE public.fn_profiles
    OWNER to postgres;


CREATE TABLE public.leveling
(
    user_id bigint,
    level bigint DEFAULT 0,
    xp bigint DEFAULT 0,
    total_xp bigint DEFAULT 0,
    xp_lock timestamp without time zone DEFAULT (now())::timestamp without time zone
);

ALTER TABLE public.leveling
    OWNER to postgres;


CREATE TABLE public.mutes
(
    user_id bigint,
    role_ids text,
    mute_start_time timestamp without time zone DEFAULT (now())::timestamp without time zone,
    mute_end_time timestamp without time zone
);

ALTER TABLE public.mutes
    OWNER to postgres;


CREATE TABLE public.reactions
(
    emoji text,
    role text,
    message_id text,
    channel_id text,
    guild_id text
);

ALTER TABLE public.reactions
    OWNER to postgres;


CREATE TABLE public.song_suggestions
(
    suggestion_id bigserial,
    suggestion_type text,
    suggestion_author_id bigint,
    suggested_song text,
    suggestion_comment text,
    curator_id bigint,
    curator_decision boolean,
    curator_comment text,
    created_at timestamp without time zone DEFAULT (now())::timestamp without time zone,
    closed_at timestamp without time zone
);

ALTER TABLE public.song_suggestions
    OWNER to postgres;


CREATE TABLE public.users_info
(
    user_id bigint,
    nickname text,
    mention text,
    joined_at timestamp without time zone DEFAULT (now())::timestamp without time zone,
    brief_biography text,
    is_profile_public boolean DEFAULT FALSE
);

ALTER TABLE public.users_info
    OWNER to postgres;


CREATE TABLE public.users_stats
(
    user_id bigint,
    achievements_list json DEFAULT '{"user_achievements_list":[]}'::json,
    messages_count bigint DEFAULT 0,
    last_message_date timestamp without time zone DEFAULT (now())::timestamp without time zone,
    rep_rank bigint DEFAULT 0,
    lost_reputation bigint DEFAULT 0,
    profanity_triggers bigint DEFAULT 0,
    invoice_time bigint DEFAULT 0,
    purchases json DEFAULT '{"vbucks_purchases":[],"realMoney_purchases":[]}'::json,
    mutes_story json DEFAULT '{"user_mute_story":[]}'::json,
    warns_story json DEFAULT '{"user_warn_story":[]}'::json
);

ALTER TABLE public.users_stats
    OWNER to postgres;


CREATE TABLE public.voice_activity
(
    user_id bigint,
    entered_at timestamp without time zone
);

ALTER TABLE public.voice_activity
    OWNER to postgres;