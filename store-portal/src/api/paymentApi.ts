import { apiClient } from './client'

export type PaymentStatus = {
  connected: boolean // a Stripe account exists for this store
  charges_enabled: boolean // store can accept online payment
  details_submitted: boolean // store finished the onboarding form
  // Commission on the pre-tax subtotal, by the channel the order came in on.
  fee_app_bps: number
  fee_phone_bps: number
  monthly_fee: string // flat fee on the monthly bill; "0.00" = none
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
