import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
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
    const tripsData = JSON.parse(fileContent);

    return NextResponse.json(tripsData);
  } catch (error) {
    console.error('Error reading trips data file:', error);
    return NextResponse.json(
      { error: 'Failed to load trips data.' },
      { status: 500 }
    );
  }
}
