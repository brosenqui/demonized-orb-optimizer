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

const optimizeRawProfileSchema = z
  .object({
    name: z.string(),
    score: z.coerce.number().nullable().optional(),
    set_score: z.coerce.number().nullable().optional(),
    orb_score: z.coerce.number().nullable().optional(),
    used_slots: z.record(z.string(), z.coerce.number().int()).default({}),
    assignments: z.record(z.string(), z.array(orbInSchema).default([])).default({}),
  })
  .transform((profile) => ({
    ...profile,
    score: profile.score ?? null,
    set_score: profile.set_score ?? null,
    orb_score: profile.orb_score ?? null,
  }));

export const optimizeRawPayloadSchema = z
  .object({
    combined_score: z.coerce.number().nullable().optional(),
    profiles: z.array(optimizeRawProfileSchema).default([]),
  })
  .transform((payload) => ({
    ...payload,
    combined_score: payload.combined_score ?? null,
  }));

export const optimizeSummarySchema = z
  .object({
    combined_score: z.coerce.number().nullable().optional(),
    per_profile: z
      .array(
        z.object({
          name: z.string(),
          score: z.coerce.number().nullable().optional(),
          set_score: z.coerce.number().nullable().optional(),
          orb_score: z.coerce.number().nullable().optional(),
        })
      )
      .default([]),
  })
  .transform((summary) => ({
    combined_score: summary.combined_score ?? null,
    per_profile: summary.per_profile.map((profile) => ({
      ...profile,
      score: profile.score ?? null,
      set_score: profile.set_score ?? null,
      orb_score: profile.orb_score ?? null,
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
