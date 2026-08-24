export interface LeagueSettingsConfig {
  participants: number;
  starting_budget: number;
  roster_size: number;
  roster_slots: Record<string, number>;
  base_price: number;
  allowed_modules: string[];
  [key: string]: unknown;
}

export interface LeagueSettings {
  id: number;
  name: string;
  config: LeagueSettingsConfig;
  is_active: boolean;
}

export interface LeagueMember {
  id: number;
  name: string;
  is_admin: boolean;
}

export interface RosterPlayer {
  player_id: number;
  name: string;
  role: string;
  price: number;
}

export interface MemberRoster {
  member_id: number;
  name: string;
  budget_remaining: number;
  slots_remaining: Record<string, number>;
  players: RosterPlayer[];
}

export interface Player {
  id: number;
  name: string;
  role: string;
  team_name: string | null;
  status: string;
}

export interface PlayerScore {
  player_id: number;
  fanta_score: number | null;
  tier_label: string | null;
  components: Record<string, unknown>;
  model_version: string | null;
  computed_at: string | null;
}

export interface PlayerValue {
  player_id: number;
  model_value: number | null;
  market_average: number | null;
  components: Record<string, unknown>;
}

export interface AuctionSession {
  id: number;
  name: string;
  status: string;
}

export interface BudgetConstraint {
  minimum_completion_budget: number;
  safe_spendable_budget: number;
  hard_max_bid: number | null;
}

export interface Scarcity {
  level: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
  players_remaining_in_tier: number;
  slots_still_needed_league_wide: number;
  ratio: number;
}

export interface RecommendedPrice {
  bargain_max: number;
  fair_max: number;
  aggressive_max: number;
  maximum: number;
  hard_capped: boolean;
}

export interface Recommendation {
  player_id: number;
  role: string;
  fanta_score: number | null;
  tier_label: string | null;
  model_value: number | null;
  market_average: number | null;
  recommended_price: RecommendedPrice | null;
  budget_constraint: BudgetConstraint;
  scarcity: Scarcity;
  warnings: string[];
}

export interface MemberState {
  member_id: number;
  name: string;
  is_admin: boolean;
  budget_remaining: number;
  slots_remaining: Record<string, number>;
}

export interface SessionState {
  session_id: number;
  status: string;
  members: MemberState[];
}

export interface Transaction {
  id: number;
  player_id: number;
  player_name: string;
  role: string;
  buyer_member_id: number;
  buyer_name: string;
  price: number;
  budget_before: number;
  budget_after: number;
  remaining_slots: Record<string, number>;
}

export interface DataSourceStatus {
  key: string;
  display_name: string;
  is_enabled: boolean;
  last_successful_sync: string | null;
  last_failed_sync: string | null;
  last_error: string | null;
}

export interface ImportResult {
  source: string;
  records_imported: number;
  players_created: number;
  players_matched: number;
  warnings: string[];
}

export interface SimulationResult {
  iterations: number;
  completion_probability: number;
  total_cost_p10: number;
  total_cost_p50: number;
  total_cost_p90: number;
  remaining_budget_p50: number;
}
