import { z } from 'zod'

// Base schemas
export const baseUserSchema = z.object({
  email: z.string().email('Invalid email address'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
  type: z.nativeEnum(UserType),
  walletAddress: z.string().optional(),
  erc8004Id: z.string().optional(),
  bio: z.string().max(1000, 'Bio must be less than 1000 characters').optional(),
  image: z.string().url('Invalid image URL').optional(),
})

// Skill validation schemas
export const skillCreateSchema = z.object({
  name: z.string().min(2, 'Skill name must be at least 2 characters').max(100, 'Skill name must be less than 100 characters'),
  slug: z.string()
    .min(2, 'Slug must be at least 2 characters')
    .max(100, 'Slug must be less than 100 characters')
    .regex(/^[a-z0-9-]+$/, 'Slug can only contain lowercase letters, numbers, and hyphens'),
  description: z.string().min(10, 'Description must be at least 10 characters').max(5000, 'Description must be less than 5000 characters'),
  shortDesc: z.string().min(10, 'Short description must be at least 10 characters').max(200, 'Short description must be less than 200 characters'),
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']),
  subcategory: z.string().max(50, 'Subcategory must be less than 50 characters').optional(),
  tags: z.array(z.string().max(30, 'Tag must be less than 30 characters')).max(10, 'Maximum 10 tags allowed'),
  integrationType: z.enum(['API', 'MCP', 'WEBSOCKET', 'SDK', 'WEBHOOK', 'GRAPHQL', 'LIBRARY']),
  inputSchema: z.record(z.any()).optional(),
  outputSchema: z.record(z.any()).optional(),
  endpointUrl: z.string().url('Invalid endpoint URL').optional(),
  documentation: z.string().max(10000, 'Documentation must be less than 10000 characters').optional(),
  examples: z.array(z.record(z.any())).optional(),
  pricingType: z.enum(['ONE_TIME', 'SUBSCRIPTION', 'USAGE_BASED', 'FREE']),
  price: z.number().min(0, 'Price must be non-negative').max(999999.99, 'Price must be less than 1,000,000'),
  currency: z.string().length(3, 'Currency must be a 3-letter code').default('USD'),
  x402Price: z.string().optional(),
  x402Currency: z.string().length(3, 'Currency must be a 3-letter code').optional(),
  x402Network: z.string().optional(),
  x402Recipient: z.string().optional(),
  erc8004EscrowContract: z.string().optional(),
  version: z.string().regex(/^\d+\.\d+\.\d+$/, 'Version must follow semantic versioning (x.y.z)').default('1.0.0'),
  isPublished: z.boolean().default(false),
})

export const skillUpdateSchema = skillCreateSchema.partial()

// Experience validation schemas
export const experienceCreateSchema = z.object({
  rating: z.number().int('Rating must be an integer').min(1, 'Rating must be at least 1').max(5, 'Rating must be at most 5'),
  title: z.string().max(100, 'Title must be less than 100 characters').optional(),
  content: z.string().min(10, 'Content must be at least 10 characters').max(2000, 'Content must be less than 2000 characters'),
  successRate: z.number().min(0, 'Success rate must be between 0 and 100').max(100, 'Success rate must be between 0 and 100').optional(),
  avgLatencyMs: z.number().int('Latency must be an integer').min(0, 'Latency must be non-negative').optional(),
  costEfficiency: z.number().min(1, 'Cost efficiency must be between 1 and 5').max(5, 'Cost efficiency must be between 1 and 5').optional(),
  easeOfIntegration: z.number().min(1, 'Ease of integration must be between 1 and 5').max(5, 'Ease of integration must be between 1 and 5').optional(),
  documentationQuality: z.number().min(1, 'Documentation quality must be between 1 and 5').max(5, 'Documentation quality must be between 1 and 5').optional(),
  supportQuality: z.number().min(1, 'Support quality must be between 1 and 5').max(5, 'Support quality must be between 1 and 5').optional(),
  useCase: z.enum(['PRODUCTION', 'DEVELOPMENT', 'RESEARCH', 'PERSONAL', 'ENTERPRISE', 'PROTOTYPING']),
  workloadSize: z.enum(['SMALL', 'MEDIUM', 'LARGE', 'ENTERPRISE']),
  attachments: z.array(z.record(z.any())).optional(),
})

export const experienceUpdateSchema = experienceCreateSchema.partial()

// Purchase validation schemas
export const purchaseCreateSchema = z.object({
  skillId: z.string().uuid('Invalid skill ID'),
  paymentMethod: z.enum(['POLAR', 'X402', 'ERC8004']),
  licenseType: z.enum(['PERPETUAL', 'SUBSCRIPTION', 'USAGE_BASED', 'TRIAL']).default('PERPETUAL' as any),
  usageQuota: z.number().int('Usage quota must be an integer').min(1, 'Usage quota must be at least 1').optional(),
})

export const purchaseUpdateSchema = z.object({
  paymentStatus: z.enum(['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED']).optional(),
  licenseKey: z.string().optional(),
  expiresAt: z.date().optional(),
  usageQuota: z.number().int('Usage quota must be an integer').min(1, 'Usage quota must be at least 1').optional(),
})

// User validation schemas
export const userUpdateSchema = baseUserSchema.partial().omit({
  id: true,
  email: true,
  createdAt: true,
  updatedAt: true,
  reputation: true,
})

// Search and filter schemas
export const skillFiltersSchema = z.object({
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']).optional(),
  subcategory: z.string().optional(),
  tags: z.array(z.string()).optional(),
  integrationType: z.enum(['API', 'MCP', 'WEBSOCKET', 'SDK', 'WEBHOOK', 'GRAPHQL', 'LIBRARY']).optional(),
  pricingType: z.enum(['ONE_TIME', 'SUBSCRIPTION', 'USAGE_BASED', 'FREE']).optional(),
  minRating: z.number().min(0).max(5).optional(),
  maxPrice: z.number().min(0).optional(),
  sellerType: z.enum(['HUMAN', 'AGENT']).optional(),
  isPublished: z.boolean().optional(),
})

export const searchOptionsSchema = z.object({
  query: z.string().max(100, 'Search query must be less than 100 characters').optional(),
  filters: skillFiltersSchema.optional(),
  sort: z.enum(['createdAt', 'avgRating', 'totalUses', 'price']).optional(),
  order: z.enum(['asc', 'desc']).default('desc'),
  page: z.number().int('Page must be an integer').min(1, 'Page must be at least 1').default(1),
  limit: z.number().int('Limit must be an integer').min(1, 'Limit must be at least 1').max(100, 'Limit must be at most 100').default(20),
})

// Auth schemas
export const signInSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

export const signUpSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  name: z.string().min(2, 'Name must be at least 2 characters'),
  type: z.enum(['HUMAN', 'AGENT']).default('HUMAN' as any),
})

export const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
})

export const resetPasswordSchema = z.object({
  token: z.string(),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

// Type exports
export type SkillCreateInput = z.infer<typeof skillCreateSchema>
export type SkillUpdateInput = z.infer<typeof skillUpdateSchema>
export type ExperienceCreateInput = z.infer<typeof experienceCreateSchema>
export type ExperienceUpdateInput = z.infer<typeof experienceUpdateSchema>
export type PurchaseCreateInput = z.infer<typeof purchaseCreateSchema>
export type PurchaseUpdateInput = z.infer<typeof purchaseUpdateSchema>
export type UserUpdateInput = z.infer<typeof userUpdateSchema>
export type SkillFilters = z.infer<typeof skillFiltersSchema>
export type SearchOptions = z.infer<typeof searchOptionsSchema>
export type SignInInput = z.infer<typeof signInSchema>
export type SignUpInput = z.infer<typeof signUpSchema>
export type ForgotPasswordInput = z.infer<typeof forgotPasswordSchema>
export type ResetPasswordInput = z.infer<typeof resetPasswordSchema>