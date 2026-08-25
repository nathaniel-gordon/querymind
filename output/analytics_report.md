# Analytics Report

## total revenue

```
Q: total revenue
SQL (offline-parser, 1 attempt(s)): SELECT SUM(quantity * unit_price) AS value FROM "order_items"
value     
----------
3817818.14
=> value = 3,817,818.14
```

## top 5 products by revenue

```
Q: top 5 products by revenue
SQL (offline-parser, 1 attempt(s)): SELECT "products"."name" AS name, SUM(quantity * unit_price) AS value FROM "order_items" JOIN "products" ON "order_items"."product_id" = "products"."product_id" GROUP BY "products"."name" ORDER BY value DESC LIMIT 5
name                       | value     
---------------------------+-----------
Laptop Pro 15              | 1495302.31
Standing Desk              | 522611.01 
4K Monitor                 | 423516.61 
Noise-Canceling Headphones | 335837.29 
Office Chair               | 319475.46 
=> 5 groups; top: Laptop Pro 15 (1,495,302.31); total 3,096,742.68
```

## revenue by country

```
Q: revenue by country
SQL (offline-parser, 1 attempt(s)): SELECT "customers"."country" AS country, SUM(quantity * unit_price) AS value FROM "order_items" JOIN "orders" ON "order_items"."order_id" = "orders"."order_id" JOIN "customers" ON "orders"."customer_id" = "customers"."customer_id" GROUP BY "customers"."country" ORDER BY value DESC LIMIT 50
country | value    
--------+----------
Germany | 579489.2 
Canada  | 570132.58
Brazil  | 501103.9 
Japan   | 482099.53
France  | 472390.12
India   | 448617.81
UK      | 400886.38
USA     | 363098.62
=> 8 groups; top: Germany (579,489.20); total 3,817,818.14
```

## how many customers per segment

```
Q: how many customers per segment
SQL (offline-parser, 1 attempt(s)): SELECT "customers"."segment" AS segment, COUNT(*) AS value FROM "customers" GROUP BY "customers"."segment" ORDER BY value DESC LIMIT 50
segment        | value
---------------+------
consumer       | 215  
corporate      | 104  
small business | 81   
=> 3 groups; top: consumer (215.00); total 400.00
```

## average revenue by channel

```
Q: average revenue by channel
SQL (offline-parser, 1 attempt(s)): SELECT "orders"."channel" AS channel, SUM(quantity * unit_price) AS value FROM "order_items" JOIN "orders" ON "order_items"."order_id" = "orders"."order_id" GROUP BY "orders"."channel" ORDER BY value DESC LIMIT 50
channel      | value     
-------------+-----------
web          | 1690118.1 
mobile app   | 1210681.12
retail store | 505302.24 
phone        | 411716.68 
=> 4 groups; top: web (1,690,118.10); total 3,817,818.14
```

## monthly revenue in 2024

```
Q: monthly revenue in 2024
SQL (offline-parser, 1 attempt(s)): SELECT strftime('%Y-%m', "orders"."order_date") AS month, SUM(quantity * unit_price) AS value FROM "order_items" JOIN "orders" ON "order_items"."order_id" = "orders"."order_id" WHERE strftime('%Y', "orders"."order_date") = '2024' GROUP BY strftime('%Y-%m', "orders"."order_date") ORDER BY month LIMIT 50
month   | value    
--------+----------
2024-01 | 221519.77
2024-02 | 156930.06
2024-03 | 138857.34
2024-04 | 162749.72
2024-05 | 222239.42
2024-06 | 163684.67
2024-07 | 180190.7 
2024-08 | 181123.0 
2024-09 | 171874.32
2024-10 | 171750.24
2024-11 | 180396.72
2024-12 | 155660.94
=> 12 groups; top: 2024-01 (221,519.77); total 2,106,976.90
```

## how many orders were cancelled

```
Q: how many orders were cancelled
SQL (offline-parser, 1 attempt(s)): SELECT COUNT(*) AS value FROM "orders" WHERE LOWER("orders"."status") = 'cancelled'
value
-----
222  
=> value = 222
```

## revenue in Germany

```
Q: revenue in Germany
SQL (offline-parser, 1 attempt(s)): SELECT SUM(quantity * unit_price) AS value FROM "order_items" JOIN "orders" ON "order_items"."order_id" = "orders"."order_id" JOIN "customers" ON "orders"."customer_id" = "customers"."customer_id" WHERE LOWER("customers"."country") = 'germany'
value   
--------
579489.2
=> value = 579,489.20
```
