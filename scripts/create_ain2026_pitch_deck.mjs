import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ARTIFACT_TOOL_PATH =
  process.env.ARTIFACT_TOOL_PATH ||
  "/Users/kirill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/@oai+artifact-tool@file+local-deps+-oai-artifact-tool-oai-artifact_tool-2.8.11.tgz/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const { Presentation, PresentationFile } = await import(ARTIFACT_TOOL_PATH);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..");
const WORKSPACE =
  process.env.PRESENTATION_WORKSPACE ||
  path.join(
    "/tmp",
    "codex-presentations",
    "manual-ain2026",
    "almaty-mobility-lab",
  );

const TMP_DIR = path.join(WORKSPACE, "tmp");
const PREVIEW_DIR = path.join(TMP_DIR, "preview");
const LAYOUT_DIR = path.join(TMP_DIR, "layout");
const QA_DIR = path.join(TMP_DIR, "qa");
const OUTPUT_DIR = path.join(PROJECT_ROOT, "reports", "pitch");
const FINAL_PPTX = path.join(
  OUTPUT_DIR,
  "almaty_mobility_lab_ain2026_pitch_deck.pptx",
);
const DOWNLOADS_COPY =
  "/Users/kirill/Downloads/Almaty_Mobility_Lab_AIN2026_Pitch_Deck.pptx";

const W = 1280;
const H = 720;

const C = {
  ink: "#102033",
  ink2: "#1E3348",
  muted: "#62748A",
  bg: "#F5F8FB",
  white: "#FFFFFF",
  line: "#D9E4EE",
  line2: "#C4D2E0",
  teal: "#008C89",
  tealDark: "#006B68",
  tealSoft: "#DDF3F1",
  yellow: "#F5C95A",
  yellowSoft: "#FFF4D1",
  red: "#E86655",
  redSoft: "#FFE6E1",
  green: "#2C9C62",
  greenSoft: "#DFF3E8",
  blueSoft: "#E5EEF9",
  dark: "#0B1F33",
  dark2: "#12314F",
};

const FONT_HEAD = "Aptos Display";
const FONT_BODY = "Aptos";

const noLine = { style: "solid", fill: "none", width: 0 };
const thinLine = (fill = C.line, width = 1) => ({
  style: "solid",
  fill,
  width,
});

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, text, position, style = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: noLine,
  });
  box.text = text;
  box.text.style = {
    typeface: FONT_BODY,
    fontSize: 20,
    color: C.ink,
    ...style,
  };
  return box;
}

function addTitle(slide, eyebrow, title, subtitle, opts = {}) {
  const color = opts.dark ? C.white : C.ink;
  const muted = opts.dark ? "#B9CAD9" : C.muted;
  addText(slide, eyebrow, { left: 74, top: 42, width: 540, height: 24 }, {
    fontSize: 13,
    bold: true,
    color: opts.accent || C.teal,
  });
  addText(slide, title, { left: 72, top: 88, width: opts.width || 760, height: 128 }, {
    typeface: FONT_HEAD,
    fontSize: opts.size || 44,
    bold: true,
    color,
  });
  if (subtitle) {
    addText(slide, subtitle, { left: 74, top: opts.subTop || 218, width: opts.subWidth || 680, height: 78 }, {
      fontSize: opts.subSize || 22,
      color: muted,
    });
  }
}

function footer(slide, n, dark = false) {
  addText(slide, "Almaty Mobility Lab", { left: 72, top: 675, width: 260, height: 22 }, {
    fontSize: 11,
    bold: true,
    color: dark ? "#AFC2D5" : "#7A8EA3",
  });
  addText(slide, String(n).padStart(2, "0"), { left: 1166, top: 675, width: 42, height: 22 }, {
    fontSize: 11,
    bold: true,
    color: dark ? "#AFC2D5" : "#7A8EA3",
    alignment: "right",
  });
}

function pill(slide, text, position, fill, color = C.ink, border = "none") {
  const p = slide.shapes.add({
    geometry: "roundRect",
    position,
    fill,
    line: border === "none" ? noLine : thinLine(border),
    borderRadius: "rounded-full",
  });
  p.text = text;
  p.text.style = {
    typeface: FONT_BODY,
    fontSize: 13,
    bold: true,
    color,
    alignment: "center",
  };
  return p;
}

function card(slide, title, body, position, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "roundRect",
    position,
    fill: opts.fill || C.white,
    line: thinLine(opts.line || C.line),
    borderRadius: opts.radius || "rounded-xl",
    shadow: opts.shadow || "shadow-sm",
  });
  if (opts.accent) {
    slide.shapes.add({
      geometry: "rect",
      position: { left: position.left, top: position.top, width: 7, height: position.height },
      fill: opts.accent,
      line: noLine,
    });
  }
  addText(slide, title, {
    left: position.left + 22,
    top: position.top + 20,
    width: position.width - 44,
    height: opts.titleHeight || 30,
  }, {
    fontSize: opts.titleSize || 21,
    bold: true,
    color: opts.titleColor || C.ink,
  });
  addText(slide, body, {
    left: position.left + 22,
    top: position.top + (opts.bodyTop || 62),
    width: position.width - 44,
    height: position.height - (opts.bodyTop || 62) - 18,
  }, {
    fontSize: opts.bodySize || 16,
    color: opts.bodyColor || C.muted,
  });
  return shape;
}

