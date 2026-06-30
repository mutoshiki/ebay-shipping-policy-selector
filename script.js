"use strict";

const POLICY_TIERS = [
  { maxWeight: 300, weightCode: "300G", weightLabel: "300g以下" },
  { maxWeight: 500, weightCode: "500G", weightLabel: "301〜500g" },
  { maxWeight: 800, weightCode: "800G", weightLabel: "501〜800g" },
  { maxWeight: 1000, weightCode: "1000G", weightLabel: "801〜1000g" },
  { maxWeight: 1500, weightCode: "1500G", weightLabel: "1001〜1500g" },
  { maxWeight: 2000, weightCode: "2000G", weightLabel: "1501〜2000g" }
];

const PRICE_TIERS = {
  low: {
    maxPrice: 100,
    code: "100USD",
    label: "100USD以下"
  },
  high: {
    maxPrice: 250,
    code: "101250USD",
    label: "101〜250USD"
  }
};

const form = document.querySelector("#policyForm");
const priceInput = document.querySelector("#price");
const weightInput = document.querySelector("#weight");
const itemNameInput = document.querySelector("#itemName");
const packedCheck = document.querySelector("#packedCheck");
const resultEmpty = document.querySelector("#resultEmpty");
const resultContent = document.querySelector("#resultContent");
const manualResult = document.querySelector("#manualResult");
const resultStatus = document.querySelector("#resultStatus");
const policyName = document.querySelector("#policyName");
const weightTier = document.querySelector("#weightTier");
const priceTier = document.querySelector("#priceTier");
const resultItem = document.querySelector("#resultItem");
const resultValues = document.querySelector("#resultValues");
const resultNotice = document.querySelector("#resultNotice");
const manualMessage = document.querySelector("#manualMessage");
const copyButton = document.querySelector("#copyButton");
const toast = document.querySelector("#toast");
const themeButton = document.querySelector("#themeButton");
const themeIcon = document.querySelector("#themeIcon");
const toggleTableButton = document.querySelector("#toggleTable");
const policyTableWrap = document.querySelector("#policyTableWrap");
const policyTableBody = document.querySelector("#policyTableBody");

let toastTimer;

function parsePositiveNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function formatUsd(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

function formatGrams(value) {
  return `${new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 }).format(value)}g`;
}

function setFieldError(input, message) {
  const field = input.closest(".field");
  const error = document.querySelector(`#${input.id}Error`);
  field.classList.toggle("has-error", Boolean(message));
  input.setAttribute("aria-invalid", message ? "true" : "false");
  error.textContent = message;
}

function validateInputs() {
  const price = parsePositiveNumber(priceInput.value);
  const weight = parsePositiveNumber(weightInput.value);

  setFieldError(priceInput, price === null ? "0より大きい商品価格を入力してください。" : "");
  setFieldError(weightInput, weight === null ? "0より大きい梱包後重量を入力してください。" : "");

  return price !== null && weight !== null ? { price, weight } : null;
}

function chooseWeightTier(weight) {
  return POLICY_TIERS.find((tier) => weight <= tier.maxWeight) ?? null;
}

function choosePriceTier(price) {
  if (price <= PRICE_TIERS.low.maxPrice) return PRICE_TIERS.low;
  if (price <= PRICE_TIERS.high.maxPrice) return PRICE_TIERS.high;
  return null;
}

function buildPolicyName(weightCode, priceCode) {
  return `CAM${weightCode}${priceCode}`;
}

function getBoundaryNotice(weight, tier) {
  const remaining = tier.maxWeight - weight;
  if (remaining < 0 || remaining > 10) return "";

  const currentIndex = POLICY_TIERS.findIndex((item) => item.maxWeight === tier.maxWeight);
  const nextTier = POLICY_TIERS[currentIndex + 1];
  if (!nextTier) return "";

  return `上限まで残り${formatGrams(remaining)}です。はかりの誤差や追加梱包がある場合は、${nextTier.weightCode}区分を選ぶと安全です。`;
}

function showManualResult(price, weight) {
  resultEmpty.hidden = true;
  resultContent.hidden = true;
  manualResult.hidden = false;
  resultStatus.textContent = "要確認";
  resultStatus.className = "status-badge is-manual";

  const reasons = [];
  if (weight > 2000) reasons.push(`梱包後重量が${formatGrams(weight)}で2000gを超えています`);
  if (price > 250) reasons.push(`商品価格が${formatUsd(price)}で250USDを超えています`);

  manualMessage.textContent = `${reasons.join("。また、")}。既存の12ポリシーは使用せず、実送料・補償・署名条件を個別に確認してください。`;
}

function showPolicyResult(price, weight) {
  const selectedWeightTier = chooseWeightTier(weight);
  const selectedPriceTier = choosePriceTier(price);

  if (!selectedWeightTier || !selectedPriceTier) {
    showManualResult(price, weight);
    return;
  }

  const selectedPolicy = buildPolicyName(selectedWeightTier.weightCode, selectedPriceTier.code);
  const itemName = itemNameInput.value.trim() || "名称未入力";
  const notice = getBoundaryNotice(weight, selectedWeightTier);

  resultEmpty.hidden = true;
  manualResult.hidden = true;
  resultContent.hidden = false;
  resultStatus.textContent = "判定完了";
  resultStatus.className = "status-badge is-ready";

  policyName.value = selectedPolicy;
  policyName.textContent = selectedPolicy;
  weightTier.textContent = selectedWeightTier.weightLabel;
  priceTier.textContent = selectedPriceTier.label;
  resultItem.textContent = itemName;
  resultValues.textContent = `${formatGrams(weight)} ／ ${formatUsd(price)}`;

  const notices = [];
  if (!packedCheck.checked) {
    notices.push("未梱包の重量で判定しています。発送状態まで梱包して再計量してください。");
  }
  if (notice) notices.push(notice);

  resultNotice.hidden = notices.length === 0;
  resultNotice.textContent = notices.join(" ");
}

function handleSubmit(event) {
  event.preventDefault();
  const values = validateInputs();
  if (!values) return;

  showPolicyResult(values.price, values.weight);
  document.querySelector("#resultTitle").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function copyPolicyName() {
  const text = policyName.textContent.trim();
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const temporaryInput = document.createElement("textarea");
    temporaryInput.value = text;
    temporaryInput.setAttribute("readonly", "");
    temporaryInput.style.position = "fixed";
    temporaryInput.style.opacity = "0";
    document.body.appendChild(temporaryInput);
    temporaryInput.select();
    document.execCommand("copy");
    temporaryInput.remove();
  }

  showToast("ポリシー名をコピーしました");
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 1800);
}

function renderPolicyTable() {
  policyTableBody.innerHTML = POLICY_TIERS.map((tier, index) => {
    const minimum = index === 0 ? 0 : POLICY_TIERS[index - 1].maxWeight;
    const rangeLabel = index === 0
      ? `${tier.maxWeight}g以下`
      : `${minimum + 1}〜${tier.maxWeight}g`;

    return `
      <tr>
        <td>${rangeLabel}</td>
        <td><code>${buildPolicyName(tier.weightCode, PRICE_TIERS.low.code)}</code></td>
        <td><code>${buildPolicyName(tier.weightCode, PRICE_TIERS.high.code)}</code></td>
      </tr>
    `;
  }).join("");
}

function togglePolicyTable() {
  const isOpen = toggleTableButton.getAttribute("aria-expanded") === "true";
  toggleTableButton.setAttribute("aria-expanded", String(!isOpen));
  toggleTableButton.textContent = isOpen ? "一覧を表示" : "一覧を閉じる";
  policyTableWrap.hidden = isOpen;
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeIcon.textContent = theme === "dark" ? "☀" : "◐";
  try {
    localStorage.setItem("ebay-policy-theme", theme);
  } catch {
    // ファイルを直接開いた環境など、保存できない場合も表示切替は継続する。
  }
}

function toggleTheme() {
  const current = document.documentElement.dataset.theme || "light";
  applyTheme(current === "dark" ? "light" : "dark");
}

function initTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem("ebay-policy-theme");
  } catch {
    stored = null;
  }

  if (stored === "light" || stored === "dark") {
    applyTheme(stored);
    return;
  }

  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark ? "dark" : "light");
}

function clearErrorOnInput(event) {
  const input = event.target;
  if (input === priceInput || input === weightInput) {
    setFieldError(input, "");
  }
}

form.addEventListener("submit", handleSubmit);
form.addEventListener("input", clearErrorOnInput);
copyButton.addEventListener("click", copyPolicyName);
toggleTableButton.addEventListener("click", togglePolicyTable);
themeButton.addEventListener("click", toggleTheme);

renderPolicyTable();
initTheme();
