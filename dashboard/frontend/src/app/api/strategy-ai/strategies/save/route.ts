import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { v4 as uuidv4 } from 'uuid';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const stratId = uuidv4().slice(0, 8);

        const row = {
            id: stratId,
            name: body.name || '',
            description: body.description || '',
            legs: body.legs || [],
            entry_time: body.entry_time || '09:20',
            exit_time: body.exit_time || '15:15',
            sl_pct: body.sl_pct ?? 25.0,
            sl_type: body.sl_type || 'hard',
            target_pct: body.target_pct ?? 0.0,
            target_type: body.target_type || 'hard',
            lot_size: body.lot_size ?? 25,
            vix_min: body.vix_min ?? null,
            vix_max: body.vix_max ?? null,
            dte_min: body.dte_min ?? null,
            dte_max: body.dte_max ?? null,
        };

        const { error } = await supabase.from('ai_strategies').upsert(row);
        if (error) throw error;

        return NextResponse.json({ status: 'saved', id: stratId, strategy: row });
    } catch (e: any) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}
