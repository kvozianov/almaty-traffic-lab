import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { exec } from 'child_process';
import util from 'util';

type Trip = {
  path: [number, number][];
  timestamps: number[];
};

type TripsPayload = {
  trips?: Trip[];
};

const MIN_TRIP_COUNT = 100;
const MAX_TRIP_COUNT = 5000;
const DEFAULT_TRIP_COUNT = 100;

const execAsync = util.promisify(exec);

export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    const requestedCount = getRequestedTripCount(request);
    const filePath = path.join(process.cwd(), 'data', 'trips.json');
    let tripsData = await readTripsPayload(filePath);

    if (!tripsData || !Array.isArray(tripsData.trips) || tripsData.trips.length === 0) {
      await execAsync(`python scripts/generate_trips.py ${requestedCount}`);
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

function getRequestedTripCount(request: NextRequest): number {
  const count = Number(request.nextUrl.searchParams.get('count') ?? DEFAULT_TRIP_COUNT);

  if (!Number.isFinite(count)) return DEFAULT_TRIP_COUNT;

  return Math.min(Math.max(Math.round(count), MIN_TRIP_COUNT), MAX_TRIP_COUNT);
}

function buildTripSample(sourceTrips: Trip[], requestedCount: number): Trip[] {
  if (sourceTrips.length === 0) return [];

  return Array.from({ length: requestedCount }, (_, index) => {
    const sourceTrip = sourceTrips[index % sourceTrips.length];
    const cycle = Math.floor(index / sourceTrips.length);
    const offset = cycle * 11 + (index % sourceTrips.length) * 0.33;

    return {
      path: sourceTrip.path,
      timestamps: sourceTrip.timestamps.map((timestamp) => Number((timestamp + offset).toFixed(2))),
    };
  });
}
