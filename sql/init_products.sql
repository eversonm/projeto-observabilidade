INSERT INTO products (name, description, link, created_at, updated_at)
SELECT
    'Produto ' || md5(random()::text || clock_timestamp()::text || series::text),
    'Descrição sintética de catálogo para demonstração de carga. SKU ' || series,
    'https://example.com/products/' || series,
    now(),
    now()
FROM generate_series(1, :row_count) AS series;
