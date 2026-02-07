'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { X, Filter } from 'lucide-react';
import { ExperienceFilters } from '@/lib/types';

const useCases = [
  'Production',
  'Development',
  'Testing',
  'Research',
  'Personal Project',
  'Enterprise'
];

const buyerTypes = [
  'Developer',
  'Data Scientist',
  'Product Manager',
  'Business Analyst',
  'Researcher',
  'Student'
];

const workloadSizes = [
  { value: 'small', label: 'Small (< 1K requests)' },
  { value: 'medium', label: 'Medium (1K-10K requests)' },
  { value: 'large', label: 'Large (> 10K requests)' }
];

const sortOptions = [
  { value: 'rating', label: 'Highest Rating' },
  { value: 'date', label: 'Most Recent' },
  { value: 'helpful', label: 'Most Helpful' }
];

interface ExperienceFiltersProps {
  filters: ExperienceFilters;
  onFiltersChange: (filters: ExperienceFilters) => void;
}

export function ExperienceFilters({ filters, onFiltersChange }: ExperienceFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isExpanded, setIsExpanded] = useState(false);

  const updateFilters = (newFilters: Partial<ExperienceFilters>) => {
    const updated = { ...filters, ...newFilters };
    onFiltersChange(updated);
    
    // Update URL
    const params = new URLSearchParams();
    if (updated.rating) params.set('rating', updated.rating.toString());
    if (updated.useCase) params.set('useCase', updated.useCase);
    if (updated.buyerType) params.set('buyerType', updated.buyerType);
    if (updated.workloadSize) params.set('workloadSize', updated.workloadSize);
    if (updated.verifiedOnly) params.set('verifiedOnly', 'true');
    if (updated.sortBy) params.set('sortBy', updated.sortBy);
    
    router.push(`?${params.toString()}`, { scroll: false });
  };

  const clearFilters = () => {
    onFiltersChange({});
    router.push(window.location.pathname, { scroll: false });
  };

  const hasActiveFilters = Object.keys(filters).some(key => 
    filters[key as keyof ExperienceFilters] !== undefined && 
    filters[key as keyof ExperienceFilters] !== ''
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
          Filter Experiences
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
            <CardTitle className="text-lg">Filter Experiences</CardTitle>
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
          {/* Sort */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Sort By</Label>
            <Select
              value={filters.sortBy || 'rating'}
              onValueChange={(value) => updateFilters({ sortBy: value as any })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {sortOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Separator />

          {/* Rating Filter */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Minimum Rating</Label>
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((rating) => (
                <div key={rating} className="flex items-center space-x-2">
                  <Checkbox
                    id={`rating-${rating}`}
                    checked={filters.rating === rating}
                    onCheckedChange={(checked) => 
                      updateFilters({ rating: checked ? rating : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`rating-${rating}`}
                    className="text-sm cursor-pointer"
                  >
                    {rating} {rating === 1 ? 'star' : 'stars'} & up
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Use Case */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Use Case</Label>
            <div className="space-y-2">
              {useCases.map((useCase) => (
                <div key={useCase} className="flex items-center space-x-2">
                  <Checkbox
                    id={`usecase-${useCase}`}
                    checked={filters.useCase === useCase}
                    onCheckedChange={(checked) => 
                      updateFilters({ useCase: checked ? useCase : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`usecase-${useCase}`}
                    className="text-sm cursor-pointer"
                  >
                    {useCase}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Buyer Type */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Buyer Type</Label>
            <div className="space-y-2">
              {buyerTypes.map((buyerType) => (
                <div key={buyerType} className="flex items-center space-x-2">
                  <Checkbox
                    id={`buyer-${buyerType}`}
                    checked={filters.buyerType === buyerType}
                    onCheckedChange={(checked) => 
                      updateFilters({ buyerType: checked ? buyerType : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`buyer-${buyerType}`}
                    className="text-sm cursor-pointer"
                  >
                    {buyerType}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Workload Size */}
          <div>
            <Label className="text-sm font-medium mb-2 block">Workload Size</Label>
            <div className="space-y-2">
              {workloadSizes.map((size) => (
                <div key={size.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`workload-${size.value}`}
                    checked={filters.workloadSize === size.value}
                    onCheckedChange={(checked) => 
                      updateFilters({ workloadSize: checked ? size.value : undefined })
                    }
                  />
                  <Label 
                    htmlFor={`workload-${size.value}`}
                    className="text-sm cursor-pointer"
                  >
                    {size.label}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Verified Only */}
          <div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="verified-only"
                checked={filters.verifiedOnly || false}
                onCheckedChange={(checked) => 
                  updateFilters({ verifiedOnly: checked as boolean })
                }
              />
              <Label 
                htmlFor="verified-only"
                className="text-sm cursor-pointer"
              >
                Verified purchases only
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}