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
 *   "uncontrolled_intersections": [
 *     {
 *       "coordinates": [lng, lat],
 *       "type": "uncontrolled_intersection"
 *     },
 *     ...
 *   ],
 *   "pedestrian_crossings": [
 *     {
 *       "coordinates": [lng, lat],
 *       "type": "pedestrian_crossing"
 *     },
 *     ...
 *   ]
 * }
 */

export const runtime = 'nodejs';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'physics.json');

    try {
      await fs.access(filePath);
    } catch {
      console.log('Physics data not found, generating...');
      await execAsync('python3 scripts/generate_physics.py');
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
