/**
 * @typedef {[number, number]} Coordinate
 * @typedef {{ path: Coordinate[], timestamps: number[] }} TimestampedTrip
 * @typedef {{ path: [Coordinate, Coordinate], opacity: number }} TripTrailSegment
 */

/**
 * Builds the visible, fading portion of timestamped routes for a single animation frame.
 *
 * @param {TimestampedTrip[]} data
 * @param {number} currentTime
 * @param {number} trailLength
 * @returns {TripTrailSegment[]}
 */
export function buildTripTrailSegments(data, currentTime, trailLength) {
  if (!Number.isFinite(currentTime) || !Number.isFinite(trailLength) || trailLength <= 0) return [];

  const trailStart = currentTime - trailLength;
  /** @type {TripTrailSegment[]} */
  const segments = [];

  for (const trip of data) {
    const pointCount = Math.min(trip.path.length, trip.timestamps.length);
    const firstVisibleEndIndex = firstTimestampAfter(trip.timestamps, trailStart, pointCount);

    for (let index = Math.max(1, firstVisibleEndIndex); index < pointCount; index += 1) {
      const segmentStartTime = trip.timestamps[index - 1];
      const segmentEndTime = trip.timestamps[index];

      if (segmentStartTime >= currentTime) break;

      if (
        !Number.isFinite(segmentStartTime) ||
        !Number.isFinite(segmentEndTime) ||
        segmentEndTime <= segmentStartTime ||
        segmentEndTime <= trailStart ||
        segmentStartTime >= currentTime
      ) {
        continue;
      }

      const visibleStartTime = Math.max(segmentStartTime, trailStart);
      const visibleEndTime = Math.min(segmentEndTime, currentTime);
      if (visibleEndTime <= visibleStartTime) continue;

      const duration = segmentEndTime - segmentStartTime;
      const source = interpolateCoordinate(
        trip.path[index - 1],
        trip.path[index],
        (visibleStartTime - segmentStartTime) / duration,
      );
      const target = interpolateCoordinate(
        trip.path[index - 1],
        trip.path[index],
        (visibleEndTime - segmentStartTime) / duration,
      );
      const segmentMidpointTime = (visibleStartTime + visibleEndTime) / 2;
      const trailProgress = clamp01(1 - (currentTime - segmentMidpointTime) / trailLength);

      segments.push({
        path: [source, target],
        opacity: 0.12 + trailProgress * 0.88,
      });
    }
  }

  return segments;
}

/**
 * Timestamp arrays are monotonic by the trip payload contract. Binary search keeps
 * each animation frame proportional to the visible trail instead of the full route.
 *
 * @param {number[]} timestamps
 * @param {number} threshold
 * @param {number} pointCount
 */
function firstTimestampAfter(timestamps, threshold, pointCount) {
  let low = 0;
  let high = pointCount;

  while (low < high) {
    const middle = low + Math.floor((high - low) / 2);
    if (timestamps[middle] <= threshold) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }

  return low;
}

/** @param {Coordinate} a @param {Coordinate} b @param {number} progress @returns {Coordinate} */
function interpolateCoordinate(a, b, progress) {
  const clamped = clamp01(progress);
  return [a[0] + (b[0] - a[0]) * clamped, a[1] + (b[1] - a[1]) * clamped];
}

/** @param {number} value */
function clamp01(value) {
  return Math.min(Math.max(value, 0), 1);
}
