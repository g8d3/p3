import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SearchBar } from '@/components/skills/search-bar';
import { SkillGrid } from '@/components/skills/skill-grid';
import { ArrowRight, Star, Zap, Shield, TrendingUp, Users, Code, Brain, Search } from 'lucide-react';

// Mock data
const featuredSkills = [
  {
    id: '1',
    slug: 'nlp-sentiment-analysis',
    name: 'Advanced Sentiment Analysis',
    description: 'State-of-the-art NLP model for accurate sentiment analysis on text data with 95% accuracy.',
    price: 49,
    currency: 'USD' as const,
    rating: 4.8,
    reviewCount: 124,
    seller: {
      id: 'seller-1',
      name: 'AI Labs',
      avatar: '',
      rating: 4.9
    },
    category: 'Data Processing',
    tags: ['nlp', 'sentiment', 'machine-learning', 'api'],
    integrationType: 'api' as const,
    createdAt: '2024-01-15',
    updatedAt: '2024-01-15'
  },
  {
    id: '2',
    slug: 'image-generation',
    name: 'AI Image Generator',
    description: 'Generate high-quality images from text prompts using advanced diffusion models.',
    price: 29,
    currency: 'USD' as const,
    rating: 4.6,
    reviewCount: 89,
    seller: {
      id: 'seller-2',
      name: 'Creative AI',
      avatar: '',
      rating: 4.7
    },
    category: 'Content Generation',
    tags: ['image', 'generation', 'ai', 'creative'],
    integrationType: 'api' as const,
    createdAt: '2024-01-10',
    updatedAt: '2024-01-10'
  },
  {
    id: '3',
    slug: 'data-automation',
    name: 'Smart Data Automation',
    description: 'Automate data processing workflows with intelligent decision-making capabilities.',
    price: 79,
    currency: 'USD' as const,
    rating: 4.9,
    reviewCount: 56,
    seller: {
      id: 'seller-3',
      name: 'Automation Pro',
      avatar: '',
      rating: 4.8
    },
    category: 'Automation',
    tags: ['automation', 'data', 'workflow', 'integration'],
    integrationType: 'sdk' as const,
    createdAt: '2024-01-08',
    updatedAt: '2024-01-08'
  }
];

const categories = [
  { name: 'Data Processing', icon: Brain, description: 'Process and analyze data with AI', count: 234 },
  { name: 'Content Generation', icon: Code, description: 'Generate text, images, and more', count: 189 },
  { name: 'Automation', icon: Zap, description: 'Automate workflows and tasks', count: 156 },
  { name: 'Analysis', icon: TrendingUp, description: 'Advanced analytics and insights', count: 145 },
  { name: 'Integration', icon: Shield, description: 'Connect with existing systems', count: 98 },
  { name: 'Security', icon: Users, description: 'AI-powered security solutions', count: 67 }
];

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center space-y-8 py-16">
        <div className="space-y-4">
          <Badge variant="secondary" className="mb-4">
            🚀 The Future of AI Skills
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
            Discover & Sell
            <span className="text-primary"> AI Agent Skills</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            The premier marketplace for cutting-edge AI capabilities. 
            Find the perfect skill for your project or monetize your AI innovations.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" asChild>
            <Link href="/skills">
              Explore Skills <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/sell">
              Start Selling
            </Link>
          </Button>
        </div>

        <div className="max-w-2xl mx-auto">
          <SearchBar />
        </div>
      </section>

      {/* Featured Skills */}
      <section className="space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold">Featured Skills</h2>
          <p className="text-muted-foreground">Discover the most popular AI skills this week</p>
        </div>
        
        <SkillGrid skills={featuredSkills} />
        
        <div className="text-center">
          <Button variant="outline" size="lg" asChild>
            <Link href="/skills">
              View All Skills <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      {/* Categories */}
      <section className="space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold">Browse Categories</h2>
          <p className="text-muted-foreground">Find skills by category</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <Link key={category.name} href={`/skills?category=${category.name.toLowerCase()}`}>
                <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Icon className="h-6 w-6 text-primary" />
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-lg">{category.name}</CardTitle>
                        <CardDescription>{category.description}</CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {category.count} skills
                      </span>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>

      {/* How It Works */}
      <section className="space-y-8">
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-bold">How It Works</h2>
          <p className="text-muted-foreground">Get started in minutes</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card className="text-center">
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>1. Discover</CardTitle>
              <CardDescription>
                Browse our marketplace to find the perfect AI skills for your needs
              </CardDescription>
            </CardHeader>
          </Card>
          
          <Card className="text-center">
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>2. Purchase</CardTitle>
              <CardDescription>
                Buy skills securely using fiat, crypto, or escrow payments
              </CardDescription>
            </CardHeader>
          </Card>
          
          <Card className="text-center">
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>3. Integrate</CardTitle>
              <CardDescription>
                Seamlessly integrate AI skills into your applications via API or SDK
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-muted/50 rounded-lg p-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div className="space-y-2">
            <div className="text-3xl font-bold text-primary">1,200+</div>
            <div className="text-sm text-muted-foreground">AI Skills</div>
          </div>
          <div className="space-y-2">
            <div className="text-3xl font-bold text-primary">15,000+</div>
            <div className="text-sm text-muted-foreground">Active Users</div>
          </div>
          <div className="space-y-2">
            <div className="text-3xl font-bold text-primary">98%</div>
            <div className="text-sm text-muted-foreground">Satisfaction</div>
          </div>
          <div className="space-y-2">
            <div className="text-3xl font-bold text-primary">24/7</div>
            <div className="text-sm text-muted-foreground">Support</div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="text-center space-y-8 py-16">
        <div className="space-y-4">
          <h2 className="text-3xl font-bold">Ready to Get Started?</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Join thousands of developers and businesses leveraging AI skills to build amazing products.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" asChild>
            <Link href="/skills">
              Explore Skills
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/sell">
              List Your Skill
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}