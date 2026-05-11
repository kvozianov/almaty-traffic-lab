import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'almaty_roads.geojson');

    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json(
        { error: 'GeoJSON data not found. Please run the fetch script first.' },
        { status: 404 }
      );
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const validJsonContent = fileContent.replace(/([:[,\[]\s*)NaN(?=\s*[,}\]])/g, '$1null');
    const geojson = JSON.parse(validJsonContent);

    return NextResponse.json(geojson);
  } catch (error) {
    console.error('Error reading geojson file:', error);
    return NextResponse.json(
      { error: 'Failed to load Almaty roads data.' },
      { status: 500 }
    );
  }
}
