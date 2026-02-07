'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Star, ThumbsUp, ThumbsDown, CheckCircle, Clock, Zap, Shield } from 'lucide-react';
import { Experience } from '@/lib/types';

interface ExperienceCardProps {
  experience: Experience;
}

export function ExperienceCard({ experience }: ExperienceCardProps) {
  const [helpful, setHelpful] = useState<'helpful' | 'unhelpful' | null>(null);

  const handleHelpful = (type: 'helpful' | 'unhelpful') => {
    setHelpful(type);
    // In real app, this would make an API call
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
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

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarImage src={experience.author.avatar} />
              <AvatarFallback>{experience.author.name[0]}</AvatarFallback>
            </Avatar>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-medium">{experience.author.name}</h4>
                {experience.verified && (
                  <CheckCircle className="h-4 w-4 text-blue-500" />
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {formatDate(experience.createdAt)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`h-4 w-4 ${
                  i < experience.rating
                    ? 'fill-yellow-400 text-yellow-400'
                    : 'text-gray-300'
                }`}
              />
            ))}
          </div>
        </div>
        
        <div>
          <h3 className="font-semibold text-lg mb-1">{experience.title}</h3>
          <p className="text-muted-foreground leading-relaxed">
            {experience.content}
          </p>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Structured Metrics */}
        <div>
          <h4 className="text-sm font-medium mb-2">Performance Metrics</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(experience.metrics).map(([metric, value]) => (
              <div key={metric} className="flex items-center gap-2">
                <MetricIcon metric={metric} />
                <div>
                  <p className="text-xs text-muted-foreground">
                    {getMetricLabel(metric)}
                  </p>
                  <p className="font-medium text-sm">
                    {metric === 'latency' ? `${value}ms` : `${value}%`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <Separator />

        {/* Tags and Metadata */}
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">
            {experience.useCase}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {experience.buyerType}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {experience.workloadSize} workload
          </Badge>
        </div>

        <Separator />

        {/* Helpful buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Was this helpful?</span>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleHelpful('helpful')}
                className={`gap-1 ${
                  helpful === 'helpful' ? 'text-green-600' : 'text-muted-foreground'
                }`}
              >
                <ThumbsUp className="h-4 w-4" />
                <span className="text-xs">
                  {experience.helpful + (helpful === 'helpful' ? 1 : 0)}
                </span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleHelpful('unhelpful')}
                className={`gap-1 ${
                  helpful === 'unhelpful' ? 'text-red-600' : 'text-muted-foreground'
                }`}
              >
                <ThumbsDown className="h-4 w-4" />
                <span className="text-xs">
                  {experience.unhelpful + (helpful === 'unhelpful' ? 1 : 0)}
                </span>
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}