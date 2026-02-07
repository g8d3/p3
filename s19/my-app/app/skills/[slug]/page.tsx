'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PaymentMethodSelector } from '@/components/payments/payment-method-selector';
import { ExperienceCard } from '@/components/experiences/experience-card';
import { ExperienceFilters } from '@/components/experiences/experience-filters';
import { ExperienceForm } from '@/components/experiences/experience-form';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Star, MapPin, CheckCircle, Clock, Shield, Zap, Users, Calendar, ArrowRight } from 'lucide-react';
import { Skill, Experience, ExperienceFilters as ExperienceFiltersType } from '@/lib/types';

// Mock data
const mockSkill: Skill = {
  id: '1',
  slug: 'advanced-sentiment-analysis',
  name: 'Advanced Sentiment Analysis',
  description: 'State-of-the-art NLP model for accurate sentiment analysis on text data with 95% accuracy. Perfect for social media monitoring, customer feedback analysis, and market research.',
  price: 49,
  currency: 'USD',
  rating: 4.8,
  reviewCount: 124,
  seller: {
    id: 'seller-1',
    name: 'AI Labs',
    avatar: '',
    rating: 4.9
  },
  category: 'Data Processing',
  tags: ['nlp', 'sentiment', 'machine-learning', 'api', 'text-analysis'],
  integrationType: 'api',
  createdAt: '2024-01-15',
  updatedAt: '2024-01-15'
};

const mockExperiences: Experience[] = Array.from({ length: 5 }, (_, i) => ({
  id: `exp-${i + 1}`,
  skillId: '1',
  rating: Math.floor(Math.random() * 2) + 4,
  title: `Great experience with sentiment analysis ${i + 1}`,
  content: `This skill has been incredibly useful for our customer feedback analysis. The accuracy is impressive and the API is well-documented. Highly recommend for anyone needing sentiment analysis capabilities.`,
  author: {
    id: `user-${i + 1}`,
    name: `User ${i + 1}`,
    avatar: ''
  },
  metrics: {
    successRate: Math.floor(Math.random() * 20) + 80,
    latency: Math.floor(Math.random() * 200) + 100,
    reliability: Math.floor(Math.random() * 15) + 85,
    easeOfUse: Math.floor(Math.random() * 20) + 80
  },
  useCase: ['Production', 'Development', 'Testing'][i % 3],
  buyerType: ['Developer', 'Data Scientist', 'Product Manager'][i % 3],
  workloadSize: ['small', 'medium', 'large'][i % 3] as any,
  verified: i % 2 === 0,
  helpful: Math.floor(Math.random() * 20) + 5,
  unhelpful: Math.floor(Math.random() * 5),
  createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString()
}));

