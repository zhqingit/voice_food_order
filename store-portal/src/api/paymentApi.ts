import { apiClient } from './client'

export type PaymentStatus = {
  connected: boolean // a Stripe account exists for this store
  charges_enabled: boolean // store can accept online payment
  details_submitted: boolean // store finished the onboarding form
  fee_bps: number // commission applied to this store's orders
}

export type ConnectResponse = {
  url: string // Stripe-hosted onboarding URL
  account_id: string
}

export async function getPaymentStatus(): Promise<PaymentStatus> {
  const res = await apiClient.get('/store/payments/status')
  return res.data as PaymentStatus
}

export async function connectPayments(returnUrl: string, refreshUrl: string): Promise<ConnectResponse> {
  const res = await apiClient.post('/store/payments/connect', {
    return_url: returnUrl,
    refresh_url: refreshUrl,
  })
  return res.data as ConnectResponse
}