function metric(slide, value, label, position, opts = {}) {
  const box = slide.shapes.add({
    geometry: "roundRect",
    position,
    fill: opts.fill || C.white,
    line: thinLine(opts.line || C.line),
    borderRadius: "rounded-xl",
    shadow: "shadow-sm",
  });
  addText(slide, value, {
    left: position.left + 18,
    top: position.top + 15,
    width: position.width - 36,
    height: 44,
  }, {
    typeface: FONT_HEAD,
    fontSize: opts.valueSize || 32,
    bold: true,
    color: opts.color || C.teal,
  });
  addText(slide, label, {
    left: position.left + 18,
    top: position.top + 62,
    width: position.width - 36,
    height: 42,
  }, {
    fontSize: 14,
    color: opts.labelColor || C.muted,
  });
  return box;
}

function roadSketch(slide, x, y, w, h, opts = {}) {
  const bg = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill || C.white,
    line: thinLine(opts.line || C.line),
    borderRadius: "rounded-2xl",
    shadow: opts.shadow || "shadow-sm",
  });
  const roads = [
    [0.08, 0.26, 0.86, 0.02, "#CCD8E3", 7],
    [0.08, 0.54, 0.78, -0.05, "#CCD8E3", 7],
    [0.16, 0.82, 0.68, -0.15, "#CCD8E3", 7],
    [0.25, 0.16, 0.00, 0.70, "#CCD8E3", 7],
    [0.52, 0.14, -0.05, 0.72, "#CCD8E3", 7],
    [0.78, 0.18, -0.12, 0.66, "#CCD8E3", 7],
  ];
  for (const [rx, ry, rw, rh, color, width] of roads) {
    slide.shapes.add({
      geometry: "line",
      position: { left: x + rx * w, top: y + ry * h, width: rw * w, height: rh * h },
      fill: "none",
      line: { style: "solid", fill: color, width },
    });
  }
  slide.shapes.add({
    geometry: "line",
    position: { left: x + 0.13 * w, top: y + 0.54 * h, width: 0.72 * w, height: -0.05 * h },
    fill: "none",
    line: { style: "solid", fill: opts.routeColor || C.teal, width: 11 },
  });
  for (const px of [0.13, 0.44, 0.85]) {
    slide.shapes.add({
      geometry: "ellipse",
      position: { left: x + px * w - 9, top: y + 0.52 * h - 9, width: 18, height: 18 },
      fill: opts.routeColor || C.teal,
      line: { style: "solid", fill: C.white, width: 2 },
    });
  }
  return bg;
}

function dossierSketch(slide, x, y, w, h, opts = {}) {
  const compact = opts.compact ?? (w < 360 || h < 300);
  const root = slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill: C.white,
    line: thinLine(C.line),
    borderRadius: "rounded-2xl",
    shadow: "shadow-md",
  });
  addText(slide, "Досье решения", {
    left: x + 24,
    top: y + 20,
    width: compact ? w - 48 : w - 210,
    height: 34,
  }, {
    fontSize: compact ? 21 : 24,
    bold: true,
    color: C.ink,
  });
  if (compact) {
    pill(slide, opts.level || "оценка", {
      left: x + 24,
      top: y + 58,
      width: 122,
      height: 26,
    }, C.yellowSoft, "#7A5600", "#F0D27E");
  } else {
    pill(slide, opts.level || "уровень: оценка", {
      left: x + w - 168,
      top: y + 24,
      width: 132,
      height: 28,
    }, C.yellowSoft, "#7A5600", "#F0D27E");
  }
  const fullLines = [
    ["Участок дороги", "Абая: тестовый пример"],
    ["Вариант изменения", "светофор / объезд / автобус"],
    ["Показатели", "задержка, нагрузка, автобусы"],
    ["Чего не хватает", "замеры, планы светофоров"],
  ];
  const compactLines = [
    ["Участок", "Абая"],
    ["Тест", "светофор / объезд"],
    ["Вывод", "досье + уровень доверия"],
  ];
  const lines = compact ? compactLines : fullLines;
  const gap = compact ? 8 : 12;
  const topStart = compact ? y + 98 : y + 78;
  const bottomPad = compact ? 20 : 24;
  const rowH = Math.min(compact ? 42 : 52, (y + h - bottomPad - topStart - gap * (lines.length - 1)) / lines.length);
  let top = topStart;
  for (const [label, val] of lines) {
    slide.shapes.add({
      geometry: "roundRect",
      position: { left: x + 24, top, width: w - 48, height: rowH },
      fill: "#F7FAFD",
      line: thinLine("#E4ECF4"),
      borderRadius: "rounded-lg",
    });
    addText(slide, label, {
      left: x + 40,
      top: top + (compact ? 9 : 10),
      width: compact ? 88 : 150,
      height: 22,
    }, {
      fontSize: compact ? 10 : 12,
      bold: true,
      color: C.teal,
    });
    addText(slide, val, {
      left: x + (compact ? 132 : 198),
      top: top + (compact ? 8 : 9),
      width: w - (compact ? 158 : 236),
      height: rowH - 10,
    }, {
      fontSize: compact ? 12 : 14,
      color: C.ink,
    });
    top += rowH + gap;
  }
  return root;
}

