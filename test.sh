URL_BASE=http://localhost:5000

test_create_user() {
  curl -s -X PUT "$URL_BASE/users/tristan"

  docker-compose -p dev-backend exec database \
    psql -U postgres -d gallery -c 'select * from "user"'
}

test_create_user
