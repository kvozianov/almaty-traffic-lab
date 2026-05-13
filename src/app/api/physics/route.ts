import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { exec } from 'child_process';
import util from 'util';

const execAsync = util.promisify(exec);

/**
 * Data Contract for Physics API (/api/physics):
 *
 * {
 *   "agents": [
 *     {
 *       "id": "1",
 *       "trajectory": [
 *         {"t": 0, "coord": [lng, lat], "v": 15.2, "a": 0.5},
 *         ...
 *       ]
 *     }
 *   ]
 * }
 */

export const runtime = 'nodejs';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'physics_trajectories.json');

    try {
      await fs.access(filePath);
    } catch {
      console.log('Physics trajectories data not found, generating...');
      await execAsync('python3 scripts/physics_engine.py');
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const physicsData = JSON.parse(fileContent);

    return NextResponse.json(physicsData);
  } catch (error) {
    console.error('Error handling physics request:', error);
    return NextResponse.json(
      { error: 'Failed to load physics data.' },
      { status: 500 }
    );
  }
}
