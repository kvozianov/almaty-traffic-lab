import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { mkdir, readFile, writeFile } from 'fs/promises';
import path from 'path';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export const runtime = 'nodejs';

async function generateFromIncidentFile(incidentPath: string) {
  const { stdout } = await execFileAsync('python3', [
    'scripts/generate_operation_playbook.py',
    '--incident',
    incidentPath,
    '--out',
    'reports/operations',
  ]);
  const summary = JSON.parse(stdout);
  const playbookFile = path.basename(String(summary.outputs.playbookJson));
  const playbookPath = path.join(process.cwd(), 'reports', 'operations', playbookFile);
  return JSON.parse(await readFile(playbookPath, 'utf8'));
}

function safeIncidentId(value: unknown) {
  const raw = String(value || 'operator-request-incident').toLowerCase();
  return raw.replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'operator-request-incident';
}

export async function GET() {
  try {
    const playbook = await generateFromIncidentFile('data/operations/sample_incident_abay.json');
    return NextResponse.json(playbook);
  } catch (error) {
    console.error('Error generating operational playbook:', error);
    return NextResponse.json(
      { error: 'Failed to generate operational playbook.' },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const incident = await request.json();
    const incidentId = safeIncidentId(incident?.id);
    const requestDir = path.join(process.cwd(), 'reports', 'operations', 'requests');
    const requestPath = path.join(requestDir, `${incidentId}.json`);
    await mkdir(requestDir, { recursive: true });
    await writeFile(requestPath, JSON.stringify(incident, null, 2), 'utf8');
    const playbook = await generateFromIncidentFile(path.relative(process.cwd(), requestPath));
    return NextResponse.json(playbook);
  } catch (error) {
    console.error('Error generating posted operational playbook:', error);
    return NextResponse.json(
      { error: 'Failed to generate operational playbook from incident.' },
      { status: 500 },
    );
  }
}
