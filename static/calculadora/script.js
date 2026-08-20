"use strict";

const CONFIG = Object.freeze({
  prices: {
    colete: { cpf: 45000, pj: 30000, parceria: 25000, alianca: 20000 },
    hacker: { normal: 95000, alianca: 80000 },
    circuito: { normal: 57000, alianca: 38000 }
  },
  resources: {
    colete: { placas: 1, lonas: 2 },
    hacker: { celular: 1, fios: 8, tubos: 8, fitas: 8, porcas: 8, parafusos: 8 },
    circuito: { aluminio: 5, cobre: 5, plastico: 10, chapa: 1 },
    placa: { cobre: 40, aluminio: 40, plastico: 60, vidro: 60, borracha: 65, base: 1, chapas: 2, dinheiroSujo: 500 }
  }
});

const DEFAULT_STATE = Object.freeze({
  quantities: { colete: 0, hacker: 0, circuito: 0, placa: 0 },
  types: { colete: "cpf", hacker: "normal", circuito: "normal" },
  additions: { colete: 0, hacker: 0, circuito: 0 }
});

const STORAGE_KEY = "irons-calculator-v2";
let state = structuredCloneSafe(DEFAULT_STATE);
let toastTimer;

const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2
});

const byId = (id) => document.getElementById(id);

function structuredCloneSafe(value) {
  return typeof structuredClone === "function"
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));
}

function money(value) {
  return currency.format(Number.isFinite(value) ? value : 0);
}

function sanitizeQuantity(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (_) {
    // A calculadora continua funcionando mesmo se o armazenamento estiver bloqueado.
  }
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!saved || typeof saved !== "object") return;

    for (const key of Object.keys(state.quantities)) {
      state.quantities[key] = sanitizeQuantity(saved.quantities?.[key]);
    }

    for (const key of Object.keys(state.types)) {
      const candidate = saved.types?.[key];
      if (candidate && CONFIG.prices[key]?.[candidate]) state.types[key] = candidate;
    }

    for (const key of Object.keys(state.additions)) {
      const candidate = Number(saved.additions?.[key]);
      if ([0, 15, 20, 30].includes(candidate)) state.additions[key] = candidate;
    }
  } catch (_) {
    // Ignora dados antigos/corrompidos.
  }
}

function setText(id, value) {
  const element = byId(id);
  if (element) element.textContent = value;
}

function unitPrice(product) {
  const base = CONFIG.prices[product][state.types[product]];
  return base * (1 + state.additions[product] / 100);
}

function calculate() {
  const q = state.quantities;
  const coleteUnit = unitPrice("colete");
  const hackerUnit = unitPrice("hacker");
  const circuitoUnit = unitPrice("circuito");

  const totalColete = q.colete * coleteUnit;
  const totalHacker = q.hacker * hackerUnit;
  const totalCircuito = q.circuito * circuitoUnit;
  const totalPlacas = q.placa + q.colete;
  const totalGeral = totalColete + totalHacker + totalCircuito;

  setText("totalColete", money(totalColete));
  setText("totalHacker", money(totalHacker));
  setText("totalCircuito", money(totalCircuito));
  setText("totalGeral", money(totalGeral));
  setText("precoHacker", money(hackerUnit));
  setText("precoCircuito", money(circuitoUnit));

  setText("coletePlacas", q.colete * CONFIG.resources.colete.placas);
  setText("coleteLonas", q.colete * CONFIG.resources.colete.lonas);

  for (const [resource, amount] of Object.entries(CONFIG.resources.hacker)) {
    const id = `hacker${resource.charAt(0).toUpperCase()}${resource.slice(1)}`;
    setText(id, q.hacker * amount);
  }

  setText("circuitoAluminio", q.circuito * CONFIG.resources.circuito.aluminio);
  setText("circuitoCobre", q.circuito * CONFIG.resources.circuito.cobre);
  setText("circuitoPlastico", q.circuito * CONFIG.resources.circuito.plastico);
  setText("circuitoChapa", q.circuito * CONFIG.resources.circuito.chapa);

  setText("placaCobre", totalPlacas * CONFIG.resources.placa.cobre);
  setText("placaAluminio", totalPlacas * CONFIG.resources.placa.aluminio);
  setText("placaPlastico", totalPlacas * CONFIG.resources.placa.plastico);
  setText("placaVidro", totalPlacas * CONFIG.resources.placa.vidro);
  setText("placaBorracha", totalPlacas * CONFIG.resources.placa.borracha);
  setText("placaBase", totalPlacas * CONFIG.resources.placa.base);
  setText("placaChapas", totalPlacas * CONFIG.resources.placa.chapas);
  setText("placaSujo", money(totalPlacas * CONFIG.resources.placa.dinheiroSujo));

  saveState();
  return { totalColete, totalHacker, totalCircuito, totalGeral, totalPlacas };
}

