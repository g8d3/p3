'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { 
  BarChart, 
  TrendingUp, 
  Users, 
  DollarSign, 
  Star, 
  Eye, 
  Edit, 
  MoreHorizontal,
  Download,
  Calendar,
  Package,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

// Mock data
const mockSkills = [
  {
    id: '1',
    name: 'Advanced Sentiment Analysis',
    status: 'active',
    price: 49,
    currency: 'USD',
    sales: 124,
    revenue: 6076,
    rating: 4.8,
    views: 1523,
    createdAt: '2024-01-15'
  },
  {
    id: '2',
    name: 'AI Image Generator',
    status: 'active',
    price: 29,
    currency: 'USD',
    sales: 89,
    revenue: 2581,
    rating: 4.6,
    views: 892,
    createdAt: '2024-01-10'
  },
  {
    id: '3',
    name: 'Smart Data Automation',
    status: 'draft',
    price: 79,
    currency: 'USD',
    sales: 0,
    revenue: 0,
    rating: 0,
    views: 45,
    createdAt: '2024-01-20'
  }
];

const mockPurchases = [
  {
    id: '1',
    skillName: 'Advanced Sentiment Analysis',
    seller: 'AI Labs',
    price: 49,
    currency: 'USD',
    purchaseDate: '2024-01-25',
    status: 'active'
  },
  {
    id: '2',
    skillName: 'AI Image Generator',
    seller: 'Creative AI',
    price: 29,
    currency: 'USD',
    purchaseDate: '2024-01-22',
    status: 'active'
  },
  {
    id: '3',
    skillName: 'Text Classification API',
    seller: 'ML Solutions',
    price: 39,
    currency: 'USD',
    purchaseDate: '2024-01-18',
    status: 'expired'
  }
];

const mockStats = {
  totalRevenue: 8657,
  totalSales: 213,
  activeSkills: 2,
  averageRating: 4.7,
  monthlyGrowth: 23.5,
  weeklyViews: 1247
};

