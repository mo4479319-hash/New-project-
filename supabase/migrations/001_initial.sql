-- ============================================================
-- AI Website Builder - Database Schema
-- Run this in your Supabase SQL Editor or as a migration.
-- ============================================================

-- 1. Businesses
create table if not exists businesses (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    type text not null default 'business',
    description text,
    phone text,
    email text,
    address text,
    city text,
    state text,
    country text,
    website_url text,
    logo_url text,
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_businesses_user_id on businesses(user_id);

-- 2. Website Configurations (immutable history — never update, always insert)
create table if not exists website_configurations (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    backbone jsonb not null default '{}',
    environment text not null default 'staging' check (environment in ('staging', 'production')),
    difference jsonb,  -- RFC 6902 JSON Patch from previous version
    message_id uuid,   -- links to the chat message that triggered this change
    created_at timestamptz not null default now()
);

create index idx_website_configs_business on website_configurations(business_id, created_at desc);
create index idx_website_configs_env on website_configurations(business_id, environment, created_at desc);

-- 3. Conversations
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references businesses(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    title text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_conversations_business on conversations(business_id, created_at desc);

-- 4. Messages
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    metadata jsonb default '{}',
    created_at timestamptz not null default now()
);

create index idx_messages_conversation on messages(conversation_id, created_at asc);

-- 5. Generated Website Files (HTML/CSS/JS output from backbone)
create table if not exists website_files (
    id uuid primary key default gen_random_uuid(),
    configuration_id uuid not null references website_configurations(id) on delete cascade,
    file_path text not null,      -- e.g. 'index.html', 'styles.css'
    content text not null,
    created_at timestamptz not null default now(),
    unique(configuration_id, file_path)
);

create index idx_website_files_config on website_files(configuration_id);

-- ============================================================
-- Row Level Security (RLS) — users can only access their own data
-- ============================================================

alter table businesses enable row level security;
alter table website_configurations enable row level security;
alter table conversations enable row level security;
alter table messages enable row level security;
alter table website_files enable row level security;

-- Businesses: users see only their own
create policy "Users manage own businesses" on businesses
    for all using (auth.uid() = user_id);

-- Configurations: users see configs for their businesses
create policy "Users manage own website configs" on website_configurations
    for all using (
        business_id in (select id from businesses where user_id = auth.uid())
    );

-- Conversations: users see their own
create policy "Users manage own conversations" on conversations
    for all using (auth.uid() = user_id);

-- Messages: users see messages in their conversations
create policy "Users see own messages" on messages
    for all using (
        conversation_id in (select id from conversations where user_id = auth.uid())
    );

-- Website files: users see files for their configs
create policy "Users see own website files" on website_files
    for all using (
        configuration_id in (
            select wc.id from website_configurations wc
            join businesses b on b.id = wc.business_id
            where b.user_id = auth.uid()
        )
    );

-- ============================================================
-- Helper function: get latest config for a business + environment
-- ============================================================
create or replace function get_latest_config(
    p_business_id uuid,
    p_environment text default 'staging'
)
returns website_configurations
language sql
stable
as $$
    select *
    from website_configurations
    where business_id = p_business_id
      and environment = p_environment
    order by created_at desc
    limit 1;
$$;
