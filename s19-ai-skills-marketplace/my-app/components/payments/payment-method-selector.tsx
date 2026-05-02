'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { CreditCard, Wallet, Shield, CheckCircle, AlertCircle } from 'lucide-react';
import { PaymentMethod } from '@/lib/types';

interface PaymentMethodSelectorProps {
  amount: number;
  currency: string;
  onPaymentMethodChange: (method: PaymentMethod) => void;
  selectedMethod?: PaymentMethod;
}

export function PaymentMethodSelector({ 
  amount, 
  currency, 
  onPaymentMethodChange, 
  selectedMethod 
}: PaymentMethodSelectorProps) {
  const [activeTab, setActiveTab] = useState(selectedMethod?.type || 'polar');
  const [polarData, setPolarData] = useState({
    email: '',
    cardNumber: '',
    expiry: '',
    cvv: '',
    name: ''
  });
  
  const [x402Data, setX402Data] = useState({
    wallet: '',
    network: 'ethereum'
  });
  
  const [erc8004Data, setErc8004Data] = useState({
    wallet: '',
    network: 'ethereum',
    escrowTerms: false
  });

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    const method: PaymentMethod = { type: tab as any };
    onPaymentMethodChange(method);
  };

  const handlePolarSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onPaymentMethodChange({
      type: 'polar',
      cardLast4: polarData.cardNumber.slice(-4)
    });
  };

  const handleX402Submit = (e: React.FormEvent) => {
    e.preventDefault();
    onPaymentMethodChange({
      type: 'x402',
      address: x402Data.wallet
    });
  };

  const handleERC8004Submit = (e: React.FormEvent) => {
    e.preventDefault();
    onPaymentMethodChange({
      type: 'erc8004',
      address: erc8004Data.wallet
    });
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wallet className="h-5 w-5" />
          Select Payment Method
        </CardTitle>
        <p className="text-muted-foreground">
          Choose how you'd like to pay {amount} {currency}
        </p>
      </CardHeader>
      
      <CardContent>
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="polar" className="flex items-center gap-2">
              <CreditCard className="h-4 w-4" />
              Polar
            </TabsTrigger>
            <TabsTrigger value="x402" className="flex items-center gap-2">
              <Wallet className="h-4 w-4" />
              x402
            </TabsTrigger>
            <TabsTrigger value="erc8004" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              ERC-8004
            </TabsTrigger>
          </TabsList>

          <TabsContent value="polar" className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900">Pay with Card/Fiat</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    Secure payment via Polar. Accepts credit/debit cards and bank transfers.
                  </p>
                </div>
              </div>
            </div>
            
            <form onSubmit={handlePolarSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Label htmlFor="polar-email">Email</Label>
                  <Input
                    id="polar-email"
                    type="email"
                    placeholder="your@email.com"
                    value={polarData.email}
                    onChange={(e) => setPolarData(prev => ({ ...prev, email: e.target.value }))}
                    required
                  />
                </div>
                
                <div className="md:col-span-2">
                  <Label htmlFor="polar-name">Cardholder Name</Label>
                  <Input
                    id="polar-name"
                    placeholder="John Doe"
                    value={polarData.name}
                    onChange={(e) => setPolarData(prev => ({ ...prev, name: e.target.value }))}
                    required
                  />
                </div>
                
                <div className="md:col-span-2">
                  <Label htmlFor="polar-card">Card Number</Label>
                  <Input
                    id="polar-card"
                    placeholder="1234 5678 9012 3456"
                    value={polarData.cardNumber}
                    onChange={(e) => setPolarData(prev => ({ ...prev, cardNumber: e.target.value }))}
                    maxLength={19}
                    required
                  />
                </div>
                
                <div>
                  <Label htmlFor="polar-expiry">Expiry</Label>
                  <Input
                    id="polar-expiry"
                    placeholder="MM/YY"
                    value={polarData.expiry}
                    onChange={(e) => setPolarData(prev => ({ ...prev, expiry: e.target.value }))}
                    maxLength={5}
                    required
                  />
                </div>
                
                <div>
                  <Label htmlFor="polar-cvv">CVV</Label>
                  <Input
                    id="polar-cvv"
                    placeholder="123"
                    value={polarData.cvv}
                    onChange={(e) => setPolarData(prev => ({ ...prev, cvv: e.target.value }))}
                    maxLength={4}
                    required
                  />
                </div>
              </div>
              
              <Button type="submit" className="w-full">
                Pay {amount} {currency} with Polar
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="x402" className="space-y-4">
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="flex items-start gap-2">
                <Wallet className="h-5 w-5 text-purple-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-purple-900">Pay with Crypto</h4>
                  <p className="text-sm text-purple-700 mt-1">
                    Direct cryptocurrency payment via x402 protocol. Lower fees, instant settlement.
                  </p>
                </div>
              </div>
            </div>
            
            <form onSubmit={handleX402Submit} className="space-y-4">
              <div>
                <Label htmlFor="x402-network">Network</Label>
                <Select
                  value={x402Data.network}
                  onValueChange={(value) => setX402Data(prev => ({ ...prev, network: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ethereum">Ethereum</SelectItem>
                    <SelectItem value="polygon">Polygon</SelectItem>
                    <SelectItem value="arbitrum">Arbitrum</SelectItem>
                    <SelectItem value="optimism">Optimism</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="x402-wallet">Wallet Address</Label>
                <Input
                  id="x402-wallet"
                  placeholder="0x1234...5678"
                  value={x402Data.wallet}
                  onChange={(e) => setX402Data(prev => ({ ...prev, wallet: e.target.value }))}
                  required
                />
              </div>
              
              <div className="bg-muted p-3 rounded-lg">
                <p className="text-sm text-muted-foreground">
                  You will be prompted to sign the transaction in your wallet.
                </p>
              </div>
              
              <Button type="submit" className="w-full">
                Pay {amount} {currency} with x402
              </Button>
            </form>
          </TabsContent>

          <TabsContent value="erc8004" className="space-y-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="flex items-start gap-2">
                <Shield className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-green-900">Pay with Escrow</h4>
                  <p className="text-sm text-green-700 mt-1">
                    Protected payment via ERC-8004 escrow. Funds released only when you confirm delivery.
                  </p>
                </div>
              </div>
            </div>
            
            <form onSubmit={handleERC8004Submit} className="space-y-4">
              <div>
                <Label htmlFor="erc8004-network">Network</Label>
                <Select
                  value={erc8004Data.network}
                  onValueChange={(value) => setErc8004Data(prev => ({ ...prev, network: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ethereum">Ethereum</SelectItem>
                    <SelectItem value="polygon">Polygon</SelectItem>
                    <SelectItem value="arbitrum">Arbitrum</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="erc8004-wallet">Wallet Address</Label>
                <Input
                  id="erc8004-wallet"
                  placeholder="0x1234...5678"
                  value={erc8004Data.wallet}
                  onChange={(e) => setErc8004Data(prev => ({ ...prev, wallet: e.target.value }))}
                  required
                />
              </div>
              
              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium">Escrow Terms:</p>
                    <ul className="text-muted-foreground mt-1 space-y-1">
                      <li>• Funds locked in escrow contract</li>
                      <li>• Released upon your confirmation</li>
                      <li>• Dispute resolution available</li>
                      <li>• 2% escrow fee</li>
                    </ul>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="escrow-terms"
                    checked={erc8004Data.escrowTerms}
                    onChange={(e) => setErc8004Data(prev => ({ ...prev, escrowTerms: e.target.checked }))}
                    required
                  />
                  <Label htmlFor="escrow-terms" className="text-sm">
                    I agree to the escrow terms
                  </Label>
                </div>
              </div>
              
              <Button type="submit" className="w-full" disabled={!erc8004Data.escrowTerms}>
                Pay {amount} {currency} with ERC-8004 Escrow
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}