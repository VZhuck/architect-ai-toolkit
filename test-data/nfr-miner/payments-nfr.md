# Payments Platform - Non-Functional Notes

## Performance

Checkout must respond within 300 ms at p95 under 500 TPS.

The admin console should be fast.

## Availability

The payment API must be highly available.

Recovery time objective (RTO) for the payment API is 1 hour.

## Features

Users can export invoices to CSV.

## Constraints

All services must run on Azure in EU regions.

We assume peak load will not exceed 2,000 TPS during Black Friday.
