import { z } from "zod";
import {
  categoryRarityOptions,
  objectiveOptions,
  orbRarityOptions,
  type OptimizeRequest,
  type OptimizeResponse,
} from "@/lib/types";

const orbRaritySchema = z.enum(orbRarityOptions);
const categoryRaritySchema = z.enum(categoryRarityOptions);
const objectiveSchema = z.enum(objectiveOptions);

const numberOrZero = z.coerce.number().catch(0);
const integerOrZero = z.coerce.number().int().catch(0);

export const orbInSchema = z
  .object({
    type: z.string().trim().min(1),
    set: z.string().trim().min(1),
    rarity: orbRaritySchema.catch("Rare"),
    value: numberOrZero,
    level: integerOrZero,
    awakened: integerOrZero.default(0),
    slot_index: integerOrZero.optional(),
  })
  .transform((orb) => ({
    ...orb,
    value: Number.isFinite(orb.value) ? Math.max(0, orb.value) : 0,
    level: Math.max(0, orb.level),
    awakened: Math.max(0, orb.awakened),
  }));

export const optimizeProfileInSchema = z.object({
  name: z.string().trim().min(1),
  weight: z.coerce.number(),
  objective: objectiveSchema,
  power: z.coerce.number(),
  epsilon: z.coerce.number(),
  set_priority: z.record(z.string(), z.coerce.number()).default({}),
  orb_weights: z.record(z.string(), z.coerce.number()).default({}),
  orb_level_weights: z.record(z.string(), z.coerce.number()).default({}),
  categories: z.record(z.string(), categoryRaritySchema).optional(),
  slots: z.record(z.string(), z.coerce.number().int()).optional(),
});

export const optimizeRequestSchema = z.object({
  orbs: z.array(orbInSchema),
  profiles: z.array(optimizeProfileInSchema),
  shareable_categories: z.array(z.string()).optional(),
  algorithm: z.literal("greedy"),
});

const sharedSlotProfileImpactSchema = z
  .object({
    profile: z.string(),
    selected_score: z.coerce.number().optional(),
    solo_best_score: z.coerce.number().optional(),
    compromise_loss: z.coerce.number().optional(),
    selected_d_set: z.coerce.number().optional(),
    selected_d_orb: z.coerce.number().optional(),
    solo_best_d_set: z.coerce.number().optional(),
    solo_best_d_orb: z.coerce.number().optional(),
    cap_limited: z.boolean().optional(),
  })
  .transform((impact) => ({
    profile: impact.profile,
    selected_score: impact.selected_score ?? 0,
    solo_best_score: impact.solo_best_score ?? 0,
    compromise_loss: impact.compromise_loss ?? 0,
    selected_d_set: impact.selected_d_set ?? 0,
    selected_d_orb: impact.selected_d_orb ?? 0,
    solo_best_d_set: impact.solo_best_d_set ?? 0,
    solo_best_d_orb: impact.solo_best_d_orb ?? 0,
    cap_limited: impact.cap_limited ?? false,
  }));

const sharedSlotAssignmentSchema = z
  .object({
    category: z.string(),
    slot_index: z.coerce.number().int().optional(),
    profiles: z.array(z.string()).default([]),
    is_uniform: z.boolean().optional(),
    orb: orbInSchema.nullable().optional(),
    profile_orbs: z.record(z.string(), orbInSchema.nullable()).default({}),
    profile_impacts: z.array(sharedSlotProfileImpactSchema).default([]),
  })
  .transform((slot) => ({
    category: slot.category,
    slot_index: slot.slot_index ?? 0,
    profiles: slot.profiles,
    is_uniform: slot.is_uniform ?? false,
    orb: slot.orb ?? null,
    profile_orbs: slot.profile_orbs ?? {},
    profile_impacts: slot.profile_impacts,
  }));