export default function SkillDetailPage() {
  const params = useParams();
  const [skill] = useState<Skill>(mockSkill);
  const [experiences, setExperiences] = useState<Experience[]>(mockExperiences);
  const [experienceFilters, setExperienceFilters] = useState<ExperienceFiltersType>({});
  const [showPurchaseDialog, setShowPurchaseDialog] = useState(false);
  const [showReviewDialog, setShowReviewDialog] = useState(false);

  const handlePurchase = (paymentMethod: any) => {
    console.log('Purchase with:', paymentMethod);
    // Handle purchase logic
    setShowPurchaseDialog(false);
  };

  const handleReviewSubmit = (reviewData: any) => {
    console.log('Review submitted:', reviewData);
    // Handle review submission
    setShowReviewDialog(false);
  };

  const MetricIcon = ({ metric }: { metric: string }) => {
    switch (metric) {
      case 'successRate':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'latency':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'reliability':
        return <Shield className="h-4 w-4 text-purple-500" />;
      case 'easeOfUse':
        return <Zap className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getMetricLabel = (metric: string) => {
    switch (metric) {
      case 'successRate':
        return 'Success Rate';
      case 'latency':
        return 'Avg Latency';
      case 'reliability':
        return 'Reliability';
      case 'easeOfUse':
        return 'Ease of Use';
      default:
        return metric;
    }
  };

  const averageMetrics = experiences.reduce((acc, exp) => {
    Object.keys(exp.metrics).forEach(key => {
      if (!acc[key as keyof typeof acc]) {
        acc[key as keyof typeof acc] = 0;
      }
      acc[key as keyof typeof acc] += exp.metrics[key as keyof typeof exp.metrics];
    });
    return acc;
  }, {} as Record<string, number>);

  Object.keys(averageMetrics).forEach(key => {
    averageMetrics[key] = Math.round(averageMetrics[key] / experiences.length);
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Skill Header */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{skill.category}</Badge>
              <Badge variant="outline">{skill.integrationType}</Badge>
            </div>
            
            <h1 className="text-3xl font-bold">{skill.name}</h1>
            
            <p className="text-muted-foreground text-lg leading-relaxed">
              {skill.description}
            </p>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    className={`h-5 w-5 ${
                      i < Math.floor(skill.rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-300'
                    }`}
                  />
                ))}
                <span className="ml-2 font-medium">{skill.rating}</span>
                <span className="text-muted-foreground">({skill.reviewCount} reviews)</span>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2">
              {skill.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="api">API</TabsTrigger>
              <TabsTrigger value="examples">Examples</TabsTrigger>
              <TabsTrigger value="support">Support</TabsTrigger>
            </TabsList>
            
            <TabsContent value="overview" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Performance Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(averageMetrics).map(([metric, value]) => (
                      <div key={metric} className="text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                          <MetricIcon metric={metric} />
                        </div>
                        <div className="text-2xl font-bold">
                          {metric === 'latency' ? `${value}ms` : `${value}%`}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {getMetricLabel(metric)}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>Features</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>95% accuracy on sentiment analysis</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>Support for 50+ languages</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>Real-time processing</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>RESTful API with comprehensive documentation</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="api" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>API Documentation</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">Endpoint</h4>
                    <code className="bg-muted px-2 py-1 rounded text-sm">
                      POST https://api.skillsmarket.ai/v1/sentiment
                    </code>
                  </div>
                  
                  <div>
                    <h4 className="font-medium mb-2">Example Request</h4>
                    <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
{`{
  "text": "I love this product! It's amazing.",
  "language": "en"
}`}
                    </pre>
                  </div>
                  
                  <div>
                    <h4 className="font-medium mb-2">Example Response</h4>
                    <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
{`{
  "sentiment": "positive",
  "confidence": 0.95,
  "score": 0.87
}`}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="examples" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Code Examples</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">Python</h4>
                      <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
{`import requests

response = requests.post(
    'https://api.skillsmarket.ai/v1/sentiment',
    json={
        'text': 'This is great!',
        'language': 'en'
    },
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)

result = response.json()
print(result['sentiment'])`}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="support" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Support & Documentation</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Button variant="outline" className="justify-start">
                      <MapPin className="h-4 w-4 mr-2" />
                      View Documentation
                    </Button>
                    <Button variant="outline" className="justify-start">
                      <Users className="h-4 w-4 mr-2" />
                      Community Forum
                    </Button>
                    <Button variant="outline" className="justify-start">
                      <Calendar className="h-4 w-4 mr-2" />
                      Schedule Demo
                    </Button>
                    <Button variant="outline" className="justify-start">
                      <Shield className="h-4 w-4 mr-2" />
                      Contact Support
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Experiences Section */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold">User Experiences</h2>
              <Dialog open={showReviewDialog} onOpenChange={setShowReviewDialog}>
                <DialogTrigger asChild>
                  <Button>Share Your Experience</Button>
                </DialogTrigger>
                <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Share Your Experience</DialogTitle>
                  </DialogHeader>
                  <ExperienceForm
                    skillId={skill.id}
                    skillName={skill.name}
                    onSubmit={handleReviewSubmit}
                    onCancel={() => setShowReviewDialog(false)}
                  />
                </DialogContent>
              </Dialog>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
              <div className="lg:col-span-1">
                <ExperienceFilters
                  filters={experienceFilters}
                  onFiltersChange={setExperienceFilters}
                />
              </div>
              
              <div className="lg:col-span-3 space-y-4">
                {experiences.map((experience) => (
                  <ExperienceCard key={experience.id} experience={experience} />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Purchase Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">
                ${skill.price} {skill.currency}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Dialog open={showPurchaseDialog} onOpenChange={setShowPurchaseDialog}>
                <DialogTrigger asChild>
                  <Button className="w-full" size="lg">
                    Purchase Skill
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Complete Purchase</DialogTitle>
                  </DialogHeader>
                  <PaymentMethodSelector
                    amount={skill.price}
                    currency={skill.currency}
                    onPaymentMethodChange={handlePurchase}
                  />
                </DialogContent>
              </Dialog>
              
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex justify-between">
                  <span>Base price</span>
                  <span>${skill.price}</span>
                </div>
                <div className="flex justify-between">
                  <span>Processing fee</span>
                  <span>$2.50</span>
                </div>
                <Separator />
                <div className="flex justify-between font-medium">
                  <span>Total</span>
                  <span>${skill.price + 2.50}</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Shield className="h-4 w-4 text-green-500" />
                  <span>Secure payment</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Instant access</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-green-500" />
                  <span>24/7 support</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Seller Info */}
          <Card>
            <CardHeader>
              <CardTitle>Seller</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12">
                  <AvatarImage src={skill.seller.avatar} />
                  <AvatarFallback>{skill.seller.name[0]}</AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-medium">{skill.seller.name}</h3>
                  <div className="flex items-center gap-1">
                    <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                    <span className="text-sm">{skill.seller.rating}</span>
                  </div>
                </div>
              </div>
              
              <Button variant="outline" className="w-full">
                View Profile
              </Button>
              
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex justify-between">
                  <span>Skills listed</span>
                  <span>12</span>
                </div>
                <div className="flex justify-between">
                  <span>Total sales</span>
                  <span>1,247</span>
                </div>
                <div className="flex justify-between">
                  <span>Member since</span>
                  <span>Jan 2023</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Related Skills */}
          <Card>
            <CardHeader>
              <CardTitle>Related Skills</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {['Text Classification', 'Entity Recognition', 'Language Translation'].map((name, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{name}</p>
                    <p className="text-xs text-muted-foreground">${20 + i * 10}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}