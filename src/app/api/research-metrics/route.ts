import { NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { readFile } from 'fs/promises';
import path from 'path';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export const runtime = 'nodejs';

export async function GET() {
  try {
    const { stdout } = await execFileAsync('python3', [
      'scripts/generate_research_metrics.py',
      '--dossier',
      'reports/dossiers/abay-signal-retiming/dossier.json',
      '--portfolio-matrix',
      'reports/portfolio/month1/kpi_matrix.csv',
      '--out',
      'reports/research_metrics/abay-signal-retiming',
    ]);
    const summary = JSON.parse(stdout);
    const metricsFile = path.basename(String(summary.outputs.json));
    const metricsPath = path.join(process.cwd(), 'reports', 'research_metrics', 'abay-signal-retiming', metricsFile);
    return NextResponse.json(JSON.parse(await readFile(metricsPath, 'utf8')));
  } catch (error) {
    console.error('Error generating research metrics:', error);
    return NextResponse.json(
      { error: 'Failed to generate research metrics.' },
      { status: 500 },
    );
  }
}
