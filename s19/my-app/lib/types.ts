export interface Skill {
  id: string;
  slug: string;
  name: string;
  description: string;
  price: number;
  currency: 'USD' | 'ETH';
  rating: number;
  reviewCount: number;
  seller: {
    id: string;
    name: string;
    avatar?: string;
    rating: number;
  };
  category: string;
  tags: string[];
  integrationType: 'api' | 'sdk' | 'plugin';
  createdAt: string;
  updatedAt: string;
}

export interface Experience {
  id: string;
  skillId: string;
  rating: number;
  title: string;
  content: string;
  author: {
    id: string;
    name: string;
    avatar?: string;
  };
  metrics: {
    successRate: number;
    latency: number;
    reliability: number;
    easeOfUse: number;
  };
  useCase: string;
  buyerType: string;
  workloadSize: 'small' | 'medium' | 'large';
  verified: boolean;
  helpful: number;
  unhelpful: number;
  createdAt: string;
}

export interface PaymentMethod {
  type: 'polar' | 'x402' | 'erc8004';
  address?: string;
  cardLast4?: string;
}

export interface SkillFilters {
  category?: string;
  minPrice?: number;
  maxPrice?: number;
  minRating?: number;
  integrationType?: string;
  tags?: string[];
  search?: string;
}

export interface ExperienceFilters {
  rating?: number;
  useCase?: string;
  buyerType?: string;
  workloadSize?: string;
  verifiedOnly?: boolean;
  sortBy?: 'rating' | 'date' | 'helpful';
}