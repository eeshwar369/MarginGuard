# Supported exports

All files are UTF-8 CSV (a UTF-8 BOM is accepted). Required column names are case-sensitive. Additional columns are ignored. IDs are strings. Empty refunds are represented by the header alone. Orders and costs must contain records. Amounts are non-negative INR decimal values, without currency symbols, thousands separators, exponent notation, or more than two decimal places. Discounts and costs below are **line totals**.

## orders.csv

```csv
line_id,order_id,date,sku,product_name,quantity,unit_price,discount,currency
L001,O001,2026-09-01,TEE-01,Studio Tee,2,899.00,150.00,INR
```

`line_id` uniquely identifies a line. Multiple lines can share an `order_id` but must have the same ISO date. Quantity is an integer from 1 to 9,999. Gross value = quantity × unit price. The line discount cannot exceed gross value. Only INR is supported.

## costs.csv

```csv
line_id,product_cost,shipping_cost
L001,690.00,63.00
```

Exactly one cost record must match every order line. Product and shipping costs are allocated totals for that line; they are not multiplied by quantity again. Missing cost allocations block analysis instead of implying zero cost.

## refunds.csv

```csv
refund_id,line_id,date,amount,recovered_cost
R001,L001,2026-09-03,500.00,200.00
```

Multiple partial refunds may reference a line, but refund IDs are unique. Total refunds cannot exceed the line's net sale; total recovered cost cannot exceed its original product cost. Refund date must not precede order date. Refunds affect the original order cohort month, including when the refund occurs later.

An identical repeated refund is quarantined and flagged for acknowledgement. A repeated refund ID with different values blocks analysis. Duplicate order or cost keys, orphan references, and contradictory dates block analysis. Export a corrected set to resolve errors; acknowledgement cannot bypass them.

## Contribution formula

`quantity × unit_price − discount − refunds − product_cost + recovered_cost − shipping_cost`

Fixed overhead, tax, payment fees, and marketing spend are not represented. This product calculates contribution margin under this contract, not complete net profit or cash flow.

## Limits and provenance

Each file is limited to 8 MB and 50,000 rows by default. Combined monetary magnitude must stay within the exact-integer safety bound. Each dataset stores source SHA-256 hashes, normalized records with CSV row numbers, validation issues, and a separate version hash. Normalized CSV exports exclude quarantined duplicates and neutralize spreadsheet formula prefixes. Cost corrections preserve the original file hashes and append an explicit correction record; the resulting data-version hash changes.
