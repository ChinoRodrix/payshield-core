# PayShield Core

## Overview

PayShield Core simulates the heart of a payment gateway. It exposes endpoints to authorize fake payments, simulate approval and decline scenarios and record transaction logs. The API is built with FastAPI and follows secure transaction flow patterns, making it ideal for practicing payment integration and exploring security concepts.

### Visão Geral

O PayShield Core simula o núcleo de um gateway de pagamentos. Ele expõe endpoints para autorizar pagamentos fictícios, simular aprovações e recusas e registrar logs de transação. A API é construída com FastAPI e segue padrões de fluxo transacional seguro, sendo ideal para treinar integração de pagamentos e explorar conceitos de segurança.

## Architecture / Arquitetura

```
[Client] --> [PayShield Core API] --> [Data Store (MongoDB / In‑Memory)]
     |                                   ^
     +----------- Swagger / Docs --------+
```

This simple flow shows a client sending a payment to the API which processes it and stores the result. The same API exposes auto‑generated Swagger documentation for quick exploration.

## API and Swagger Documentation

The service includes interactive OpenAPI docs at `/docs`. Major endpoints include:

- `POST /pay` – Process a payment request with card details and amount. Returns a status of `APPROVED` or `DECLINED`.
- `GET /transactions` – List all processed transactions with status, amount, and timestamps.
- `GET /transactions/{transaction_id}` – Retrieve a single transaction by its identifier.
- `GET /health` – Health check endpoint to verify the service is running.

### Exemplos

Uma chamada de exemplo ao endpoint `/pay`:

```
POST /pay
{
  "card_number": "4111111111111111",
  "expiry_month": "12",
  "expiry_year": "2026",
  "cvv": "123",
  "amount": 100.0
}
Response:
{
  "status": "APPROVED",
  "transaction_id": "abc123"
}
```

## Use Cases / Casos de Uso

- **Integration testing:** simulate card payments and observe approval or decline scenarios without touching real payment networks.
- **Error handling:** validate how invalid inputs are handled (ex: falha na verificação de Luhn para números de cartão inválidos).
- **Fraud experimentation:** chain calls to the PayShield Risk service (motor antifraude) to calculate risk scores before final approval.
- **Education:** entender conceitos como autorização, captura, estornos, logs e idempotência.

## Roadmap

- Integrate PayShield Risk for real-time fraud scoring.
- Add authentication (JWT) and rate limiting.
- Support additional payment flows (capture, refund, reversal).
- Persist transactions in PostgreSQL in addition to MongoDB.

## Screenshots / Doc Preview

Como a API utiliza FastAPI, a documentação interativa está disponível em `/docs` quando a aplicação está em execução. Abaixo um trecho ilustrativo do Swagger gerado automaticamente:

```
# Example excerpt of /docs (Swagger UI)
```

## Disclaimer

This is an educational project. The implementation uses only simulated data and does not handle real cardholder information or connect to any payment processors.
