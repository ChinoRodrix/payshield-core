"""
fake_payment_api/main.py
========================

This module contains a small fake payment processor implemented with
FastAPI.  It exposes a RESTful API for accepting and recording payment
requests, as well as retrieving stored transactions.  The intent of
this service is to provide a playground for learning about
payment flows, API design and basic persistence; it **does not**
perform any real payment processing.

Endpoints
---------

```
POST  /pay              -- process a payment request
GET   /transactions     -- list all transactions
GET   /transactions/{id}-- fetch a single transaction by identifier
GET   /health           -- simple health check
```

This service stores transactions in MongoDB when the environment
variable ``MONGO_URL`` is set.  If a database is not available the
server falls back to keeping data in memory for the life of the
process.  Responses include a unique transaction identifier and a
status to indicate whether the payment was "approved" or "declined".

Usage
-----

You can run this API locally using ``uvicorn``:

```
uvicorn fake_payment_api.main:app --reload
```

By default the service listens on ``http://127.0.0.1:8000``.  You can
interact with it using any HTTP client (e.g. ``curl``, ``requests`` or
Postman).  When running locally you may want to set
``MONGO_URL`` to point at a running MongoDB instance if you want
persistent storage.

The API is documented with OpenAPI; after starting the service you
can browse the automatically generated documentation at
``/docs``.
"""

from __future__ import annotations

import os
import logging
import random
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, validator

try:
    # Attempt to import the motor async driver for MongoDB.  If this
    # import fails the service will operate with an in‑memory store
    import motor.motor_asyncio  # type: ignore
    _MOTOR_AVAILABLE = True