function stepFlow(slide, steps, x, y, w, opts = {}) {
  const gap = opts.gap || 18;
  const nodeW = (w - gap * (steps.length - 1)) / steps.length;
  const nodes = [];
  for (let i = 0; i < steps.length; i += 1) {
    const node = slide.shapes.add({
      geometry: "roundRect",
      position: { left: x + i * (nodeW + gap), top: y, width: nodeW, height: opts.height || 96 },
      fill: opts.fills?.[i] || C.white,
      line: thinLine(opts.lines?.[i] || C.line),
      borderRadius: "rounded-xl",
      shadow: "shadow-sm",
    });
    addText(slide, String(i + 1), {
      left: x + i * (nodeW + gap) + 16,
      top: y + 16,
      width: 28,
      height: 24,
    }, {
      fontSize: 14,
      bold: true,
      color: opts.numColor || C.teal,
    });
    addText(slide, steps[i], {
      left: x + i * (nodeW + gap) + 16,
      top: y + 42,
      width: nodeW - 32,
      height: (opts.height || 96) - 50,
    }, {
      fontSize: opts.fontSize || 16,
      bold: true,
      color: opts.textColor || C.ink,
    });
    nodes.push(node);
  }
  for (let i = 0; i < nodes.length - 1; i += 1) {
    addText(slide, "→", {
      left: x + (i + 1) * nodeW + i * gap + 2,
      top: y + ((opts.height || 96) - 36) / 2,
      width: gap - 4,
      height: 36,
    }, {
      fontSize: 22,
      bold: true,
      color: opts.arrowColor || C.teal,
      alignment: "center",
    });
  }
  return nodes;
}

function darkBand(slide, title, subtitle) {
  slide.background.fill = C.dark;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: W, height: H },
    fill: C.dark,
    line: noLine,
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 18, height: H },
    fill: C.teal,
    line: noLine,
  });
  addTitle(slide, "ASTANA INNOVATIONS ACCELERATOR 2026", title, subtitle, {
    dark: true,
    accent: C.yellow,
    width: 780,
    subWidth: 660,
  });
}

const slidePlan = [
  ["Титул", "Проверка дорожных изменений до запуска на улице"],
  ["Проблема", "Город меняет дорогу, но часто не видит последствия заранее"],
  ["Что это", "Выберите участок, проверьте вариант изменения, получите досье решения"],
  ["Как работает", "От дорожной ситуации к проверяемому выводу"],
  ["Пример", "Участок Абая как тестовый пример"],
  ["Что видит специалист", "Понятный экран без сырых технических деталей"],
  ["Досье решения", "Итог — материал для обсуждения пилота"],
  ["Доверие", "Каждое число получает уровень доказательств"],
  ["Статус", "Что есть, что проверяем, чего не заявляем"],
  ["AIA fit", "AIA закрывает главный разрыв: данные и городской пилот"],
  ["План пилота", "Один маршрут, 2-3 варианта изменения, одно досье"],
  ["Ценность и модель", "Меньше риск дорогого решения на слабых данных"],
  ["Техническое приложение", "Что внутри системы"],
  ["Запрос и контакты", "Что нужно от акселератора"],
];

const sourceNotes = `Sources and claim boundaries

User-provided context:
- Project name: Almaty Mobility Lab.
- Founder: Kirill Vozianov, vks151109@gmail.com, Telegram @owers3g, +7 771 216 27 28.
- User requested simple Russian and replacement of internal analytics terms with clear municipal wording in main slides.

Local project sources:
- AMDP Product Audit 2026: enough for accelerator application if framed as decision-support, not as a ready procurement item.
- Claim Ledger: application pack demo; indicators/dossier proxy; road geometry real-data snapshot.
- Local Abay road-area pack: Abay is a first internal/test example, not an official city pilot.
- Akimat application package: current safe position is reproducible proxy-level dossier with run metadata, indicator deltas, source labels, limitations, workflow evidence, and procurement checklist artifacts.

Official external source:
- Astana Hub AIA 2026 page, accessed 2026-06-15: AIA supports digital city solutions for Astana, access to city data, direct client/pilot support, and transport challenges around traffic lights and route optimization.

Deck claim posture:
- No official partnership, city data access agreement, real deployment, automatic traffic-light control, guaranteed congestion effect, ready procurement status, or full-city traffic model is claimed.
`;

