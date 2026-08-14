import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import { readFile } from 'fs/promises';
import path from 'path';
import util from 'util';

const execFileAsync = util.promisify(execFile);

export const runtime = 'nodejs';

async function generateWorkflow(dossierPath = 'reports/dossiers/abay-signal-retiming/dossier.json') {
  const { stdout } = await execFileAsync('python3', [
    'scripts/generate_decision_workflow.py',
    '--dossier',
    dossierPath,
    '--out',
    'reports/workflows',
  ]);
  const summary = JSON.parse(stdout);
  const workflowFile = path.basename(String(summary.outputs.workflowJson));
  const workflowPath = path.join(process.cwd(), 'reports', 'workflows', workflowFile);
  return JSON.parse(await readFile(workflowPath, 'utf8'));
}

function allowedDossierPath(value: unknown) {
  const requested = String(value || 'reports/dossiers/abay-signal-retiming/dossier.json');
  if (!requested.startsWith('reports/dossiers/') || !requested.endsWith('/dossier.json')) {
    return 'reports/dossiers/abay-signal-retiming/dossier.json';
  }
  return requested;
}

export async function GET() {
  try {
    const workflow = await generateWorkflow();
    return NextResponse.json(workflow);
  } catch (error) {
    console.error('Error generating decision workflow:', error);
    return NextResponse.json(
      { error: 'Failed to generate decision workflow.' },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();
    const workflow = await generateWorkflow(allowedDossierPath(payload?.dossierPath));
    return NextResponse.json(workflow);
  } catch (error) {
    console.error('Error generating posted decision workflow:', error);
    return NextResponse.json(
      { error: 'Failed to generate decision workflow from dossier.' },
      { status: 500 },
    );
  }
}
