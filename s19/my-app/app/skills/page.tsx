'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { SearchBar } from '@/components/skills/search-bar';
import { SkillGrid } from '@/components/skills/skill-grid';
import { SkillFilters } from '@/components/skills/skill-filters';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Skill, SkillFilters as SkillFiltersType } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';

// Mock API function
const fetchSkills = async (filters: SkillFiltersType): Promise<Skill[]> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Mock data
  const mockSkills: Skill[] = Array.from({ length: 20 }, (_, i) => ({
    id: `skill-${i + 1}`,
    slug: `skill-${i + 1}`,
    name: `AI Skill ${i + 1}`,
    description: `Advanced AI capability for ${['data processing', 'content generation', 'automation', 'analysis'][i % 4]} with state-of-the-art performance.`,
    price: Math.floor(Math.random() * 200) + 10,
    currency: Math.random() > 0.5 ? 'USD' : 'ETH',
    rating: Math.round((Math.random() * 2 + 3) * 10) / 10,
    reviewCount: Math.floor(Math.random() * 200) + 10,
    seller: {
      id: `seller-${(i % 5) + 1}`,
      name: `AI Provider ${(i % 5) + 1}`,
      avatar: '',
      rating: Math.round((Math.random() * 2 + 3) * 10) / 10
    },
    category: ['Data Processing', 'Content Generation', 'Automation', 'Analysis'][i % 4],
    tags: [['machine-learning', 'nlp'], ['image', 'generation'], ['automation', 'workflow'], ['analytics', 'insights']][i % 4],
    integrationType: ['api', 'sdk', 'plugin'][i % 3] as any,
    createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString()
  }));

  // Apply filters (mock implementation)
  let filtered = mockSkills;
  
  if (filters.search) {
    filtered = filtered.filter(skill => 
      skill.name.toLowerCase().includes(filters.search!.toLowerCase()) ||
      skill.description.toLowerCase().includes(filters.search!.toLowerCase())
    );
  }
  
  if (filters.category) {
    filtered = filtered.filter(skill => skill.category === filters.category);
  }
  
  if (filters.minPrice) {
    filtered = filtered.filter(skill => skill.price >= filters.minPrice!);
  }
  
  if (filters.maxPrice) {
    filtered = filtered.filter(skill => skill.price <= filters.maxPrice!);
  }
  
  if (filters.minRating) {
    filtered = filtered.filter(skill => skill.rating >= filters.minRating!);
  }
  
  if (filters.integrationType) {
    filtered = filtered.filter(skill => skill.integrationType === filters.integrationType);
  }
  
  if (filters.tags && filters.tags.length > 0) {
    filtered = filtered.filter(skill => 
      filters.tags!.some(tag => skill.tags.includes(tag))
    );
  }

  return filtered;
};

export default function SkillsPage() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<SkillFiltersType>({});
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    
    // Initialize filters from URL params
    const initialFilters: SkillFiltersType = {};
    if (searchParams.get('search')) initialFilters.search = searchParams.get('search')!;
    if (searchParams.get('category')) initialFilters.category = searchParams.get('category')!;
    if (searchParams.get('minPrice')) initialFilters.minPrice = Number(searchParams.get('minPrice'));
    if (searchParams.get('maxPrice')) initialFilters.maxPrice = Number(searchParams.get('maxPrice'));
    if (searchParams.get('minRating')) initialFilters.minRating = Number(searchParams.get('minRating'));
    if (searchParams.get('integrationType')) initialFilters.integrationType = searchParams.get('integrationType')!;
    if (searchParams.get('tags')) initialFilters.tags = searchParams.get('tags')!.split(',');
    
    setFilters(initialFilters);
  }, [searchParams]);

  const { data: skills, isLoading, error } = useQuery({
    queryKey: ['skills', filters],
    queryFn: () => fetchSkills(filters),
    enabled: isClient
  });

  const handleSearch = (query: string) => {
    setFilters(prev => ({ ...prev, search: query }));
  };

  const handleFiltersChange = (newFilters: SkillFiltersType) => {
    setFilters(newFilters);
  };

  const activeFilterCount = Object.keys(filters).filter(key => 
    filters[key as keyof SkillFiltersType] !== undefined && 
    filters[key as keyof SkillFiltersType] !== ''
  ).length;

  if (!isClient) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-8">
          <div className="space-y-4">
            <Skeleton className="h-12 w-full max-w-2xl mx-auto" />
            <Skeleton className="h-6 w-32 mx-auto" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-1">
              <Skeleton className="h-96 w-full" />
            </div>
            <div className="lg:col-span-3">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-64 w-full" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">AI Skills Marketplace</h1>
          <p className="text-muted-foreground">
            Discover the perfect AI skills for your project
          </p>
          <SearchBar onSearch={handleSearch} />
        </div>

        {/* Active Filters */}
        {activeFilterCount > 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Active filters:</span>
                  <Badge variant="secondary">{activeFilterCount}</Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleFiltersChange({})}
                >
                  Clear all
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            <SkillFilters
              filters={filters}
              onFiltersChange={handleFiltersChange}
            />
          </div>

          {/* Skills Grid */}
          <div className="lg:col-span-3">
            {error ? (
              <Card>
                <CardContent className="pt-6 text-center">
                  <p className="text-muted-foreground">Failed to load skills. Please try again.</p>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-muted-foreground">
                    {skills ? `${skills.length} skills found` : 'Loading...'}
                  </p>
                  {/* Sort dropdown could go here */}
                </div>
                
                <SkillGrid skills={skills || []} loading={isLoading} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}