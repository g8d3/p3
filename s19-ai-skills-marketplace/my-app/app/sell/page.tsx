'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowRight, ArrowLeft, CheckCircle, Upload, Code, Zap, Shield, Star } from 'lucide-react';
import { toast } from 'sonner';

interface SkillFormData {
  // Step 1: Basic Info
  name: string;
  description: string;
  category: string;
  tags: string[];
  integrationType: string;
  
  // Step 2: Technical Specs
  apiEndpoint: string;
  documentation: string;
  codeExamples: string;
  performanceMetrics: {
    accuracy: number;
    latency: number;
    reliability: number;
  };
  
  // Step 3: Pricing
  price: number;
  currency: string;
  pricingModel: string;
  trialAvailable: boolean;
  trialDays: number;
  
  // Step 4: Review
  agreedToTerms: boolean;
}

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
  { value: 'api', label: 'REST API' },
  { value: 'sdk', label: 'SDK/Library' },
  { value: 'plugin', label: 'Plugin/Extension' }
];

const popularTags = [
  'machine-learning', 'nlp', 'computer-vision', 'web-scraping',
  'data-analysis', 'automation', 'ai', 'python', 'javascript',
  'rest-api', 'real-time', 'batch-processing', 'cloud-native'
];

const pricingModels = [
  { value: 'one-time', label: 'One-time Purchase' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'usage-based', label: 'Usage-based' }
];