const deckPlan = `Slide plan and visual style

Mode: create.
Audience: Astana Innovations Accelerator 2026 jury.
Language: Russian, simple municipal wording.
Main vocabulary: участок дороги, маршрут, вариант изменения, дорожная ситуация, тест меры, показатели, уровень доказательств, досье решения.
Technical terms are kept to the technical appendix.

Palette:
- Dominant: deep municipal navy ${C.dark} / light civic background ${C.bg}
- Supporting: teal ${C.teal}, white surfaces ${C.white}, line ${C.line}
- Accent: road yellow ${C.yellow}, controlled risk red ${C.red}, verification green ${C.green}

Typeface: Aptos Display for headings, Aptos for body.
Visual motif: schematic road segment + dossier page + claim label ladder.
No raw screenshots. No unverified logos. No large unsupported metrics.

Slides:
${slidePlan.map((s, idx) => `${idx + 1}. ${s[0]} — ${s[1]}`).join("\n")}
`;

await fs.mkdir(PREVIEW_DIR, { recursive: true });
await fs.mkdir(LAYOUT_DIR, { recursive: true });
await fs.mkdir(QA_DIR, { recursive: true });
await fs.mkdir(OUTPUT_DIR, { recursive: true });
await fs.writeFile(path.join(TMP_DIR, "source-notes.txt"), sourceNotes);
await fs.writeFile(path.join(TMP_DIR, "slide-plan.txt"), deckPlan);

const presentation = Presentation.create({
  slideSize: { width: W, height: H },
});

function addSlide(bg = C.bg) {
  const slide = presentation.slides.add();
  slide.background.fill = bg;
  return slide;
}

// 1. Cover
{
  const s = addSlide(C.dark);
  darkBand(s, "Almaty Mobility Lab", "Проверка дорожных изменений до запуска на улице");
  addText(s, "Мы не заменяем решение города. Мы делаем его проверяемым.", {
    left: 74,
    top: 322,
    width: 640,
    height: 72,
  }, {
    fontSize: 27,
    bold: true,
    color: C.white,
  });
  roadSketch(s, 790, 106, 358, 252, { fill: "#12314F", line: "#274B6A", routeColor: C.yellow, shadow: "shadow-lg" });
  dossierSketch(s, 820, 324, 326, 262, { level: "демо / оценка", compact: true });
  pill(s, "Презентация для жюри AIA 2026", { left: 74, top: 426, width: 292, height: 34 }, "#163B5E", "#D8E6F4", "#2C5577");
  addText(s, "Основатель: Kirill Vozianov", { left: 74, top: 600, width: 340, height: 28 }, {
    fontSize: 16,
    color: "#B9CAD9",
  });
  footer(s, 1, true);
  s.speakerNotes.textFrame.setText("Открыть с простой мыслью: это не система, которая сама управляет городом. Это способ заранее проверить дорожное изменение и собрать досье решения для обсуждения пилота.");
}

// 2. Problem
{
  const s = addSlide();
  addTitle(s, "ПРОБЛЕМА", "Город меняет дорогу, но часто не видит последствия заранее", "Решения по светофорам, ремонтам, автобусам и объездам несут ответственность, но данные и допущения часто разбросаны.");
  const cards = [
    ["Что хотят изменить", "светофор, ремонтный объезд, автобусный приоритет, тестовая дорожная ситуация", C.blueSoft],
    ["Что нужно понять", "как изменятся задержка, нагрузка, время в пути и влияние на маршруты", C.tealSoft],
    ["Что часто теряется", "откуда взяты данные, какие допущения слабые, можно ли идти в пилот", C.redSoft],
  ];
  cards.forEach(([title, body, fill], i) => {
    card(s, title, body, { left: 72 + i * 378, top: 376, width: 338, height: 164 }, {
      fill,
      line: "transparent",
      bodySize: 17,
      accent: i === 2 ? C.red : C.teal,
    });
  });
  addText(s, "Главный риск: красивое решение запускают раньше, чем понятно, на каких данных оно держится.", {
    left: 74,
    top: 312,
    width: 780,
    height: 36,
  }, {
    fontSize: 22,
    bold: true,
    color: C.ink,
  });
  footer(s, 2);
  s.speakerNotes.textFrame.setText("Проблема не в отсутствии карт. Проблема в том, что перед запуском меры городу нужен один проверяемый пакет: что меняем, что ожидаем, что знаем, чего не хватает.");
}

