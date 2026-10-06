import type { Change, PeriodId, RawCityGraph, Scenario } from "./engine/types";

type ExampleChange =
  | { type: "close" | "busLane" | "addLane" | "greenWave"; street: string; from: string }
  | { type: "speedLimit"; street: string; from: string; kmh: number }
  | Extract<Change, { type: "development" }>;

export interface Example {
  id: string;
  title: string;
  question: string;
  period: PeriodId;
  changes: ExampleChange[];
}

/**
 * Starter questions on the home page. Sections are referenced by street name
 * and the start of their label so the examples survive a graph rebuild.
 */
export const EXAMPLES: Example[] = [
  {
    id: "abay-repairs",
    title: "Abay Avenue closes for repairs",
    question: "Two central blocks of Abay are closed in the morning rush. Where do the cars go?",
    period: "am",
    changes: [
      { type: "close", street: "Abay Avenue", from: "Zharokov St" },
      { type: "close", street: "Abay Avenue", from: "Manas St" },
    ],
  },
  {
    id: "tole-bi-bus-lane",
    title: "A bus lane on Tole Bi Street",
    question: "One lane in each direction goes to buses between Rozybakiev and Zheltoksan.",
    period: "am",
    changes: [
      { type: "busLane", street: "Tole Bi Street", from: "Rozybakiev St" },
      { type: "busLane", street: "Tole Bi Street", from: "Auezov St" },
      { type: "busLane", street: "Tole Bi Street", from: "Mukanov St" },
      { type: "busLane", street: "Tole Bi Street", from: "Baitursynuly St" },
    ],
  },
  {
    id: "new-housing",
    title: "3,000 new apartments in the west",
    question: "A housing estate opens near Sain Street. What does it add to the morning commute?",
    period: "am",
    changes: [{ type: "development", kind: "housing", lon: 76.838, lat: 43.236, size: 3000 }],
  },
  {
    id: "dostyk-green",
    title: "More green time on Dostyk Avenue",
    question: "Signals favour Dostyk in the evening peak. Who pays for it at the crossings?",
    period: "pm",
    changes: [
      { type: "greenWave", street: "Dostyk Avenue", from: "Kazhimukan St" },
      { type: "greenWave", street: "Dostyk Avenue", from: "Zholdasbekov St" },
      { type: "greenWave", street: "Dostyk Avenue", from: "Abay Ave" },
    ],
  },
];

export function findSection(graph: RawCityGraph, street: string, from: string): number {
  const id = graph.streets.findIndex((s) => s.name === street);
  return graph.sections.findIndex((s) => s.street === id && s.label.startsWith(from));
}

export function resolveExample(graph: RawCityGraph, example: Example): Scenario {
  const changes: Change[] = [];
  for (const c of example.changes) {
    if (c.type === "development") {
      changes.push(c);
      continue;
    }
    const section = findSection(graph, c.street, c.from);
    if (section < 0) continue;
    changes.push(c.type === "speedLimit" ? { type: c.type, section, kmh: c.kmh } : { type: c.type, section });
  }
  return { v: 1, period: example.period, changes };
}
