UPDATE historial_usuario
SET datos_antes = JSON_REMOVE(datos_antes, '$.password_hash', '$.pin_hash', '$.session_token')
WHERE datos_antes IS NOT NULL AND JSON_VALID(datos_antes);

UPDATE historial_usuario
SET datos_despues = JSON_REMOVE(datos_despues, '$.password_hash', '$.pin_hash', '$.session_token')
WHERE datos_despues IS NOT NULL AND JSON_VALID(datos_despues);