function syncUiFromState() {
  const inputMap = {
    colete: "qtdColete",
    hacker: "qtdHacker",
    circuito: "qtdCircuito",
    placa: "qtdPlaca"
  };

  for (const [product, id] of Object.entries(inputMap)) {
    byId(id).value = state.quantities[product];
  }

  const typeGroups = {
    colete: "tiposColete",
    hacker: "tiposHacker",
    circuito: "tiposCircuito"
  };

  for (const [product, groupId] of Object.entries(typeGroups)) {
    byId(groupId).querySelectorAll("button").forEach((button) => {
      button.classList.toggle("ativo", button.dataset.value === state.types[product]);
      button.setAttribute("aria-pressed", String(button.dataset.value === state.types[product]));
    });
  }

  const additionGroups = {
    colete: "acrescimoColete",
    hacker: "acrescimoHacker",
    circuito: "acrescimoCircuito"
  };

  for (const [product, groupId] of Object.entries(additionGroups)) {
    byId(groupId).querySelectorAll("button").forEach((button) => {
      const active = Number(button.dataset.value) === state.additions[product];
      button.classList.toggle("ativo", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }
}

function productFromInputId(id) {
  return ({ qtdColete: "colete", qtdHacker: "hacker", qtdCircuito: "circuito", qtdPlaca: "placa" })[id];
}

function setupInputs() {
  document.querySelectorAll(".quantidade").forEach((input) => {
    input.addEventListener("input", () => {
      const product = productFromInputId(input.id);
      state.quantities[product] = sanitizeQuantity(input.value);
      if (input.value === "" || Number(input.value) < 0) input.value = state.quantities[product];
      calculate();
    });

    input.addEventListener("blur", () => {
      const product = productFromInputId(input.id);
      input.value = state.quantities[product];
    });
  });

  document.querySelectorAll(".stepper-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const input = byId(button.dataset.target);
      const product = productFromInputId(input.id);
      const step = Number(button.dataset.step) || 0;
      state.quantities[product] = Math.max(0, state.quantities[product] + step);
      input.value = state.quantities[product];
      calculate();
    });
  });
}

function setupOptionGroups() {
  const groups = [
    ["tiposColete", "colete", "types"],
    ["tiposHacker", "hacker", "types"],
    ["tiposCircuito", "circuito", "types"],
    ["acrescimoColete", "colete", "additions"],
    ["acrescimoHacker", "hacker", "additions"],
    ["acrescimoCircuito", "circuito", "additions"]
  ];

  for (const [groupId, product, stateKey] of groups) {
    const group = byId(groupId);
    group.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-value]");
      if (!button) return;
      const value = stateKey === "additions" ? Number(button.dataset.value) : button.dataset.value;
      state[stateKey][product] = value;
      syncUiFromState();
      calculate();
    });
  }
}

function resetCalculator() {
  state = structuredCloneSafe(DEFAULT_STATE);
  syncUiFromState();
  calculate();
  showToast("Calculadora limpa");
}

function typeLabel(value) {
  return ({ cpf: "CPF", pj: "PJ", parceria: "Parceria", alianca: "Aliança", normal: "Normal" })[value] || value;
}

function buildSummary() {
  const totals = calculate();
  return [
    "CALCULADORA IRONS",
    "",
    `Colete: ${state.quantities.colete} un. • ${typeLabel(state.types.colete)} • +${state.additions.colete}% • ${money(totals.totalColete)}`,
    `Celular Hacker: ${state.quantities.hacker} un. • ${typeLabel(state.types.hacker)} • +${state.additions.hacker}% • ${money(totals.totalHacker)}`,
    `Circuito Eletrônico: ${state.quantities.circuito} un. • ${typeLabel(state.types.circuito)} • +${state.additions.circuito}% • ${money(totals.totalCircuito)}`,
    `Placas extras: ${state.quantities.placa} un.`,
    `Placas totais para materiais: ${totals.totalPlacas} un.`,
    "",
    `TOTAL GERAL: ${money(totals.totalGeral)}`
  ].join("\n");
}

async function copySummary() {
  const summary = buildSummary();
  try {
    await navigator.clipboard.writeText(summary);
    showToast("Resumo copiado");
  } catch (_) {
    const textarea = document.createElement("textarea");
    textarea.value = summary;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
    showToast("Resumo copiado");
  }
}

function showToast(message) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 1800);
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    });
  }
}

function init() {
  loadState();
  syncUiFromState();
  setupInputs();
  setupOptionGroups();
  byId("resetButton").addEventListener("click", resetCalculator);
  byId("copyButton").addEventListener("click", copySummary);
  calculate();
  registerServiceWorker();
}

document.addEventListener("DOMContentLoaded", init);