// 3. What it is
{
  const s = addSlide();
  addTitle(s, "ЧТО ЭТО", "Платформа проверяет дорожные изменения до запуска", "Выбираете участок дороги или маршрут, задаете вариант изменения и видите, что может случиться с движением.", {
    width: 760,
    subTop: 232,
  });
  stepFlow(s, [
    "Участок дороги или маршрут",
    "Вариант изменения",
    "Модельная проверка",
    "Показатели и пробелы",
    "Досье решения",
  ], 72, 332, 1136, { height: 116, fontSize: 15 });
  addText(s, "Пример варианта изменения: перенастройка светофора, автобусный приоритет, ремонтный объезд или искусственный инцидент для проверки устойчивости.", {
    left: 112,
    top: 500,
    width: 920,
    height: 62,
  }, {
    fontSize: 21,
    color: C.ink2,
  });
  pill(s, "решение остается за городом", { left: 900, top: 206, width: 244, height: 34 }, C.tealSoft, C.tealDark, "#B8E5E1");
  footer(s, 3);
  s.speakerNotes.textFrame.setText("Здесь важно объяснить продукт одной фразой: город выбирает участок и проверяет вариант изменения до запуска на улице.");
}

// 4. How it works
{
  const s = addSlide();
  addTitle(s, "КАК РАБОТАЕТ", "От дорожной ситуации к проверяемому выводу", "Система не прячет слабые места: вместе с результатом она показывает источники, ограничения и недостающие данные.");
  roadSketch(s, 78, 278, 420, 250);
  addText(s, "Вход", { left: 104, top: 298, width: 120, height: 26 }, { fontSize: 14, bold: true, color: C.teal });
  card(s, "Модельная проверка", "сравнивает “как сейчас” и “что может измениться”, не выдавая приближенный расчет за доказанный факт", {
    left: 550,
    top: 304,
    width: 280,
    height: 160,
  }, { fill: C.tealSoft, line: "#B8E5E1", accent: C.teal, bodySize: 16 });
  dossierSketch(s, 880, 226, 300, 310, { level: "оценка" });
  addText(s, "→", { left: 508, top: 366, width: 34, height: 42 }, {
    fontSize: 32,
    bold: true,
    color: C.teal,
    alignment: "center",
  });
  addText(s, "→", { left: 838, top: 366, width: 34, height: 42 }, {
    fontSize: 32,
    bold: true,
    color: C.teal,
    alignment: "center",
  });
  footer(s, 4);
  s.speakerNotes.textFrame.setText("Показать, что это не черный ящик: на входе дорожная сеть и данные, внутри проверка изменения, на выходе досье с ограничениями.");
}

// 5. Example
{
  const s = addSlide();
  addTitle(s, "ПЕРВЫЙ ПРИМЕР", "Участок Абая как тестовый пример", "Это внутренний пример для демонстрации логики продукта, а не заявление об официальном городском проекте.");
  roadSketch(s, 82, 292, 500, 268, { routeColor: C.teal });
  const examples = [
    ["Изменить режим светофора", "проверить, где может снизиться задержка"],
    ["Автобусный приоритет", "оценить влияние на общественный транспорт"],
    ["Ремонтный объезд", "понять нагрузку на соседние улицы"],
    ["Искусственный инцидент", "проверить устойчивость маршрута"],
  ];
  examples.forEach(([title, body], i) => {
    const x = 650 + (i % 2) * 268;
    const y = 292 + Math.floor(i / 2) * 144;
    card(s, title, body, { left: x, top: y, width: 236, height: 112 }, {
      fill: i === 3 ? C.yellowSoft : C.white,
      bodySize: 14,
      titleSize: 18,
      accent: i === 3 ? C.yellow : C.teal,
    });
  });
  pill(s, "уровень текущего примера: демо / оценка", { left: 80, top: 582, width: 330, height: 34 }, C.yellowSoft, "#7A5600", "#F0D27E");
  footer(s, 5);
  s.speakerNotes.textFrame.setText("Abay нужен как понятный пример. Для AIA тот же подход переносится на выбранный участок или маршрут в Астане после доступа к данным и городского эксперта.");
}

// 6. Specialist view
{
  const s = addSlide();
  addTitle(s, "ЧТО ВИДИТ СПЕЦИАЛИСТ", "Не сырой скриншот, а понятная рабочая картина", "На одном экране видно: участок, вариант изменения, показатели, уровень доверия и недостающие данные.");
  s.shapes.add({
    geometry: "roundRect",
    position: { left: 76, top: 300, width: 1128, height: 318 },
    fill: C.white,
    line: thinLine(C.line),
    borderRadius: "rounded-2xl",
    shadow: "shadow-md",
  });
  roadSketch(s, 108, 338, 300, 176, { fill: "#F8FBFD", routeColor: C.teal });
  addText(s, "Участок дороги", { left: 128, top: 532, width: 220, height: 24 }, { fontSize: 14, bold: true, color: C.teal });
  metric(s, "было", "текущая дорожная ситуация", { left: 462, top: 344, width: 180, height: 112 }, { color: C.muted, fill: "#F7FAFD" });
  metric(s, "после", "после варианта изменения", { left: 662, top: 344, width: 210, height: 112 }, { color: C.teal, fill: C.tealSoft, line: "#B8E5E1", valueSize: 32 });
  metric(s, "оценка", "уровень доказательств", { left: 902, top: 344, width: 210, height: 112 }, { color: "#8A6200", fill: C.yellowSoft, line: "#EED27A", valueSize: 30 });
  card(s, "Чего не хватает для доверия", "замеры скорости, планы светофоров, данные автобусов, стоимость меры", {
    left: 462,
    top: 488,
    width: 650,
    height: 112,
  }, { fill: C.redSoft, line: "#F0B6AD", accent: C.red, bodySize: 17 });
  footer(s, 6);
  s.speakerNotes.textFrame.setText("Из-за сырого внешнего вида приложения в deck используем схему интерфейса. Главное: что пользователь понимает и какое решение может принять.");
}

