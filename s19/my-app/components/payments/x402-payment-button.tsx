'use client'

import React, { useState, useCallback } from 'react'
import { useAccount, useSignMessage, useSwitchChain, useChainId } from 'wagmi'
import { base, baseSepolia } from 'wagmi/chains'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Loader2, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react'
import { X402PaymentRequirements, SUPPORTED_NETWORKS } from '@/lib/x402'

interface X402PaymentButtonProps {
  skillId: string
  skillName: string
  requirements?: X402PaymentRequirements
  onPaymentComplete?: (licenseKey: string) => void
  onPaymentError?: (error: string) => void
  className?: string
}

type PaymentStatus = 'idle' | 'loading' | 'verifying' | 'success' | 'error'

export function X402PaymentButton({
  skillId,
  skillName,
  requirements,
  onPaymentComplete,
  onPaymentError,
  className
}: X402PaymentButtonProps) {
  const { address, isConnected } = useAccount()
  const { signMessageAsync } = useSignMessage()
  const { switchChainAsync } = useSwitchChain()
  const chainId = useChainId()

  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [licenseKey, setLicenseKey] = useState<string | null>(null)
  const [txHash, setTxHash] = useState<string | null>(null)

  const getRequirements = useCallback(async (): Promise<X402PaymentRequirements> => {
    if (requirements) {
      return requirements
    }

    const response = await fetch(`/api/payments/x402/requirements?skillId=${skillId}`)
    if (!response.ok) {
      throw new Error('Failed to fetch payment requirements')
    }

    const data = await response.json()
    return data.requirements
  }, [skillId, requirements])

  const createPayment = useCallback(async (reqs: X402PaymentRequirements) => {
    // Check if we're on the correct network
    const targetNetwork = SUPPORTED_NETWORKS[reqs.network as keyof typeof SUPPORTED_NETWORKS]
    if (chainId !== targetNetwork.chainId) {
      try {
        await switchChainAsync({ 
          chainId: targetNetwork.chainId 
        })
      } catch (error) {
        throw new Error(`Please switch to ${targetNetwork.name} to continue`)
      }
    }

    // Create payment with x402
    const response = await fetch('/api/payments/x402/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        skillId,
        requirements: reqs
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Failed to create payment')
    }

    return response.json()
  }, [skillId, chainId, switchChainAsync])

  const verifyPayment = useCallback(async (paymentId: string, txHash: string) => {
    const response = await fetch('/api/payments/x402/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        skillId,
        paymentPayload: {
          paymentId,
          transactionHash: txHash,
          userId: address
        }
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Payment verification failed')
    }

    return response.json()
  }, [skillId, address])

  const handlePayment = useCallback(async () => {
    if (!isConnected || !address) {
      setError('Please connect your wallet first')
      return
    }

    setPaymentStatus('loading')
    setError(null)

    try {
      // Get payment requirements
      const reqs = await getRequirements()

    // Create payment
    setPaymentStatus('loading')
    const paymentData = await createPayment(reqs)

    // Sign message if required
    if (paymentData.messageToSign) {
      await signMessageAsync({ message: paymentData.messageToSign })
    }

    setTxHash(paymentData.transactionHash || '')
    setPaymentStatus('verifying')

    // Verify payment
    const verification = await verifyPayment(paymentData.paymentId, paymentData.transactionHash || '')

      setPaymentStatus('success')
      setLicenseKey(verification.licenseKey)
      onPaymentComplete?.(verification.licenseKey)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Payment failed'
      setError(errorMessage)
      setPaymentStatus('error')
      onPaymentError?.(errorMessage)
    }
  }, [isConnected, address, getRequirements, createPayment, signMessageAsync, verifyPayment, onPaymentComplete, onPaymentError])

  const getNetworkExplorerUrl = (network: string, hash: string) => {
    const config = SUPPORTED_NETWORKS[network as keyof typeof SUPPORTED_NETWORKS]
    return config?.blockExplorerUrls[0] ? `${config.blockExplorerUrls[0]}/tx/${hash}` : null
  }

  if (paymentStatus === 'success' && licenseKey) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            Payment Successful!
          </CardTitle>
          <CardDescription>
            You now have access to {skillName}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">License Key:</label>
            <div className="mt-1 p-3 bg-gray-50 rounded-md font-mono text-sm">
              {licenseKey}
            </div>
          </div>
          {txHash && requirements && (
            <div>
              <label className="text-sm font-medium">Transaction:</label>
              <div className="mt-1">
                <a
                  href={getNetworkExplorerUrl(requirements.network, txHash)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  View on {requirements.network} explorer
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Pay with x402</CardTitle>
        <CardDescription>
          Secure crypto payment for {skillName}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {requirements && (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Amount:</span>
              <span className="font-mono">{requirements.amount} {requirements.currency}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Network:</span>
              <Badge variant="secondary">{requirements.network}</Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Recipient:</span>
              <span className="font-mono text-xs">
                {requirements.recipient.slice(0, 6)}...{requirements.recipient.slice(-4)}
              </span>
            </div>
          </div>
        )}

        {!isConnected && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Please connect your wallet to continue with payment
            </AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter>
        <Button 
          onClick={handlePayment}
          disabled={!isConnected || paymentStatus === 'loading' || paymentStatus === 'verifying'}
          className="w-full"
        >
          {paymentStatus === 'loading' && (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating Payment...
            </>
          )}
          {paymentStatus === 'verifying' && (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Verifying Payment...
            </>
          )}
          {paymentStatus === 'idle' && 'Pay with x402'}
          {paymentStatus === 'error' && 'Retry Payment'}
        </Button>
      </CardFooter>
    </Card>
  )
}