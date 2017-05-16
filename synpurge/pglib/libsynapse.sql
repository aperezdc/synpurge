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

[application_services]
SELECT as_id 
FROM application_services_state

[rooms_by_application_service_id]
SELECT room_id 
FROM appservice_room_list
WHERE appservice_id = $1

[users_by_application_service_id]
SELECT name 
FROM users
WHERE appservice_id = $1

[events_by_application_service_id]
SELECT event_id 
FROM events
WHERE room_id IN (
    SELECT room_id 
    FROM appservice_room_list
    WHERE appservice_id = $1
)

[delete_tuples_from_table_by_id]
DELETE FROM $1 WHERE room_id = $2

[delete_tuples_from_table_by_as_id_linked_with_user_id]
DELETE FROM $1 
WHERE user_id IN (
    SELECT name FROM users
    WHERE appservice_id = $2 
)

[delete_tuples_from_table_by_as_id_linked_with_event_id]
DELETE FROM $1 
WHERE event_id IN (
    SELECT event_id 
    FROM events
    WHERE room_id IN (
        SELECT room_id 
        FROM appservice_room_list
        WHERE appservice_id = $2
    )
)

[delete_room_alias_server_by_as_id]
DELETE FROM room_alias_servers 
WHERE room_alias IN (
    SELECT room_alias
    FROM room_aliases
    WHERE room_id IN (
        SELECT room_id 
        FROM appservice_room_list
        WHERE appservice_id = $2
    )
)

[delete_state_group_edges_by_as_id]
DELETE FROM state_group_edges 
WHERE state_group IN (
    SELECT state_group
    FROM state_groups
    WHERE room_id IN (
        SELECT room_id 
        FROM appservice_room_list
        WHERE appservice_id = $2
    )
)

[delete_users_by_as_id]
DELETE FROM users 
WHERE appservice_id = $1

[delete_application_services_state_by_as_id]
DELETE FROM application_services_state 
WHERE as_id = $1

[delete_application_services_txns_by_as_id]
DELETE FROM application_services_txns 
WHERE as_id = $1

[delete_appservice_room_list_by_as_id]
DELETE FROM appservice_room_list 
WHERE appservice_id = $1
