'use client';

import Link from 'next/link';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Star, MapPin } from 'lucide-react';
import { Skill } from '@/lib/types';

interface SkillCardProps {
  skill: Skill;
}

export function SkillCard({ skill }: SkillCardProps) {
  return (
    <Link href={`/skills/${skill.slug}`}>
      <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="font-semibold text-lg mb-1 line-clamp-1">
                {skill.name}
              </h3>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {skill.description}
              </p>
            </div>
            <Badge variant="secondary" className="ml-2">
              {skill.integrationType}
            </Badge>
          </div>
        </CardHeader>
        
        <CardContent className="pb-3">
          <div className="flex items-center gap-2 mb-3">
            <Avatar className="h-6 w-6">
              <AvatarImage src={skill.seller.avatar} />
              <AvatarFallback>{skill.seller.name[0]}</AvatarFallback>
            </Avatar>
            <span className="text-sm text-muted-foreground">
              {skill.seller.name}
            </span>
            <div className="flex items-center gap-1 ml-auto">
              <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
              <span className="text-sm font-medium">
                {skill.rating.toFixed(1)}
              </span>
              <span className="text-sm text-muted-foreground">
                ({skill.reviewCount})
              </span>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-1 mb-3">
            {skill.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            {skill.tags.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{skill.tags.length - 3}
              </Badge>
            )}
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <span className="text-2xl font-bold">
                {skill.price}
              </span>
              <span className="text-sm text-muted-foreground">
                {skill.currency}
              </span>
            </div>
            <Badge variant="outline" className="text-xs">
              {skill.category}
            </Badge>
          </div>
        </CardContent>
        
        <CardFooter className="pt-0">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span>API Available</span>
          </div>
        </CardFooter>
      </Card>
    </Link>
  );
}