const sharedSummarySchema = z
  .object({
    requested_slots: z.coerce.number().int().optional(),
    filled_slots: z.coerce.number().int().optional(),
    is_partial: z.boolean().optional(),
    requested_positions: z.coerce.number().int().optional(),
    filled_positions: z.coerce.number().int().optional(),
    active_sets: z.record(z.string(), z.coerce.number().int()).default({}),
    totals_by_type: z.record(z.string(), z.coerce.number()).default({}),
    compromise_loss_total: z.coerce.number().optional(),
    compromise_loss_by_profile: z.record(z.string(), z.coerce.number()).default({}),
    cap_limited_slots_by_profile: z.record(z.string(), z.coerce.number().int()).default({}),
    slots: z.array(sharedSlotAssignmentSchema).default([]),
  })
  .transform((shared) => ({
    requested_slots: shared.requested_slots ?? 0,
    filled_slots: shared.filled_slots ?? 0,
    is_partial: shared.is_partial ?? false,
    requested_positions: shared.requested_positions ?? 0,
    filled_positions: shared.filled_positions ?? 0,
    active_sets: shared.active_sets ?? {},
    totals_by_type: shared.totals_by_type ?? {},
    compromise_loss_total: shared.compromise_loss_total ?? 0,
    compromise_loss_by_profile: shared.compromise_loss_by_profile ?? {},
    cap_limited_slots_by_profile: shared.cap_limited_slots_by_profile ?? {},
    slots: shared.slots,
  }));

const optimizeRawProfileSchema = z
  .object({
    name: z.string(),
    score: z.coerce.number().nullable().optional(),
    set_score: z.coerce.number().nullable().optional(),
    orb_score: z.coerce.number().nullable().optional(),
    requested_slots: z.coerce.number().int().optional(),
    filled_slots: z.coerce.number().int().optional(),
    is_partial: z.boolean().optional(),
    assignments: z.record(z.string(), z.array(orbInSchema).default([])).default({}),
  })
  .transform((profile) => ({
    ...profile,
    score: profile.score ?? null,
    set_score: profile.set_score ?? null,
    orb_score: profile.orb_score ?? null,
    requested_slots: profile.requested_slots ?? 0,
    filled_slots: profile.filled_slots ?? 0,
    is_partial: profile.is_partial ?? false,
  }));

export const optimizeRawPayloadSchema = z
  .object({
    combined_score: z.coerce.number().nullable().optional(),
    requested_slots: z.coerce.number().int().optional(),
    filled_slots: z.coerce.number().int().optional(),
    is_partial: z.boolean().optional(),
    shared_summary: sharedSummarySchema.nullable().optional(),
    profiles: z.array(optimizeRawProfileSchema).default([]),
  })
  .transform((payload) => ({
    ...payload,
    combined_score: payload.combined_score ?? null,
    requested_slots: payload.requested_slots ?? 0,
    filled_slots: payload.filled_slots ?? 0,
    is_partial: payload.is_partial ?? false,
    shared_summary: payload.shared_summary ?? null,
  }));

export const optimizeSummarySchema = z
  .object({
    combined_score: z.coerce.number().nullable().optional(),
    requested_slots: z.coerce.number().int().optional(),
    filled_slots: z.coerce.number().int().optional(),
    is_partial: z.boolean().optional(),
    shared_summary: sharedSummarySchema.nullable().optional(),
    profiles: z
      .array(
        z.object({
          name: z.string(),
          score: z.coerce.number().nullable().optional(),
          set_score: z.coerce.number().nullable().optional(),
          orb_score: z.coerce.number().nullable().optional(),
          requested_slots: z.coerce.number().int().optional(),
          filled_slots: z.coerce.number().int().optional(),
          is_partial: z.boolean().optional(),
        })
      )
      .default([]),
  })
  .transform((summary) => ({
    combined_score: summary.combined_score ?? null,
    requested_slots: summary.requested_slots ?? 0,
    filled_slots: summary.filled_slots ?? 0,
    is_partial: summary.is_partial ?? false,
    shared_summary: summary.shared_summary ?? null,
    profiles: summary.profiles.map((profile) => ({
      ...profile,
      score: profile.score ?? null,
      set_score: profile.set_score ?? null,
      orb_score: profile.orb_score ?? null,
      requested_slots: profile.requested_slots ?? 0,
      filled_slots: profile.filled_slots ?? 0,
      is_partial: profile.is_partial ?? false,
    })),
  }));

export const optimizeResponseSchema = z.object({
  ok: z.literal(true),
  result: z.object({
    summary: optimizeSummarySchema,
    raw: optimizeRawPayloadSchema,
  }),
});

export function parseOptimizeRequest(value: unknown): OptimizeRequest {
  return optimizeRequestSchema.parse(value);
}

export function parseOptimizeResponse(value: unknown): OptimizeResponse {
  return optimizeResponseSchema.parse(value);
}