except ImportError:
    _MOTOR_AVAILABLE = False


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def luhn_checksum(card_number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm.

    This function returns True if the supplied card number satisfies
    the Luhn check, otherwise False.  It ignores non‑digit characters.

    Parameters
    ----------
    card_number: str
        The card number string to validate.

    Returns
    -------
    bool
        True if the card number passes the Luhn check.
    """
    digits = [int(c) for c in card_number if c.isdigit()]
    if not digits:
        return False
    checksum = 0
    # double every second digit from the right
    doubled = [d * 2 if (len(digits) - i) % 2 == 0 else d for i, d in enumerate(digits)]
    for d in doubled:
        # subtract 9 from numbers over 9 (equivalent to adding the digits)
        checksum += d - 9 if d > 9 else d
    return checksum % 10 == 0


class CardDetails(BaseModel):
    number: str = Field(..., description="Credit card number")
    expiry_month: int = Field(..., ge=1, le=12, description="Expiry month (1‑12)")
    expiry_year: int = Field(..., ge=datetime.utcnow().year, description="Expiry year (>= current year)")
    cvv: str = Field(..., min_length=3, max_length=4, description="Card security code (3 or 4 digits)")

    @validator("number")
    def validate_number(cls, v: str) -> str:
        digits = ''.join(filter(str.isdigit, v))
        if not luhn_checksum(digits):
            raise ValueError("Invalid card number (failed Luhn check)")
        return digits

    @validator("cvv")
    def validate_cvv(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("CVV must be numeric")
        return v


class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to charge (greater than zero)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code (e.g. USD)")
    description: Optional[str] = Field(None, description="Payment description")
    card: CardDetails

    @validator("currency")
    def uppercase_currency(cls, v: str) -> str:
        return v.upper()


class PaymentResponse(BaseModel):
    id: str
    status: str
    message: str
    amount: float
    currency: str
    created_at: datetime


class Transaction(PaymentResponse, PaymentRequest):
    """Pydantic model combining request and response data for storage."""
    pass


class InMemoryStore:
    """Simple in‑memory storage for transactions.

    This class mimics a minimal subset of the Motor collection API used
    below; it provides asynchronous `insert_one` and `find` methods.
    """

    def __init__(self) -> None:
        self._storage: List[Transaction] = []

    async def insert_one(self, txn: dict) -> dict:
        self._storage.append(Transaction(**txn))
        return {"inserted_id": txn["id"]}

    async def find(self, query: dict | None = None) -> List[Transaction]:
        if not query:
            return list(self._storage)
        # support lookup by id
        if "id" in query:
            return [t for t in self._storage if t.id == query["id"]]
        return []


async def get_database_collection() -> any:
    """Return a MongoDB collection or an in‑memory store.

    If the environment variable ``MONGO_URL`` is defined and motor
    (asynchronous MongoDB driver) is available, this function will
    return a Motor collection connected to the ``payments`` database and
    ``transactions`` collection.  Otherwise an instance of
    :class:`InMemoryStore` is returned.
    """
    mongo_url = os.getenv("MONGO_URL")
    if mongo_url and _MOTOR_AVAILABLE:
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
        db = client.get_default_database() if client.get_default_database() else client["payments"]
        return db["transactions"]
    logger.warning(
        "Using in‑memory store; set MONGO_URL and install motor to persist transactions"
    )
    return InMemoryStore()


app = FastAPI(title="Fake Payment API", version="1.0.0")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database collection on startup."""
    app.state.collection = await get_database_collection()
    logger.info("Payment API started; using %s", type(app.state.collection).__name__)


@app.get("/health", response_model=dict)
async def health_check() -> dict:
    """Return a simple health status.

    This endpoint can be used by monitoring systems to verify that
    the service is responsive.
    """
    return {"status": "ok"}


@app.post(
    "/pay",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentResponse,
    summary="Process a payment request",
    response_description="Payment processing result",
)
async def process_payment(payment: PaymentRequest) -> PaymentResponse:
    """Process a payment request and persist the transaction.

    This endpoint simulates a payment by performing a basic Luhn
    validation on the card number and returning an approved/declined
    status based on a deterministic but pseudo‑random rule.

    Transactions are stored in MongoDB when available or kept in
    memory otherwise.  Each transaction receives a unique
    identifier.
    """
    # Determine approval status: for demonstration we approve if
    # the sum of all digits modulo 2 is 0 (even), otherwise decline.
    digits = [int(c) for c in payment.card.number if c.isdigit()]
    approved = sum(digits) % 2 == 0

    txn_id = str(uuid.uuid4())
    created = datetime.utcnow()
    status_str = "approved" if approved else "declined"
    message = (
        "Payment approved" if approved else "Payment declined by issuer"
    )
    response_data: PaymentResponse = PaymentResponse(
        id=txn_id,
        status=status_str,
        message=message,
        amount=payment.amount,
        currency=payment.currency,
        created_at=created,
    )
    # Persist transaction data
    txn_record = response_data.dict()
    txn_record.update(payment.dict())
    collection = app.state.collection
    await collection.insert_one(txn_record)
    logger.info(
        "Processed payment: id=%s status=%s amount=%s%s",
        txn_id,
        status_str,
        payment.amount,
        payment.currency,
    )
    return response_data


@app.get(
    "/transactions",
    response_model=List[Transaction],
    summary="List all transactions",
    response_description="List of all stored transactions",
)
async def list_transactions() -> List[Transaction]:
    """Return a list of all stored transactions."""
    collection = app.state.collection
    results = await collection.find({})
    # When using motor this returns an async cursor; convert to a list
    if not isinstance(results, list):
        results = [Transaction(**doc) async for doc in results]
    return results


@app.get(
    "/transactions/{transaction_id}",
    response_model=Transaction,
    responses={404: {"description": "Transaction not found"}},
    summary="Get a single transaction",
    response_description="Transaction details",
)
async def get_transaction(transaction_id: str) -> Transaction:
    """Retrieve a single transaction by its identifier."""
    collection = app.state.collection
    results = await collection.find({"id": transaction_id})
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found",
        )
    # When using motor results is a cursor; convert to list
    if not isinstance(results, list):
        results = [Transaction(**doc) async for doc in results]
    return results[0]