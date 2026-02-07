'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { X, Filter } from 'lucide-react';
import { SkillFilters } from '@/lib/types';

const categories = [
  'Data Processing',
  'Content Generation',
  'Automation',
  'Analysis',
  'Integration',
  'Security',
  'Monitoring',
  'Communication'
];

const integrationTypes = [
  'API',
  'SDK',
  'Plugin'
];

const popularTags = [
  'machine-learning',
  'nlp',
  'computer-vision',
  'web-scraping',
  'data-analysis',
  'automation',
  'ai',
  'python',
  'javascript',
  'rest-api'
];

interface SkillFiltersProps {
  filters: SkillFilters;
  onFiltersChange: (filters: SkillFilters) => void;
}

export function SkillFilters({ filters, onFiltersChange }: SkillFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isExpanded, setIsExpanded] = useState(false);

  const updateFilters = (newFilters: Partial<SkillFilters>) => {
    const updated = { ...filters, ...newFilters };
    onFiltersChange(updated);
    
    // Update URL
    const params = new URLSearchParams();
    if (updated.search) params.set('search', updated.search);
    if (updated.category) params.set('category', updated.category);
    if (updated.minPrice) params.set('minPrice', updated.minPrice.toString());
    if (updated.maxPrice) params.set('maxPrice', updated.maxPrice.toString());
    if (updated.minRating) params.set('minRating', updated.minRating.toString());
    if (updated.integrationType) params.set('integrationType', updated.integrationType);
    if (updated.tags?.length) params.set('tags', updated.tags.join(','));
    
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const clearFilters = () => {
    onFiltersChange({});
    router.push('/skills', { scroll: false });
  };

  const hasActiveFilters = Object.keys(filters).some(key => 
    filters[key as keyof SkillFilters] !== undefined && 
    filters[key as keyof SkillFilters] !== ''
  );

  return (
    <>
      {/* Mobile filter toggle */}
      <div className="lg:hidden mb-4">
        <Button
          variant="outline"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full"
        >
          <Filter className="h-4 w-4 mr-2" />
          Filters
          {hasActiveFilters && (
            <Badge variant="secondary" className="ml-2">
              Active
            </Badge>
          )}
        </Button>
      </div>

      {/* Filters sidebar */}
      <Card className={`lg:sticky lg:top-4 ${isExpanded ? 'block' : 'hidden lg:block'}`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Filters</CardTitle>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-muted-foreground"
              >
                <X className="h-4 w-4 mr-1" />
                Clear
              </Button>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Category */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Category</Label>
            <div className="space-y-2">
              {categories.map((category) => (
                <div key={category} className="flex items-center space-x-2">
                  <Checkbox
                    id={`category-${category}`}
                    checked={filters.category === category}
                    onCheckedChange={(checked) => 
                      updateFilters({ category: checked ? category : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`category-${category}`}
                    className="text-sm cursor-pointer"
                  >
                    {category}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Price Range */}
          <div>
            <Label className="text-sm font-medium mb-2 block">
              Price Range: ${filters.minPrice || 0} - ${filters.maxPrice || 1000}
            </Label>
            <Slider
              value={[filters.minPrice || 0, filters.maxPrice || 1000]}
              onValueChange={([min, max]) => 
                updateFilters({ minPrice: min, maxPrice: max })
              }
              max={1000}
              step={10}
              className="w-full"
            />
          </div>

          <Separator />

          {/* Rating */}
          <div>
            <Label className="text-sm font-medium mb-2 block">
              Minimum Rating: {filters.minRating || 0}+
            </Label>
            <Slider
              value={[filters.minRating || 0]}
              onValueChange={([rating]) => 
                updateFilters({ minRating: rating })
              }
              max={5}
              step={0.5}
              className="w-full"
            />
          </div>

          <Separator />

          {/* Integration Type */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Integration Type</Label>
            <div className="space-y-2">
              {integrationTypes.map((type) => (
                <div key={type} className="flex items-center space-x-2">
                  <Checkbox
                    id={`integration-${type}`}
                    checked={filters.integrationType === type.toLowerCase()}
                    onCheckedChange={(checked) => 
                      updateFilters({ integrationType: checked ? type.toLowerCase() : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`integration-${type}`}
                    className="text-sm cursor-pointer"
                  >
                    {type}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Tags */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Popular Tags</Label>
            <div className="flex flex-wrap gap-2">
              {popularTags.map((tag) => (
                <Badge
                  key={tag}
                  variant={filters.tags?.includes(tag) ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => {
                    const currentTags = filters.tags || [];
                    const newTags = currentTags.includes(tag)
                      ? currentTags.filter(t => t !== tag)
                      : [...currentTags, tag];
                    updateFilters({ tags: newTags.length ? newTags : undefined });
                  }}
                >
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}