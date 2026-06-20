import { createClient } from '@supabase/supabase-js';
const url = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://localhost';
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'public-anon-key';
export const supabase = createClient(url, anon);
