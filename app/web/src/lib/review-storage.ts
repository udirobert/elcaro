"use client";

import type { ParsedReviewPacket, ReviewRow } from "./review-csv";

const DB_NAME = "elcaro-review-workbench";
const DB_VERSION = 1;
const STORE = "packets";

export interface StoredPacket {
  fileName: string;
  updatedAt: string;
  checksum: string;
  rows: ReviewRow[];
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE, { keyPath: "checksum" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Unable to open private review store"));
  });
}

export async function savePacket(fileName: string, packet: ParsedReviewPacket): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put({
        checksum: packet.checksum,
        fileName,
        updatedAt: new Date().toISOString(),
        rows: packet.rows,
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error ?? new Error("Unable to save private review state"));
    });
  } finally {
    db.close();
  }
}

export async function listPackets(): Promise<StoredPacket[]> {
  const db = await openDb();
  try {
    const packets = await new Promise<StoredPacket[]>((resolve, reject) => {
      const request = db.transaction(STORE, "readonly").objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result as StoredPacket[]);
      request.onerror = () => reject(request.error ?? new Error("Unable to read private review state"));
    });
    return packets.sort((a, b) => a.fileName.localeCompare(b.fileName));
  } finally {
    db.close();
  }
}

export async function clearPackets(): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error ?? new Error("Unable to clear private review state"));
    });
  } finally {
    db.close();
  }
}