export default function DashboardPage() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'skills');

  const StatCard = ({ title, value, icon: Icon, change, changeType }: {
    title: string;
    value: string | number;
    icon: any;
    change?: number;
    changeType?: 'increase' | 'decrease';
  }) => (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {change !== undefined && (
              <div className={`flex items-center gap-1 text-sm ${
                changeType === 'increase' ? 'text-green-600' : 'text-red-600'
              }`}>
                {changeType === 'increase' ? (
                  <ArrowUpRight className="h-4 w-4" />
                ) : (
                  <ArrowDownRight className="h-4 w-4" />
                )}
                <span>{change}%</span>
              </div>
            )}
          </div>
          <div className="p-2 bg-primary/10 rounded-lg">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">Manage your skills and track performance</p>
          </div>
          <Button>
            <Package className="h-4 w-4 mr-2" />
            List New Skill
          </Button>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Revenue"
            value={`$${mockStats.totalRevenue.toLocaleString()}`}
            icon={DollarSign}
            change={mockStats.monthlyGrowth}
            changeType="increase"
          />
          <StatCard
            title="Total Sales"
            value={mockStats.totalSales}
            icon={Users}
            change={12.3}
            changeType="increase"
          />
          <StatCard
            title="Active Skills"
            value={mockStats.activeSkills}
            icon={Package}
          />
          <StatCard
            title="Average Rating"
            value={mockStats.averageRating.toFixed(1)}
            icon={Star}
          />
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="skills">My Skills</TabsTrigger>
            <TabsTrigger value="purchases">My Purchases</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="wallet">Wallet</TabsTrigger>
          </TabsList>

          {/* My Skills */}
          <TabsContent value="skills" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Your Skills</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Skill</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Sales</TableHead>
                      <TableHead>Revenue</TableHead>
                      <TableHead>Rating</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockSkills.map((skill) => (
                      <TableRow key={skill.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{skill.name}</p>
                            <p className="text-sm text-muted-foreground">
                              Created {skill.createdAt}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={skill.status === 'active' ? 'default' : 'secondary'}>
                            {skill.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          ${skill.price} {skill.currency}
                        </TableCell>
                        <TableCell>{skill.sales}</TableCell>
                        <TableCell>${skill.revenue.toLocaleString()}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                            <span>{skill.rating}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* My Purchases */}
          <TabsContent value="purchases" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Your Purchases</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Skill</TableHead>
                      <TableHead>Seller</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Purchase Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockPurchases.map((purchase) => (
                      <TableRow key={purchase.id}>
                        <TableCell className="font-medium">
                          {purchase.skillName}
                        </TableCell>
                        <TableCell>{purchase.seller}</TableCell>
                        <TableCell>
                          ${purchase.price} {purchase.currency}
                        </TableCell>
                        <TableCell>{purchase.purchaseDate}</TableCell>
                        <TableCell>
                          <Badge variant={purchase.status === 'active' ? 'default' : 'secondary'}>
                            {purchase.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Download className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics */}
          <TabsContent value="analytics" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Revenue Overview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">This Month</span>
                      <span className="font-medium">$2,341</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Last Month</span>
                      <span className="font-medium">$1,896</span>
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Growth</span>
                      <div className="flex items-center gap-1 text-green-600">
                        <ArrowUpRight className="h-4 w-4" />
                        <span>23.5%</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Top Performing Skills</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {mockSkills.slice(0, 3).map((skill, index) => (
                      <div key={skill.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                            <span className="text-sm font-medium">{index + 1}</span>
                          </div>
                          <div>
                            <p className="font-medium text-sm">{skill.name}</p>
                            <p className="text-xs text-muted-foreground">{skill.sales} sales</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-sm">${skill.revenue.toLocaleString()}</p>
                          <p className="text-xs text-muted-foreground">revenue</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Conversion Rate</span>
                      <span className="font-medium">12.4%</span>
                    </div>
                    <Progress value={12.4} className="h-2" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Customer Satisfaction</span>
                      <span className="font-medium">94.2%</span>
                    </div>
                    <Progress value={94.2} className="h-2" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Skill Utilization</span>
                      <span className="font-medium">78.6%</span>
                    </div>
                    <Progress value={78.6} className="h-2" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Wallet */}
          <TabsContent value="wallet" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Wallet Balance</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="text-center space-y-2">
                    <p className="text-4xl font-bold">$1,234.56</p>
                    <p className="text-muted-foreground">Available balance</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <Button className="w-full">
                      <CreditCard className="h-4 w-4 mr-2" />
                      Withdraw
                    </Button>
                    <Button variant="outline" className="w-full">
                      <Download className="h-4 w-4 mr-2" />
                      Transaction History
                    </Button>
                  </div>
                  
                  <Separator />
                  
                  <div className="space-y-4">
                    <h4 className="font-medium">Recent Transactions</h4>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">Sale - Advanced Sentiment Analysis</p>
                          <p className="text-xs text-muted-foreground">Jan 25, 2024</p>
                        </div>
                        <div className="text-green-600 font-medium">+$49.00</div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">Platform Fee</p>
                          <p className="text-xs text-muted-foreground">Jan 25, 2024</p>
                        </div>
                        <div className="text-red-600 font-medium">-$7.35</div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">Sale - AI Image Generator</p>
                          <p className="text-xs text-muted-foreground">Jan 22, 2024</p>
                        </div>
                        <div className="text-green-600 font-medium">+$29.00</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Payout Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Payment Method</p>
                    <div className="p-3 bg-muted rounded-lg">
                      <p className="text-sm">Bank Account ending in 1234</p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Payout Schedule</p>
                    <div className="p-3 bg-muted rounded-lg">
                      <p className="text-sm">Monthly (1st of each month)</p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Minimum Payout</p>
                    <div className="p-3 bg-muted rounded-lg">
                      <p className="text-sm">$50.00</p>
                    </div>
                  </div>
                  
                  <Button variant="outline" className="w-full">
                    Edit Settings
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}