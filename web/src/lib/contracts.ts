export type User = {
  id: string;
  name: string;
  email: string | null;
  is_demo: boolean;
  workspace_name: string;
  csrf_token: string;
};
export type Config = {
  ai_available: boolean;
  model: string;
  registration: boolean;
  demo: boolean;
  max_upload_mb: number;
  max_rows: number;
};
export type Period = {
  period: string;
  orders: number;
  lines: number;
  units: number;
  gross: number;
  discount: number;
  refunds: number;
  product_cost: number;
  shipping: number;
  revenue: number;
  margin: number;
  margin_pct: number;
  refund_rate: number;
};
export type Finding = {
  id: string;
  key: string;
  title: string;
  amount: number;
  count?: number;
  severity: string;
  status: string;
  per_order_change?: number;
  explanation: string;
  hypothesis?: string;
  evidence: {
    query: string;
    formula: string;
    before?: number;
    after?: number;
    delta?: number;
    params: string[];
  } | null;
};
export type Summary = {
  current: Period;
  previous: Period | null;
  daily: { date: string; revenue: number; margin: number; orders: number }[];
  products: {
    sku: string;
    name: string;
    revenue: number;
    margin: number;
    margin_pct: number;
    orders: number;
  }[];
  bridge: { key: string; value: number }[];
  findings: Finding[];
  negative_lines: number;
  reconciliation_residual: number;
};
export type Dataset = {
  id: string;
  name: string;
  version: number;
  content_hash: string;
  status: string;
  synthetic: boolean;
  created_at: string;
  summary: Summary;
  files: { kind: string; rows: number; hash: string }[];
  issues: {
    code: string;
    severity: string;
    file: string;
    row: number;
    record_id: string;
    message: string;
    resolution: string;
  }[];
};
export type Params = {
  discount_reduction: number;
  demand_drop: number;
  max_demand_drop: number;
  shipping_saving: number;
  extra_return_cost: number;
  implementation_cost: number;
};
export type Workspace = {
  id: string;
  name: string;
  dataset: Dataset | null;
  versions: Pick<Dataset, 'id' | 'version' | 'name' | 'status' | 'created_at' | 'content_hash'>[];
  scenario: Partial<Params>;
  scenario_hash: string;
};
export type Simulation = {
  baseline: number;
  orders: number;
  unit_margin: number;
  break_even_pct: number | null;
  recommended: string;
  params: Params;
  scenario_hash: string;
  data_hash: string;
  dataset_id: string;
  assumptions: string[];
  alternatives: {
    id: string;
    label: string;
    best: number;
    worst: number;
    selected: number;
    delta: number;
    orders: number;
  }[];
  curve: { demand_drop: number; discount: number; shipping: number; baseline: number }[];
};
export type Run = {
  id: string;
  question: string;
  dataset_id: string;
  status: string;
  stage: string;
  mode: string;
  created_at: string;
  events: { stage: string; message: string; at: string }[];
  result: null | {
    question: string;
    answer: string;
    findings: Finding[];
    unresolved: boolean;
    warning: string | null;
    scope_note: string;
    mode: string;
    model_tokens: number;
    elapsed_ms: number;
  };
};
export type Memo = {
  id: string;
  dataset_id: string;
  scenario_hash: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  content: {
    scenario: Simulation;
    data_hash: string;
    version: number;
    synthetic: boolean;
    findings: Finding[];
  };
};
export type LedgerRow = {
  line_id: string;
  order_id: string;
  sku: string;
  product_name: string;
  date: string;
  gross: number;
  discount: number;
  refunds: number;
  product_cost: number;
  shipping: number;
  revenue: number;
  margin: number;
  order_source_row: number;
  cost_source_row: number;
};
export type Evidence = {
  finding: Finding;
  rows: LedgerRow[];
  total: number;
  offset: number;
  limit: number;
  ledger_query: string;
  content_hash: string;
  version: number;
  dataset_id: string;
  source_hashes: Record<string, string>;
};
export type AuditEvent = {
  id: number;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};
