import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET() {
    try {
        const { data, error } = await supabase
            .from('ai_backtest_history')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(50);

        if (error) throw error;
        return NextResponse.json({ runs: data || [], count: data?.length || 0 });
    } catch (e: any) {
        return NextResponse.json({ runs: [], count: 0 });
    }
}
