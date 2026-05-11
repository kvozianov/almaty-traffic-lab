import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'data', 'analytics_report.csv');

    try {
      await fs.access(filePath);
    } catch {
      return new NextResponse('Analytics report not found. Please run the generate_analytics script first.', { status: 404 });
    }

    const fileContent = await fs.readFile(filePath, 'utf-8');

    return new NextResponse(fileContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="analytics_report.csv"',
      },
    });
  } catch (error) {
    console.error('Error reading analytics report file:', error);
    return new NextResponse('Failed to load analytics report.', { status: 500 });
  }
}
