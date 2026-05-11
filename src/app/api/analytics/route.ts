import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'analytics.json');

    try {
      await fs.access(filePath);
    } catch {
      return NextResponse.json(
        { error: 'Analytics data not found. Please run the generate_analytics script first.' },
        { status: 404 }
      );
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error reading analytics data file:', error);
    return NextResponse.json(
      { error: 'Failed to load analytics data.' },
      { status: 500 }
    );
  }
}
