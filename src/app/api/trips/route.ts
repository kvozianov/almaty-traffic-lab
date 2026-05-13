import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { execFile } from 'child_process';
import util from 'util';

const execFileAsync = util.promisify(execFile);

type Trip = {
  type: 'car' | 'truck' | 'bus';
  path: [number, number][];
  timestamps: number[];
};

/**
 * Data Contract for Trips API (/api/trips):
 *
 * Query Params:
 *  - count: Optional. Number of trips to generate.
 *  - pattern: Optional. String ("normal" | "night" | "weekend"). Adjusts traffic behavior and density.
 *  - closed_streets: Optional. Comma-separated list of street names to close (e.g. "abay,al-farabi").
 *
 * {
 *   "trips": [
 *     {
 *       "type": "car" | "truck" | "bus",   // Defines agent rendering size/icon (Level 6)
 *       "path": [[lng, lat], ...],         // Sequence of geospatial coordinates
 *       "timestamps": [float, ...]         // Time in seconds to reach each coordinate, accounting for speed limits, vehicle type, and minor yielding delays
 *     },
 *     ...
 *   ]
 * }
 */

type TripsPayload = {
  trips?: Trip[];
};

const MIN_TRIP_COUNT = 10;
const MAX_TRIP_COUNT = 5000;
const DEFAULT_TRIP_COUNT = 100;

export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    const pattern = request.nextUrl.searchParams.get('pattern') || 'normal';
    const closedStreets = request.nextUrl.searchParams.get('closed_streets') || '';

    // Adjust default count if night mode
    let defaultCount = DEFAULT_TRIP_COUNT;
    if (pattern === 'night') {
        defaultCount = 30;
    }

    const requestedCount = getRequestedTripCount(request, defaultCount);

    // Create unique filename based on parameters to avoid cross-scenario pollution
    const fileName = `trips_${pattern.replace(/[^a-zA-Z0-9]/g, '')}${closedStreets ? '_' + closedStreets.replace(/[^a-zA-Z0-9]/g, '_') : ''}.json`;
    const filePath = path.join(process.cwd(), 'data', fileName);

    let tripsData = await readTripsPayload(filePath);

    if (!tripsData || !Array.isArray(tripsData.trips) || tripsData.trips.length === 0) {
      const args = ['scripts/generate_trips.py', '--num_trips', requestedCount.toString(), '--pattern', pattern, '--out', `data/${fileName}`];
      if (closedStreets) {
        args.push('--closed_streets', closedStreets);
      }
      await execFileAsync('python3', args);
      tripsData = await readTripsPayload(filePath);
    }

    return NextResponse.json({
      ...tripsData,
      trips: buildTripSample(Array.isArray(tripsData.trips) ? tripsData.trips : [], requestedCount),
    });
  } catch (error) {
    console.error('Error handling trips request:', error);
    return NextResponse.json(
      { error: 'Failed to process trips request.' },
      { status: 500 }
    );
  }
}

async function readTripsPayload(filePath: string): Promise<TripsPayload> {
  try {
    const fileContent = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(fileContent) as TripsPayload;
  } catch {
    return { trips: [] };
  }
}

function getRequestedTripCount(request: NextRequest, defaultCount: number = DEFAULT_TRIP_COUNT): number {
  const countParam = request.nextUrl.searchParams.get('count');
  const count = Number(countParam ?? defaultCount);

  if (!Number.isFinite(count)) return defaultCount;

  return Math.min(Math.max(Math.round(count), MIN_TRIP_COUNT), MAX_TRIP_COUNT);
}

function buildTripSample(sourceTrips: Trip[], requestedCount: number): Trip[] {
  if (sourceTrips.length === 0) return [];

  return Array.from({ length: requestedCount }, (_, index) => {
    const sourceTrip = sourceTrips[index % sourceTrips.length];
    const cycle = Math.floor(index / sourceTrips.length);
    const offset = cycle * 11 + (index % sourceTrips.length) * 0.33;

    return {
      type: sourceTrip.type || 'car',
      path: sourceTrip.path,
      timestamps: sourceTrip.timestamps.map((timestamp) => Number((timestamp + offset).toFixed(2))),
    };
  });
}
