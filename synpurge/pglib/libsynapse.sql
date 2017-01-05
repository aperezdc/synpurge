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
