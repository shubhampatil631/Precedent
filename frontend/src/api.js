/**
 * API client wrapper for Hiver Support Agent backend.
 */

const API_BASE_URL = "http://localhost:8000";

export async function handleMessage(customerText, system = "full") {
  const response = await fetch(`${API_BASE_URL}/handle-message?system=${encodeURIComponent(system)}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ customer_text: customerText }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return await response.json();
}

export async function getEvalResults() {
  const response = await fetch(`${API_BASE_URL}/eval-results`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch eval results (${response.status})`);
  }
  return await response.json();
}

export async function getTaxonomy() {
  const response = await fetch(`${API_BASE_URL}/taxonomy`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch taxonomy (${response.status})`);
  }
  return await response.json();
}
