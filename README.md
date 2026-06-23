# Fake Payment API

This repository contains a small **fake payment processor** built with
Python and FastAPI.  Its goal is to help you understand payment
workflows, RESTful API design and basic persistence without touching
any real money or integrating with actual payment providers.

## Features

* **Process payment requests**: POST to `/pay` with card details and
  transaction data; the service performs a basic Luhn check and
  pseudo‑randomly approves or declines the payment.
* **Store transactions**: all requests and responses are stored in
  MongoDB when available, or in an in‑memory list during development.
* **Retrieve transactions**: list all stored transactions or fetch a
  single one by its identifier.
* **Health check**: quickly verify that the API is running via `/health`.
* **OpenAPI documentation**: browse auto‑generated docs at `/docs` once
  the server is running.

## Prerequisites

* Python 3.10+
* Recommended: a running MongoDB instance for persistent storage
* The dependencies listed in `requirements.txt`

## Setup

Clone the repository and install the dependencies:

```sh
pip install -r requirements.txt
```

Optionally, create a `.env` file at the root of the project and
define `MONGO_URL` with your MongoDB connection string.  When
`MONGO_URL` is undefined, the API will store transactions in memory:

```
MONGO_URL=mongodb://localhost:27017/payments
```

## Running the API

Start the server using `uvicorn`:

```sh
uvicorn fake_payment_api.main:app --reload
```

The `--reload` flag enables hot reloading for development.  The
service will be available at `http://127.0.0.1:8000`.

Open the interactive API documentation at
`http://127.0.0.1:8000/docs` to explore the endpoints.

## Example Request

### Process a payment

```
POST /pay HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "amount": 49.99,
  "currency": "USD",
  "description": "Test order",
  "card": {
    "number": "4242 4242 4242 4242",
    "expiry_month": 12,
    "expiry_year": 2028,
    "cvv": "123"
  }
}
```

Sample response:

```
{
  "id": "b1a9292a-f2b1-4a8d-9d2c-3c98ab7107c5",
  "status": "approved",
  "message": "Payment approved",
  "amount": 49.99,
  "currency": "USD",
  "created_at": "2026-06-23T12:34:56.789Z"
}
```

## License

This code is provided under the MIT License.  See the `LICENSE` file
for details.