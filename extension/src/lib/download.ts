// Minimal typing for the File System Access API (not yet in TypeScript's DOM lib).
interface SaveFilePicker {
  showSaveFilePicker?: (options: {
    suggestedName: string;
    types: { description: string; accept: Record<string, string[]> }[];
  }) => Promise<{
    name: string;
    createWritable: () => Promise<{ write: (data: Blob) => Promise<void>; close: () => Promise<void> }>;
  }>;
}

/**
 * Saves text through the system "Save as" dialog so the user picks the folder.
 * Returns the chosen file name, or null if the user cancelled.
 * Falls back to a normal browser download where the picker isn't available.
 */
export async function saveTextFile(name: string, text: string, mime = "text/markdown"): Promise<string | null> {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const picker = (window as unknown as SaveFilePicker).showSaveFilePicker;
  if (picker) {
    try {
      const handle = await picker({
        suggestedName: name,
        types: [{ description: "Markdown", accept: { [mime]: [".md"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return handle.name;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return null;
      // Any other failure (e.g. picker blocked in this context): use a plain download.
    }
  }
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return name;
}
