// Clicking the toolbar icon opens the side panel (and grants activeTab for that tab).
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(console.error);
