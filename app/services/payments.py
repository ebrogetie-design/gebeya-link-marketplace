"""
Payment integration boundary.

No payment is marked PAID from a Telegram button or browser redirect.
For production, implement the selected Ethiopian provider's server-to-server
initiation + signed webhook verification according to its current merchant docs.
"""
from dataclasses import dataclass


@dataclass
class PaymentInit:
    provider: str
    reference: str
    checkout_url: str


class PaymentProviderNotConfigured(RuntimeError):
    pass


class PaymentGateway:
    def __init__(self, settings):
        self.settings = settings

    def initiate(self, *, amount, currency, tx_ref, customer_email=None):
        if self.settings.payment_provider == "manual":
            raise PaymentProviderNotConfigured(
                "Online payments are disabled. Configure and verify a payment provider first."
            )
        if self.settings.payment_provider == "chapa":
            # Intentionally fail closed until merchant credentials, callback verification,
            # and provider-specific contract are implemented and tested.
            raise PaymentProviderNotConfigured(
                "Chapa adapter requires merchant credentials and verified webhook implementation."
            )
        raise PaymentProviderNotConfigured("Unsupported payment provider.")

    def verify_webhook(self, headers, raw_body):
        # Never trust a redirect/query parameter as proof of payment.
        raise PaymentProviderNotConfigured("Webhook verification is not configured.")
