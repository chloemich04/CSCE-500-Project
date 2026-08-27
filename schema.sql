-- Mini Shop — tables for Supabase
-- Run this in: Supabase Dashboard → SQL Editor → New query → Run
--
-- Step 1 (this file, now): users only — enough for register / login.
-- Later steps will add products, cart, and orders.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('customer', 'store_manager')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
