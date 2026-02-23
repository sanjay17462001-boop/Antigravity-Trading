import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET() {
    try {
        const { data, error } = await supabase
            .from('ai_strategies')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) throw error;
        return NextResponse.json({ strategies: data || [], count: data?.length || 0 });
    } catch (e: any) {
        return NextResponse.json({ strategies: [], count: 0 });
    }
}