// 7. Dossier
{
  const s = addSlide();
  addTitle(s, "ДОСЬЕ РЕШЕНИЯ", "Итог — материал для обсуждения пилота", "Если город ничего не забирает из системы, кроме досье, ценность уже есть: все аргументы и ограничения собраны в одном месте.");
  dossierSketch(s, 92, 310, 430, 320, { level: "демо / оценка" });
  const outputs = [
    ["Что проверяли", "участок дороги, маршрут или тестовая дорожная ситуация"],
    ["Что изменилось", "показатели “как сейчас” и “что может измениться”"],
    ["Можно ли доверять", "уровень доказательств и список недостающих данных"],
    ["Что делать дальше", "идти в пилот, отложить или запросить данные"],
  ];
  outputs.forEach(([title, body], i) => {
    card(s, title, body, { left: 586, top: 310 + i * 78, width: 560, height: 62 }, {
      fill: i === 3 ? C.tealSoft : C.white,
      titleSize: 17,
      titleHeight: 20,
      bodyTop: 38,
      bodySize: 14,
      shadow: "shadow-none",
      accent: i === 3 ? C.teal : undefined,
    });
  });
  footer(s, 7);
  s.speakerNotes.textFrame.setText("Сделать акцент: продукт не продает экран. Он производит досье решения, которое можно отдать на обсуждение, проверить и архивировать.");
}

// 8. Evidence ladder
{
  const s = addSlide();
  addTitle(s, "ДОВЕРИЕ К ДАННЫМ", "Каждое число получает уровень доказательств", "Сила продукта в том, что он не прячет слабые данные. Он показывает, чему можно верить сейчас и что нужно доказать дальше.");
  const levels = [
    ["демо", "показывает механику продукта", C.blueSoft, C.muted],
    ["приближенная оценка", "приближенный расчет, нужны реальные данные", C.yellowSoft, "#8A6200"],
    ["сверено с замерами", "сверено с измерениями", "#E9F1FF", "#315B9A"],
    ["реальные данные", "источник данных подтвержден", C.greenSoft, C.green],
  ];
  levels.forEach(([level, text, fill, color], i) => {
    const y = 330 + i * 62;
    pill(s, level, { left: 118, top: y, width: 236, height: 38 }, fill, color, color === C.muted ? C.line2 : fill);
    addText(s, text, { left: 394, top: y + 6, width: 430, height: 32 }, {
      fontSize: 20,
      color: C.ink,
    });
  });
  card(s, "Текущий честный статус", "пакет заявки: демо\nпоказатели по примеру: приближенная оценка\nгеометрия дорог: снимок открытых картографических данных", {
    left: 872,
    top: 318,
    width: 280,
    height: 218,
  }, { fill: C.white, accent: C.teal, bodySize: 16 });
  footer(s, 8);
  s.speakerNotes.textFrame.setText("Здесь превращаем слабость в дисциплину: продукт сам запрещает выдавать приближенную оценку за доказанный эффект.");
}

// 9. Status boundaries
{
  const s = addSlide();
  addTitle(s, "ЧЕСТНАЯ РАМКА", "Что есть, что проверяем, чего пока не заявляем", "Так жюри видит зрелость продукта и границы заявки.");
  const columns = [
    ["Уже есть в логике продукта", "участок дороги -> вариант изменения -> показатели -> уровень доказательств -> досье решения\nпаспорт расчета и список недостающих данных", C.tealSoft, C.teal],
    ["Проверяем в акселераторе", "какие данные нужны по нагрузке\nодин маршрут или участок в Астане\nпроверка с городским экспертом\nформат пилотной оценки", C.yellowSoft, "#8A6200"],
    ["Пока не заявляем", "официальное внедрение\nавтоматическое управление светофорами\nгарантированный эффект\nготовность к закупке сегодня", C.redSoft, C.red],
  ];
  columns.forEach(([title, body, fill, accent], i) => {
    card(s, title, body, { left: 74 + i * 378, top: 258, width: 338, height: 270 }, {
      fill,
      line: "transparent",
      accent,
      titleSize: 20,
      titleHeight: 50,
      bodyTop: 76,
      bodySize: 16,
    });
  });
  footer(s, 9);
  s.speakerNotes.textFrame.setText("Этот слайд нужен, чтобы не было ощущения, что мы пытаемся продать несуществующее внедрение. Мы показываем зрелость через честную границу.");
}

