import { NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { readFile } from 'fs/promises';
import path from 'path';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export const runtime = 'nodejs';

export async function GET() {
  try {
    const registryPath = path.join(process.cwd(), 'reports', 'data_sources', 'provider_registry.json');
    try {
      return NextResponse.json(JSON.parse(await readFile(registryPath, 'utf8')));
    } catch {
      await execFileAsync('python3', ['scripts/refresh_data_sources.py', '--out', 'reports/data_sources']);
      return NextResponse.json(JSON.parse(await readFile(registryPath, 'utf8')));
    }
  } catch (error) {
    console.error('Error loading data-source registry:', error);
    return NextResponse.json(
      { error: 'Failed to load data-source registry.' },
      { status: 500 },
    );
  }
}
