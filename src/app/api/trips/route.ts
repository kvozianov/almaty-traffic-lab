import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { exec } from 'child_process';
import util from 'util';

const execAsync = util.promisify(exec);

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const countParam = searchParams.get('count');
    let requestedCount = countParam ? parseInt(countParam, 10) : undefined;

    const filePath = path.join(process.cwd(), 'data', 'trips.json');

    let tripsData: { trips: any[] } = { trips: [] };
    let fileExists = false;

    try {
      await fs.access(filePath);
      fileExists = true;
      const fileContent = await fs.readFile(filePath, 'utf-8');
      tripsData = JSON.parse(fileContent);
    } catch {
      fileExists = false;
    }

    if (requestedCount !== undefined && !isNaN(requestedCount) && requestedCount > 0) {
        if (!fileExists || tripsData.trips.length < requestedCount) {
            // Need to generate on the fly
            console.log(`Generating ${requestedCount} trips on the fly...`);
            try {
                // Determine python executable, mostly 'python' works since we activate env or run in shell
                await execAsync(`python scripts/generate_trips.py ${requestedCount}`);

                const newFileContent = await fs.readFile(filePath, 'utf-8');
                tripsData = JSON.parse(newFileContent);
                // The newly generated file should have requestedCount trips, but just in case:
                tripsData.trips = tripsData.trips.slice(0, requestedCount);
            } catch (err) {
                console.error('Error generating trips:', err);
                return NextResponse.json(
                  { error: 'Failed to generate trips data on the fly.' },
                  { status: 500 }
                );
            }
        } else {
            // Slice the pre-generated large pool
            tripsData.trips = tripsData.trips.slice(0, requestedCount);
        }
    } else {
        if (!fileExists) {
             return NextResponse.json(
                { error: 'Trips data not found. Please run the generate_trips script first.' },
                { status: 404 }
              );
        }
    }

    return NextResponse.json(tripsData);
  } catch (error) {
    console.error('Error handling trips request:', error);
    return NextResponse.json(
      { error: 'Failed to process trips request.' },
      { status: 500 }
    );
  }
}
