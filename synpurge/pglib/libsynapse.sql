[event_id_before::first]
SELECT event_id FROM events
    WHERE room_id = $1 AND origin_server_ts <= $2
    ORDER BY origin_server_ts DESC
    LIMIT 1
