import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    return NextResponse.json(
        {
            detail: "Backtesting requires the Python engine. Run the backend locally: python -m uvicorn dashboard.api.main:app --port 8000",
            error: "backend_required",
        },
        { status: 503 }
    );
}