// 10. AIA fit
{
  const s = addSlide();
  addTitle(s, "ПОЧЕМУ AIA 2026", "AIA дает формат для проверки с городом", "Программа подходит проекту, потому что первый шаг — не внедрение, а проверка подхода на одном маршруте вместе с городским экспертом.");
  const cards = [
    ["Задача AIA", "цифровые решения для городской среды Астаны", C.blueSoft],
    ["Почему совпадает", "проект проверяет изменения на дороге до запуска", C.tealSoft],
    ["Что хотим проверить", "один маршрут, один эксперт, один формат досье", C.yellowSoft],
  ];
  cards.forEach(([title, body, fill], i) => {
    card(s, title, body, { left: 88 + i * 360, top: 330, width: 310, height: 176 }, {
      fill,
      line: "transparent",
      accent: i === 1 ? C.teal : i === 2 ? C.yellow : C.ink2,
      bodySize: 17,
    });
  });
  addText(s, "Источник: Astana Hub, страница Astana Innovations Accelerator 2026; доступ 15.06.2026.", {
    left: 90,
    top: 570,
    width: 850,
    height: 24,
  }, {
    fontSize: 12,
    color: C.muted,
  });
  footer(s, 10);
  s.speakerNotes.textFrame.setText("Связать pitch с AIA: это не просто интересный проект, а решение, которому акселератор может дать ровно недостающие условия проверки.");
}

// 11. Pilot plan
{
  const s = addSlide();
  addTitle(s, "ПИЛОТНЫЙ ПЛАН", "Один маршрут, 2-3 варианта изменения, одно досье решения", "Цель первого этапа — не доказать “минус пробки”, а доказать, что город получил проверяемый способ сравнивать варианты.");
  const steps = [
    ["1-2 нед.", "выбрать участок и городского эксперта"],
    ["3-4 нед.", "подключить дорожную нагрузку и базовые данные"],
    ["5-6 нед.", "проверить 2-3 варианта изменения"],
    ["7-8 нед.", "собрать досье и провести встречу проверки"],
  ];
  steps.forEach(([time, text], i) => {
    const x = 90 + i * 280;
    const y = 330;
    s.shapes.add({
      geometry: "roundRect",
      position: { left: x, top: y, width: 232, height: 162 },
      fill: i === 3 ? C.tealSoft : C.white,
      line: thinLine(i === 3 ? "#B8E5E1" : C.line),
      borderRadius: "rounded-xl",
      shadow: "shadow-sm",
    });
    addText(s, time, { left: x + 20, top: y + 22, width: 120, height: 28 }, {
      fontSize: 19,
      bold: true,
      color: i === 3 ? C.teal : C.ink,
    });
    addText(s, text, { left: x + 20, top: y + 68, width: 192, height: 68 }, {
      fontSize: 17,
      color: C.ink2,
    });
    if (i < 3) {
      s.shapes.add({
        geometry: "line",
        position: { left: x + 236, top: y + 88, width: 36, height: 0 },
        fill: "none",
        line: { style: "solid", fill: C.teal, width: 2 },
      });
    }
  });
  pill(s, "результат: решение проверить дальше / отложить / запросить данные", { left: 308, top: 548, width: 620, height: 40 }, C.yellowSoft, "#7A5600", "#F0D27E");
  footer(s, 11);
  s.speakerNotes.textFrame.setText("Пилотный план должен звучать реально: один участок, ограниченное число тестов, один официальный формат проверки результата.");
}

// 12. Value and business model
{
  const s = addSlide();
  addTitle(s, "ЦЕННОСТЬ И МОДЕЛЬ", "Меньше риск дорогого решения на слабых данных", "Almaty Mobility Lab помогает подготовить решение до пилота: быстрее, прозрачнее и с понятной ответственностью.");
  const values = [
    ["Для города", "понять, что проверить до запуска меры на улице"],
    ["Для эксперта", "видеть источники, допущения и слабые места"],
    ["Для закупки позже", "собрать след проверки и требования к данным"],
  ];
  values.forEach(([title, body], i) => {
    card(s, title, body, { left: 88, top: 314 + i * 94, width: 486, height: 72 }, {
      fill: C.white,
      titleSize: 20,
      bodyTop: 44,
      bodySize: 15,
      accent: C.teal,
    });
  });
  card(s, "Как это продается", "1. оплачиваемый пилотный пакет\n2. лицензия для управления / проектной организации\n3. поддержка, настройка данных и интеграции", {
    left: 658,
    top: 320,
    width: 440,
    height: 226,
  }, {
    fill: C.tealSoft,
    line: "#B8E5E1",
    accent: C.teal,
    bodySize: 18,
  });
  footer(s, 12);
  s.speakerNotes.textFrame.setText("Не перегружать бизнес-модель. Для акселератора достаточно показать path: пилотный пакет, затем лицензия и сопровождение.");
}

