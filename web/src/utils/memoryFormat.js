export function formatGB(bytes, digits = 1) {
  if (!bytes || bytes <= 0) return '0 GB';
  return `${(bytes / 1e9).toFixed(digits)} GB`;
}

export function meterColor(pct) {
  if (pct >= 75) return '#f85149';
  if (pct >= 50) return '#d29922';
  return '#3fb950';
}

const DEFAULT_PER_TICKET = 16e9;
const CONTEXT_OVERHEAD = 2e9;

const MODEL_RAM_GB = {
  codestral: 16,
  devstral: 16,
  'llama3.3': 40,
  codellama: 10,
  mixtral: 26,
  starcoder2: 6,
  'granite-code': 6,
  'llama3.2': 3,
};

export function estimatePerTicketBytes(modelName) {
  if (!modelName) return DEFAULT_PER_TICKET;
  const base = modelName.split(':')[0].toLowerCase();
  for (const [key, gb] of Object.entries(MODEL_RAM_GB)) {
    if (base === key || base.startsWith(key)) return gb * 1e9;
  }
  return DEFAULT_PER_TICKET;
}

export function estimateBudgetBytes(loadedBytes, inProgress, perTicketBytes) {
  const perTicket = perTicketBytes || DEFAULT_PER_TICKET;
  if (inProgress <= 0) {
    return { budgetedBytes: loadedBytes, reserveBytes: 0, perTicketBytes: perTicket };
  }
  let budgetedBytes = loadedBytes;
  if (inProgress === 1) {
    budgetedBytes = Math.max(loadedBytes, perTicket);
  } else {
    budgetedBytes = Math.max(loadedBytes, perTicket + (inProgress - 1) * CONTEXT_OVERHEAD);
  }
  return {
    budgetedBytes,
    reserveBytes: Math.max(0, budgetedBytes - loadedBytes),
    perTicketBytes: perTicket,
  };
}
