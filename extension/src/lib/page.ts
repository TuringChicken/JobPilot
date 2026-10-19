import type { PageContent } from "./types";

// A selection shorter than this is probably accidental; use the whole page instead.
export const MIN_SELECTION_CHARS = 200;

/**
 * Runs inside the job page (serialized by chrome.scripting), so it must be self-contained.
 * Only reads visible text; nothing on the page is modified.
 */
export function readPage(minSelection: number): PageContent {
  const selection = window.getSelection()?.toString().trim() ?? "";
  const fromSelection = selection.length >= minSelection;
  return {
    url: location.href,
    title: document.title,
    text: fromSelection ? selection : (document.body?.innerText ?? ""),
    fromSelection,
  };
}

export class PageAccessError extends Error {
  constructor(readonly reason: "noTab" | "noAccess") {
    super(reason);
  }
}

/** Reads the active tab. Needs activeTab (toolbar click) or a host permission for the site. */
export async function readActiveTab(): Promise<PageContent> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id === undefined) throw new PageAccessError("noTab");
  try {
    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readPage,
      args: [MIN_SELECTION_CHARS],
    });
    return result.result as PageContent;
  } catch {
    throw new PageAccessError("noAccess");
  }
}

/** Lets the panel read any page without a toolbar click first; still only read on "Analyze". */
export function requestAllSitesAccess(): Promise<boolean> {
  return chrome.permissions.request({ origins: ["http://*/*", "https://*/*"] });
}
