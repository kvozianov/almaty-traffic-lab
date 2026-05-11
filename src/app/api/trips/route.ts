import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

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

export async function GET(request: Request) {
  try {
    const filePath = path.join(process.cwd(), 'data', 'trips.json');

    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json(
        { error: 'Trips data not found. Please run the generate_trips script first.' },
        { status: 404 }
      );
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const tripsData = JSON.parse(fileContent) as TripsPayload;
    const requestedCount = getRequestedTripCount(request);

    return NextResponse.json({
      ...tripsData,
      trips: buildTripSample(Array.isArray(tripsData.trips) ? tripsData.trips : [], requestedCount),
    });
  } catch (error) {
    console.error('Error reading trips data file:', error);
    return NextResponse.json(
      { error: 'Failed to load trips data.' },
      { status: 500 }
    );
  }
}

function getRequestedTripCount(request: Request): number {
  const requestUrl = new URL(request.url);
  const count = Number(requestUrl.searchParams.get('count') ?? DEFAULT_TRIP_COUNT);

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