export default function SellPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<SkillFormData>({
    name: '',
    description: '',
    category: '',
    tags: [],
    integrationType: '',
    apiEndpoint: '',
    documentation: '',
    codeExamples: '',
    performanceMetrics: {
      accuracy: 50,
      latency: 500,
      reliability: 50
    },
    price: 0,
    currency: 'USD',
    pricingModel: 'one-time',
    trialAvailable: false,
    trialDays: 7,
    agreedToTerms: false
  });

  const totalSteps = 4;
  const progress = (currentStep / totalSteps) * 100;

  const updateFormData = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleTagToggle = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.includes(tag)
        ? prev.tags.filter(t => t !== tag)
        : [...prev.tags, tag]
    }));
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = () => {
    console.log('Submitting skill:', formData);
    toast.success('Skill submitted successfully!');
    // Reset form or redirect
  };

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return formData.name.trim() !== '' && 
               formData.description.trim() !== '' && 
               formData.category !== '' && 
               formData.integrationType !== '';
      case 2:
        return formData.apiEndpoint.trim() !== '' && 
               formData.documentation.trim() !== '';
      case 3:
        return formData.price > 0;
      case 4:
        return formData.agreedToTerms;
      default:
        return false;
    }
  };

  const StepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <Label htmlFor="name">Skill Name</Label>
              <Input
                id="name"
                placeholder="Enter a descriptive name for your AI skill"
                value={formData.name}
                onChange={(e) => updateFormData('name', e.target.value)}
              />
            </div>
            
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe what your AI skill does, its key features, and ideal use cases"
                value={formData.description}
                onChange={(e) => updateFormData('description', e.target.value)}
                rows={4}
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Category</Label>
                <Select
                  value={formData.category}
                  onValueChange={(value) => updateFormData('category', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label>Integration Type</Label>
                <Select
                  value={formData.integrationType}
                  onValueChange={(value) => updateFormData('integrationType', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select integration type" />
                  </SelectTrigger>
                  <SelectContent>
                    {integrationTypes.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label>Tags</Label>
              <p className="text-sm text-muted-foreground mb-2">
                Select relevant tags to help buyers find your skill
              </p>
              <div className="flex flex-wrap gap-2">
                {popularTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant={formData.tags.includes(tag) ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => handleTagToggle(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        );
        
      case 2:
        return (
          <div className="space-y-6">
            <div>
              <Label htmlFor="api-endpoint">API Endpoint</Label>
              <Input
                id="api-endpoint"
                placeholder="https://api.example.com/v1/skill"
                value={formData.apiEndpoint}
                onChange={(e) => updateFormData('apiEndpoint', e.target.value)}
              />
            </div>
            
            <div>
              <Label htmlFor="documentation">Documentation URL</Label>
              <Input
                id="documentation"
                placeholder="https://docs.example.com/skill"
                value={formData.documentation}
                onChange={(e) => updateFormData('documentation', e.target.value)}
              />
            </div>
            
            <div>
              <Label htmlFor="code-examples">Code Examples</Label>
              <Textarea
                id="code-examples"
                placeholder="Provide code examples in different languages to help users get started"
                value={formData.codeExamples}
                onChange={(e) => updateFormData('codeExamples', e.target.value)}
                rows={6}
              />
            </div>
            
            <div>
              <Label className="text-sm font-medium mb-4 block">Performance Metrics</Label>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Accuracy</Label>
                    <span className="text-sm text-muted-foreground">{formData.performanceMetrics.accuracy}%</span>
                  </div>
                  <Slider
                    value={[formData.performanceMetrics.accuracy]}
                    onValueChange={([value]) => updateFormData('performanceMetrics', {
                      ...formData.performanceMetrics,
                      accuracy: value
                    })}
                    max={100}
                    step={1}
                  />
                </div>
                
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Latency (ms)</Label>
                    <span className="text-sm text-muted-foreground">{formData.performanceMetrics.latency}ms</span>
                  </div>
                  <Slider
                    value={[formData.performanceMetrics.latency]}
                    onValueChange={([value]) => updateFormData('performanceMetrics', {
                      ...formData.performanceMetrics,
                      latency: value
                    })}
                    max={5000}
                    step={50}
                  />
                </div>
                
                <div>
                  <div className="flex justify-between mb-2">
                    <Label className="text-sm">Reliability</Label>
                    <span className="text-sm text-muted-foreground">{formData.performanceMetrics.reliability}%</span>
                  </div>
                  <Slider
                    value={[formData.performanceMetrics.reliability]}
                    onValueChange={([value]) => updateFormData('performanceMetrics', {
                      ...formData.performanceMetrics,
                      reliability: value
                    })}
                    max={100}
                    step={1}
                  />
                </div>
              </div>
            </div>
          </div>
        );
        
      case 3:
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="price">Price</Label>
                <Input
                  id="price"
                  type="number"
                  placeholder="49.99"
                  value={formData.price || ''}
                  onChange={(e) => updateFormData('price', Number(e.target.value))}
                />
              </div>
              
              <div>
                <Label>Currency</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(value) => updateFormData('currency', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="ETH">ETH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label>Pricing Model</Label>
              <Select
                value={formData.pricingModel}
                onValueChange={(value) => updateFormData('pricingModel', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {pricingModels.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="trial-available"
                  checked={formData.trialAvailable}
                  onCheckedChange={(checked) => updateFormData('trialAvailable', checked)}
                />
                <Label htmlFor="trial-available">Offer free trial</Label>
              </div>
              
              {formData.trialAvailable && (
                <div>
                  <Label htmlFor="trial-days">Trial Days</Label>
                  <Input
                    id="trial-days"
                    type="number"
                    placeholder="7"
                    value={formData.trialDays}
                    onChange={(e) => updateFormData('trialDays', Number(e.target.value))}
                  />
                </div>
              )}
            </div>
            
            <Alert>
              <Zap className="h-4 w-4" />
              <AlertDescription>
                You'll earn 85% of each sale. Platform fees cover payment processing, hosting, and support.
              </AlertDescription>
            </Alert>
          </div>
        );
        
      case 4:
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Review Your Skill</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm text-muted-foreground">Name</Label>
                    <p className="font-medium">{formData.name}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Category</Label>
                    <p className="font-medium">{formData.category}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Price</Label>
                    <p className="font-medium">${formData.price} {formData.currency}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Integration</Label>
                    <p className="font-medium">{formData.integrationType}</p>
                  </div>
                </div>
                
                <div>
                  <Label className="text-sm text-muted-foreground">Description</Label>
                  <p className="font-medium">{formData.description}</p>
                </div>
                
                <div>
                  <Label className="text-sm text-muted-foreground">Tags</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {formData.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="terms"
                  checked={formData.agreedToTerms}
                  onCheckedChange={(checked) => updateFormData('agreedToTerms', checked)}
                />
                <Label htmlFor="terms" className="text-sm">
                  I agree to the Terms of Service and understand that my skill will be reviewed before publication.
                </Label>
              </div>
              
              <Alert>
                <Shield className="h-4 w-4" />
                <AlertDescription>
                  Your skill will undergo a technical review to ensure it meets our quality standards. This typically takes 2-3 business days.
                </AlertDescription>
              </Alert>
            </div>
          </div>
        );
        
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold">List Your AI Skill</h1>
          <p className="text-muted-foreground">
            Share your AI capabilities with thousands of developers and businesses
          </p>
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Step {currentStep} of {totalSteps}</span>
            <span>{Math.round(progress)}% Complete</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>
              {currentStep === 1 && 'Basic Information'}
              {currentStep === 2 && 'Technical Specifications'}
              {currentStep === 3 && 'Pricing'}
              {currentStep === 4 && 'Review & Submit'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <StepContent />
            
            <Separator className="my-6" />
            
            {/* Navigation */}
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={handlePrevious}
                disabled={currentStep === 1}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Previous
              </Button>
              
              {currentStep === totalSteps ? (
                <Button
                  onClick={handleSubmit}
                  disabled={!validateStep(currentStep)}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Submit Skill
                </Button>
              ) : (
                <Button
                  onClick={handleNext}
                  disabled={!validateStep(currentStep)}
                >
                  Next
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}