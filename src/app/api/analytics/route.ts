import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { execFile } from 'child_process';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export const runtime = 'nodejs';

/**
 * Data Contract for Analytics API (/api/analytics):
 *
 * Query Params:
 *  - pattern: Optional. String ("normal" | "night" | "weekend"). Adjusts analytics outputs.
 *  - closed_streets: Optional. Comma-separated list of street names to close (e.g. "abay").
 *
 * {
 *   "summary": {
 *     "average_trip_time_seconds": float,
 *     "congestion_index": float,
 *     "total_active_vehicles": int
 *   },
 *   "node_throughput": [...],
 *   "time_series": [...],
 *   "ml_forecast": [...]
 * }
 */
export async function GET(request: NextRequest) {
  try {
    const pattern = request.nextUrl.searchParams.get('pattern') || 'normal';
    const closedStreets = request.nextUrl.searchParams.get('closed_streets') || '';

    const baseName = `analytics_${pattern.replace(/[^a-zA-Z0-9]/g, '')}${closedStreets ? '_' + closedStreets.replace(/[^a-zA-Z0-9]/g, '_') : ''}`;
    const filePath = path.join(process.cwd(), 'data', `${baseName}.json`);

    try {
      await fs.access(filePath);
    } catch {
      const args = ['scripts/generate_analytics.py', '--pattern', pattern];
      if (closedStreets) {
        args.push('--closed_streets', closedStreets);
      }
      await execFileAsync('python3', args);
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error reading analytics data file:', error);
    return NextResponse.json(
      { error: 'Failed to load analytics data.' },
      { status: 500 }
    );
  }
}