// 13. Technical appendix
{
  const s = addSlide();
  addTitle(s, "ПРИЛОЖЕНИЕ", "Что внутри системы", "Технические детали вынесены сюда, чтобы основная история оставалась понятной для жюри.");
  const tech = [
    ["Досье варианта", "структура: входные данные, результат, ограничения"],
    ["Паспорт запуска", "ID запуска, версия, seed, источник, хэши файлов"],
    ["Метки доверия", "demo / proxy / calibrated / real-data; сильный финальный статус не заявляется"],
    ["Экспорт", "PPTX/PDF/DOCX/JSON пакет для обсуждения"],
    ["API и воспроизводимость", "дорожная сеть, пакет данных, повторяемый запуск"],
    ["Готовность данных", "что подключено, чего не хватает, что запросить"],
  ];
  tech.forEach(([title, body], i) => {
    const x = 88 + (i % 3) * 360;
    const y = 330 + Math.floor(i / 3) * 126;
    card(s, title, body, { left: x, top: y, width: 310, height: 108 }, {
      fill: C.white,
      titleSize: 18,
      bodySize: 14,
      bodyTop: 48,
      accent: i < 3 ? C.teal : C.yellow,
    });
  });
  footer(s, 13);
  s.speakerNotes.textFrame.setText("Если у жюри есть технические вопросы, здесь можно показать, что внутри есть воспроизводимость, паспорт расчета и экспортируемые форматы.");
}

// 14. Ask + contacts
{
  const s = addSlide(C.dark);
  darkBand(s, "Что нужно от акселератора", "Данные, городской эксперт, один тестовый маршрут и формат проверки результата");
  const asks = [
    ["Данные", "дорожная нагрузка, скорость, светофоры, общественный транспорт"],
    ["Куратор", "городской специалист, который проверяет досье"],
    ["Маршрут", "один участок дороги или маршрут в Астане"],
    ["Проверка", "встреча проверки: что подтвердилось, что требует данных"],
  ];
  asks.forEach(([title, body], i) => {
    const x = 74 + (i % 2) * 360;
    const y = 292 + Math.floor(i / 2) * 118;
    card(s, title, body, { left: x, top: y, width: 316, height: 96 }, {
      fill: "#12314F",
      line: "#274B6A",
      shadow: "shadow-none",
      titleColor: C.white,
      bodyColor: "#B9CAD9",
      titleSize: 19,
      bodySize: 13,
      bodyTop: 46,
      accent: C.yellow,
    });
  });
  addText(s, "Kirill Vozianov", { left: 824, top: 296, width: 300, height: 34 }, {
    fontSize: 28,
    bold: true,
    color: C.white,
  });
  addText(s, "Основатель, Almaty Mobility Lab", { left: 826, top: 338, width: 320, height: 28 }, {
    fontSize: 17,
    color: "#B9CAD9",
  });
  const contacts = "vks151109@gmail.com\nTelegram: @owers3g\n+7 771 216 27 28";
  addText(s, contacts, { left: 826, top: 402, width: 340, height: 92 }, {
    fontSize: 20,
    color: C.white,
  });
  pill(s, "готов обсудить пилотный кейс", { left: 826, top: 528, width: 294, height: 38 }, C.yellow, C.dark, C.yellow);
  footer(s, 14, true);
  s.speakerNotes.textFrame.setText("Закрыть не просьбой о деньгах, а конкретным запросом к акселератору: данные, эксперт, один кейс, проверка.");
}

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(path.join(PREVIEW_DIR, `${stem}.png`), png);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(LAYOUT_DIR, `${stem}.layout.json`), await layout.text());
}

const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
await writeBlob(path.join(PREVIEW_DIR, "deck-montage.webp"), montage);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(FINAL_PPTX);
await pptx.save(DOWNLOADS_COPY);

await fs.writeFile(path.join(QA_DIR, "visual-qa.txt"), `Initial QA checklist

- Final PPTX exported with 14 slides.
- Previews rendered to ${PREVIEW_DIR}.
- Montage rendered to ${path.join(PREVIEW_DIR, "deck-montage.webp")}.
- Main slides avoid raw application screenshots and use schematic road/dossier visuals.
- Main slides use simple Russian terms: участок дороги, маршрут, вариант изменения, дорожная ситуация, показатели, досье решения.
- Forbidden claims avoided: official deployment, automatic signal control, guaranteed impact, ready procurement status.

Pending: external visual inspection and final PPTX package/text check.
`);

console.log(JSON.stringify({
  finalPptx: FINAL_PPTX,
  downloadsCopy: DOWNLOADS_COPY,
  workspace: WORKSPACE,
  preview: path.join(PREVIEW_DIR, "deck-montage.webp"),
  slides: presentation.slides.items.length,
}, null, 2));
