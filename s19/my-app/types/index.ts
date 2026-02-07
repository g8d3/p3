// Core types matching Prisma schema
import type {
  User as PrismaUser,
  Skill as PrismaSkill,
  Experience as PrismaExperience,
  Purchase as PrismaPurchase,
  Account as PrismaAccount,
  Session as PrismaSession,
  Verification as PrismaVerification,
} from '@prisma/client'

// Re-export with proper names
export type User = PrismaUser
export type Skill = PrismaSkill
export type Experience = PrismaExperience
export type Purchase = PrismaPurchase
export type Account = PrismaAccount
export type Session = PrismaSession
export type Verification = PrismaVerification

// Enums
export enum UserType {
  HUMAN = 'HUMAN',
  AGENT = 'AGENT',
}

export enum Category {
  DATA_PROCESSING = 'DATA_PROCESSING',
  NLP = 'NLP',
  VISION = 'VISION',
  AUTOMATION = 'AUTOMATION',
  ANALYTICS = 'ANALYTICS',
  COMMUNICATION = 'COMMUNICATION',
  CREATIVE = 'CREATIVE',
  RESEARCH = 'RESEARCH',
  DEV_TOOLS = 'DEV_TOOLS',
  FINANCE = 'FINANCE',
  OTHER = 'OTHER',
}

export enum IntegrationType {
  API = 'API',
  MCP = 'MCP',
  WEBSOCKET = 'WEBSOCKET',
  SDK = 'SDK',
  WEBHOOK = 'WEBHOOK',
  GRAPHQL = 'GRAPHQL',
  LIBRARY = 'LIBRARY',
}

export enum PricingType {
  ONE_TIME = 'ONE_TIME',
  SUBSCRIPTION = 'SUBSCRIPTION',
  USAGE_BASED = 'USAGE_BASED',
  FREE = 'FREE',
}

export enum UseCase {
  PRODUCTION = 'PRODUCTION',
  DEVELOPMENT = 'DEVELOPMENT',
  RESEARCH = 'RESEARCH',
  PERSONAL = 'PERSONAL',
  ENTERPRISE = 'ENTERPRISE',
  PROTOTYPING = 'PROTOTYPING',
}

export enum WorkloadSize {
  SMALL = 'SMALL',
  MEDIUM = 'MEDIUM',
  LARGE = 'LARGE',
  ENTERPRISE = 'ENTERPRISE',
}

export enum PaymentMethod {
  POLAR = 'POLAR',
  X402 = 'X402',
  ERC8004 = 'ERC8004',
}

export enum PaymentStatus {
  PENDING = 'PENDING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  REFUNDED = 'REFUNDED',
  DISPUTED = 'DISPUTED',
}

export enum LicenseType {
  PERPETUAL = 'PERPETUAL',
  SUBSCRIPTION = 'SUBSCRIPTION',
  USAGE_BASED = 'USAGE_BASED',
  TRIAL = 'TRIAL',
}

// Extended types with relations
export type UserWithSkills = User & {
  skills: Skill[]
}

export type UserWithExperiences = User & {
  experiences: Experience[]
}

export type UserWithPurchases = User & {
  purchases: Purchase[]
}

export type SkillWithSeller = Skill & {
  seller: User
}

export type SkillWithExperiences = Skill & {
  experiences: Experience[]
}

export type SkillWithRelations = Skill & {
  seller: User
  experiences: Experience[]
  purchases: Purchase[]
}

export type ExperienceWithAuthor = Experience & {
  author: User
}

export type ExperienceWithSkill = Experience & {
  skill: Skill
}

export type ExperienceWithRelations = Experience & {
  author: User
  skill: Skill
  purchase?: Purchase | null
}

export type PurchaseWithBuyer = Purchase & {
  buyer: User
}

export type PurchaseWithSkill = Purchase & {
  skill: Skill
}

export type PurchaseWithRelations = Purchase & {
  buyer: User
  skill: Skill
  experience?: Experience | null
}

// API Response types
export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
}

// Form types
export interface SkillFormData {
  name: string
  slug: string
  description: string
  shortDesc: string
  category: Category
  subcategory?: string
  tags: string[]
  integrationType: IntegrationType
  inputSchema?: Record<string, any>
  outputSchema?: Record<string, any>
  endpointUrl?: string
  documentation?: string
  examples?: Record<string, any>[]
  pricingType: PricingType
  price: number
  currency: string
  x402Price?: string
  x402Currency?: string
  x402Network?: string
  x402Recipient?: string
  erc8004EscrowContract?: string
  version: string
}

export interface ExperienceFormData {
  rating: number
  title?: string
  content: string
  successRate?: number
  avgLatencyMs?: number
  costEfficiency?: number
  easeOfIntegration?: number
  documentationQuality?: number
  supportQuality?: number
  useCase: UseCase
  workloadSize: WorkloadSize
  attachments?: Record<string, any>[]
}

export interface PurchaseFormData {
  paymentMethod: PaymentMethod
  licenseType: LicenseType
  usageQuota?: number
}

// Auth types
export interface AuthUser {
  id: string
  email: string
  name: string
  type: UserType
  walletAddress?: string
  erc8004Id?: string
  reputation: number
  image?: string
  bio?: string
}

// Filter and search types
export interface SkillFilters {
  category?: Category
  subcategory?: string
  tags?: string[]
  integrationType?: IntegrationType
  pricingType?: PricingType
  minRating?: number
  maxPrice?: number
  sellerType?: UserType
  isPublished?: boolean
}

export interface ExperienceFilters {
  rating?: number
  useCase?: UseCase
  workloadSize?: WorkloadSize
  buyerType?: UserType
  isVerifiedPurchase?: boolean
  isVerifiedUsage?: boolean
}

export interface SearchOptions {
  query?: string
  filters?: SkillFilters
  sort?: 'createdAt' | 'avgRating' | 'totalUses' | 'price'
  order?: 'asc' | 'desc'
  page?: number
  limit?: number
}