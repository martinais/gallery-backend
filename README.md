# gallery-backend

![tests](./test.png)

## API reference

### `POST /signin`

Enregistre un nouvel utilisateur.

```bash
curl "$BASE/signin" \
  --header 'Content-Type: application/json' \
  --request 'POST' \
  --data '{ "name": "alan", "email": "alan.turing@mail.uk" }'
```

### `POST /login`

Déclenche l'envoie d'un mail contenant le code d'authentification.

```bash
curl "$BASE/login" \
  --header 'Content-Type: application/json' \
  --request 'POST' \
  --data '{ "name": "alan" }'
```

### `POST /token`

Obtient un token d'authentification à partir du code reçu par mail.

```bash
curl "$BASE/token" \
  --header 'Content-Type: application/json' \
  --header 'Accept: application/json' \
  --request 'POST' \
  --data '{ "code": "..." }'
```

Réponse:
```json
{
  "access_token": "eyJ0oXA...SQ"
}
```

### `GET /users`

```bash
curl "$BASE/users" \
  --header 'Accept: application/json' \
  --header "Authorization: Bearer $TOKEN" \
  --request 'GET'
```

### `GET /albums`

```bash
curl "$BASE/albums" \
  --header 'Accept: application/json' \
  --header "Authorization: Bearer $TOKEN" \
  --request 'GET'
```

### `POST /albums`

```bash
curl "$BASE/albums" \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer $TOKEN" \
  --request 'POST' \
  --data '{"name": "..."}'
```

### `GET /albums/<slug>`

```bash
curl "$BASE/albums/$SLUG" \
  --header 'Accept: application/json' \
  --header "Authorization: Bearer $TOKEN" \
  --request 'GET'
```

### `DELETE /albums/<slug>`

```bash
curl "$BASE/albums/$SLUG" \
  --header "Authorization: Bearer $TOKEN" \
  --request 'DELETE'
```

### `GET /albums/<slug>/pics`

### `PATCH /albums/<slug>/pics`

### `GET /pic/<filehash>`

### `PUT /pic/<filehash>`

## Exemple

```
$ curl -i "$BASE/signin" \
  --header 'Content-Type: application/json' \
  --request 'POST' \
  --data '{ "name": "tristan", "email": "tristan@tic.sh" }'

HTTP/1.0 204 NO CONTENT
Content-Type: text/html; charset=utf-8
Server: Werkzeug/1.0.1 Python/3.9.4
Date: Thu, 29 Jul 2021 16:50:10 GMT

$ curl -i "$BASE/login" \
  --header 'Content-Type: application/json' \
  --request 'POST' \
  --data '{ "name": "tristan" }'

HTTP/1.0 204 NO CONTENT
Content-Type: text/html; charset=utf-8
Server: Werkzeug/1.0.1 Python/3.9.4
Date: Thu, 29 Jul 2021 16:53:24 GMT

$ docker-compose exec kvstore redis-cli -c KEYS '*' | tail -n 1

1) "737FDFDC"

$ export CODE='737FDFDC'

$ curl "$BASE/token" \
  --header 'Content-Type: application/json' \
  --header 'Accept: application/json' \
  --request 'POST' \
  --data "{ \"code\": \"$CODE\" }"

{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYyNzU3NzUwMCwianRpIjoiNmJkMzhkMjctZjU1My00YmUzLTg5NmEtMWQzZTRlZjE2YjBmIiwibmJmIjoxNjI3NTc3NTAwLCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoidGVzdCIsImV4cCI6MTYyNzU3ODQwMH0.jIbmLglFmwBYXu1s3CYq0QdlpUV50SkMJvDR04VYZr4"
}

$ export TOKEN='eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTYyNzU3NzUwMCwianRpIjoiNmJkMzhkMjctZjU1My00YmUzLTg5NmEtMWQzZTRlZjE2YjBmIiwibmJmIjoxNjI3NTc3NTAwLCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoidGVzdCIsImV4cCI6MTYyNzU3ODQwMH0.jIbmLglFmwBYXu1s3CYq0QdlpUV50SkMJvDR04VYZr4'

$ curl "$BASE/users" \
  --header 'Accept: application/json' \
  --header "Authorization: Bearer $TOKEN" \
  --request 'GET'

{
  "users": [
    "test",
    "tristan",
    "albert"
  ]
}
```
