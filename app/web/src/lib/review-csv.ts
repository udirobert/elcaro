export type ReviewLabel = "steering" | "non_steering" | "uncertain" | "";

export interface ReviewRow {
  sample_id: string;
  source: string;
  channel: string;
  actor: string;
  time: string;
  text: string;
  label: ReviewLabel;
  notes: string;
}

export interface ParsedReviewPacket {
  rows: ReviewRow[];
  originalCsv: string;
  checksum: string;
}

const REQUIRED_COLUMNS = [
  "sample_id",
  "source",
  "channel",
  "actor",
  "time",
  "text",
  "label",
  "notes",
] as const;

type RequiredColumn = (typeof REQUIRED_COLUMNS)[number];

export function parseCsvRows(input: string): string[][] {
  const csv = input.replace(/^\uFEFF/, "");
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  let rowHasContent = false;
  const endField = () => {
    row.push(field);
    field = "";
  };
  const endRow = () => {
    endField();
    rows.push(row);
    row = [];
    rowHasContent = false;
  };
  for (let i = 0; i < csv.length; i += 1) {
    const ch = csv[i];
    if (quoted) {
      if (ch === '"') {
        if (csv[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        field += ch;
      }
      rowHasContent = true;
      continue;
    }
    if (ch === '"') {
      quoted = true;
      rowHasContent = true;
    } else if (ch === ",") {
      endField();
      rowHasContent = true;
    } else if (ch === "\n") {
      if (field !== "" || row.length > 0 || rowHasContent) endRow();
    } else if (ch !== "\r") {
      field += ch;
      rowHasContent = true;
    }
  }
  if (quoted) throw new Error("CSV has an unterminated quoted field");
  if (field !== "" || row.length > 0 || rowHasContent) endRow();
  return rows;
}

export function serializeCsvRows(rows: string[][]): string {
  return `${rows
    .map((row) =>
      row
        .map((cell) => {
          const needsQuotes = /[",\r\n]/.test(cell);
          const escaped = cell.replace(/"/g, '""');
          return needsQuotes ? `"${escaped}"` : escaped;
        })
        .join(","),
    )
    .join("\r\n")}\r\n`;
}

export function parseReviewCsv(csv: string): ParsedReviewPacket {
  const grid = parseCsvRows(csv);
  if (grid.length < 2) throw new Error("Review CSV must contain a header and at least one record");
  const header = grid[0];
  if (
    header.length !== REQUIRED_COLUMNS.length ||
    !REQUIRED_COLUMNS.every((name, i) => header[i] === name)
  ) {
    throw new Error("Unexpected review columns. Use the CSV supplied by Elcaro.");
  }
  const seen = new Set<string>();
  const rows = grid.slice(1).map((cells, index) => {
    if (cells.length !== REQUIRED_COLUMNS.length) {
      throw new Error(`Row ${index + 2} does not match the review schema`);
    }
    const entry = Object.fromEntries(
      cells.map((value, i) => [header[i], value]),
    ) as Record<RequiredColumn, string>;
    if (!entry.sample_id || seen.has(entry.sample_id)) {
      throw new Error(`Duplicate or missing sample id on row ${index + 2}`);
    }
    seen.add(entry.sample_id);
    return { ...entry, label: entry.label as ReviewLabel };
  });
  return { rows, originalCsv: csv, checksum: hashFNV(csv) };
}

export function serializeReviewCsv(rows: ReviewRow[]): string {
  return serializeCsvRows([
    [...REQUIRED_COLUMNS],
    ...rows.map((row) => REQUIRED_COLUMNS.map((column) => row[column])),
  ]);
}

export function labelsAreComplete(rows: ReviewRow[]): boolean {
  return rows.every((row) => row.label !== "");
}

export function hashFNV(value: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}
