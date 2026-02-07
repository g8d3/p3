'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Star, CheckCircle, Clock, Shield, Zap } from 'lucide-react';
import { toast } from 'sonner';

interface ExperienceFormData {
  rating: number;
  title: string;
  content: string;
  useCase: string;
  buyerType: string;
  workloadSize: string;
  metrics: {
    successRate: number;
    latency: number;
    reliability: number;
    easeOfUse: number;
  };
}

interface ExperienceFormProps {
  skillId: string;
  skillName: string;
  onSubmit: (data: ExperienceFormData) => void;
  onCancel: () => void;
}

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

export function ExperienceForm({ skillId, skillName, onSubmit, onCancel }: ExperienceFormProps) {
  const [formData, setFormData] = useState<ExperienceFormData>({
    rating: 0,
    title: '',
    content: '',
    useCase: '',
    buyerType: '',
    workloadSize: '',
    metrics: {
      successRate: 50,
      latency: 500,
      reliability: 50,
      easeOfUse: 50
    }
  });

  const [hoveredRating, setHoveredRating] = useState(0);

  const handleRatingChange = (rating: number) => {
    setFormData(prev => ({ ...prev, rating }));
  };

  const handleMetricChange = (metric: keyof typeof formData.metrics, value: number) => {
    setFormData(prev => ({
      ...prev,
      metrics: {
        ...prev.metrics,
        [metric]: value
      }
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.rating) {
      toast.error('Please select a rating');
      return;
    }
    
    if (!formData.title.trim()) {
      toast.error('Please enter a title');
      return;
    }
    
    if (!formData.content.trim()) {
      toast.error('Please enter your experience');
      return;
    }
    
    if (!formData.useCase) {
      toast.error('Please select a use case');
      return;
    }
    
    if (!formData.buyerType) {
      toast.error('Please select your buyer type');
      return;
    }
    
    if (!formData.workloadSize) {
      toast.error('Please select workload size');
      return;
    }

    onSubmit(formData);
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
        return 'Latency (ms)';
      case 'reliability':
        return 'Reliability';
      case 'easeOfUse':
        return 'Ease of Use';
      default:
        return metric;
    }
  };

  const getMetricMax = (metric: string) => {
    switch (metric) {
      case 'successRate':
      case 'reliability':
      case 'easeOfUse':
        return 100;
      case 'latency':
        return 5000;
      default:
        return 100;
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>Share Your Experience</CardTitle>
        <p className="text-muted-foreground">
          Tell others about your experience using <strong>{skillName}</strong>
        </p>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Rating */}
          <div>
            <Label className="text-sm font-medium mb-3 block">Overall Rating</Label>
            <div className="flex items-center gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleRatingChange(i + 1)}
                  onMouseEnter={() => setHoveredRating(i + 1)}
                  onMouseLeave={() => setHoveredRating(0)}
                  className="transition-colors"
                >
                  <Star
                    className={`h-8 w-8 ${
                      i < (hoveredRating || formData.rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-300 hover:text-yellow-200'
                    }`}
                  />
                </button>
              ))}
              {formData.rating > 0 && (
                <span className="ml-2 text-sm text-muted-foreground">
                  {formData.rating} of 5 stars
                </span>
              )}
            </div>
          </div>

          <Separator />

          {/* Title and Content */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                placeholder="Summarize your experience in one sentence"
                value={formData.title}
                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                maxLength={100}
              />
            </div>
            
            <div>
              <Label htmlFor="content">Your Experience</Label>
              <Textarea
                id="content"
                placeholder="Describe your experience with this AI skill. What did you like? What could be improved?"
                value={formData.content}
                onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                rows={6}
                maxLength={1000}
              />
              <p className="text-xs text-muted-foreground mt-1">
                {formData.content.length}/1000 characters
              </p>
            </div>
          </div>

          <Separator />

          {/* Use Case and Buyer Type */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label>Use Case</Label>
              <Select
                value={formData.useCase}
                onValueChange={(value) => setFormData(prev => ({ ...prev, useCase: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select use case" />
                </SelectTrigger>
                <SelectContent>
                  {useCases.map((useCase) => (
                    <SelectItem key={useCase} value={useCase}>
                      {useCase}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Your Role</Label>
              <Select
                value={formData.buyerType}
                onValueChange={(value) => setFormData(prev => ({ ...prev, buyerType: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select your role" />
                </SelectTrigger>
                <SelectContent>
                  {buyerTypes.map((buyerType) => (
                    <SelectItem key={buyerType} value={buyerType}>
                      {buyerType}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Workload Size</Label>
              <Select
                value={formData.workloadSize}
                onValueChange={(value) => setFormData(prev => ({ ...prev, workloadSize: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select workload" />
                </SelectTrigger>
                <SelectContent>
                  {workloadSizes.map((size) => (
                    <SelectItem key={size.value} value={size.value}>
                      {size.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          {/* Performance Metrics */}
          <div>
            <Label className="text-sm font-medium mb-4 block">Performance Metrics</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {Object.entries(formData.metrics).map(([metric, value]) => (
                <div key={metric} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <MetricIcon metric={metric} />
                    <Label className="text-sm">
                      {getMetricLabel(metric)}: {metric === 'latency' ? `${value}ms` : `${value}%`}
                    </Label>
                  </div>
                  <Slider
                    value={[value]}
                    onValueChange={([newValue]) => handleMetricChange(metric as keyof typeof formData.metrics, newValue)}
                    max={getMetricMax(metric)}
                    min={metric === 'latency' ? 0 : 0}
                    step={metric === 'latency' ? 50 : 1}
                    className="w-full"
                  />
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit">
              Submit Experience
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}