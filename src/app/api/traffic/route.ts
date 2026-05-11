import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'traffic_data.json');

    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json(
        { error: 'Traffic data not found. Please run the generate_traffic script first.' },
        { status: 404 }
      );
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const trafficData = JSON.parse(fileContent);

    return NextResponse.json(trafficData);
  } catch (error) {
    console.error('Error reading traffic data file:', error);
    return NextResponse.json(
      { error: 'Failed to load traffic data.' },
      { status: 500 }
    );
  }
}
