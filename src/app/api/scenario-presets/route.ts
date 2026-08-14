import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

export const runtime = 'nodejs';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data/scenarios/library/municipal_presets.json');
    const payload = JSON.parse(await readFile(filePath, 'utf8'));
    return NextResponse.json({
      presets: payload.presets ?? [],
      claimLevel: payload.claimLevel ?? 'proxy',
      source: 'data/scenarios/library/municipal_presets.json',
    });
  } catch (error) {
    console.error('Error loading scenario presets:', error);
    return NextResponse.json(
      { error: 'Failed to load scenario presets.' },
      { status: 500 },
    );
  }
}
