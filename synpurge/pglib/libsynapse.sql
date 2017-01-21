[event_id_before::first]
SELECT event_id FROM events
    WHERE room_id = $1 AND origin_server_ts <= $2
    ORDER BY origin_server_ts DESC
    LIMIT 1

[resolve_room_alias::first]
SELECT room_id FROM room_aliases WHERE room_alias = $1

[room_aliases:const]
SELECT room_id, array_agg(room_alias) aliases
    FROM room_aliases
    GROUP BY room_id;

[public_room_aliases:const]
SELECT room_id, array_agg(room_alias) aliases
    FROM room_aliases
    WHERE room_id IN (SELECT room_id FROM rooms WHERE is_public = TRUE)
    GROUP BY room_id;

[get_room_info::first]
SELECT
    r.room_id AS room_id,
    r.is_public AS is_public,
    r.creator AS creator,
    array_agg(a.room_alias) AS aliases,
    (SELECT content FROM events
        WHERE room_id = r.room_id AND type = 'm.room.topic'
        ORDER BY origin_server_ts DESC LIMIT 1)::json->>'topic' AS topic,
    (SELECT content FROM events
        WHERE room_id = r.room_id AND type = 'm.room.name'
        ORDER BY origin_server_ts DESC LIMIT 1)::json->>'name' AS name
FROM rooms r,
     room_aliases a
WHERE r.room_id = $1
  AND r.room_id = a.room_id
GROUP BY
    r.room_id;

[table_indexes]
SELECT 
    idx.relname AS index, 
	pg_get_indexdef(idx.oid)||';' AS definition, 
	ind.indisclustered AS clustered 
FROM  pg_index ind
    JOIN pg_class idx ON idx.oid = ind.indexrelid
    JOIN pg_class tbl ON tbl.oid = ind.indrelid
    LEFT JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
WHERE tbl.relname = $1
    AND ind.indisvalid
    AND ind.indisready

