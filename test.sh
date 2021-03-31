#!/bin/bash

URL_BASE=http://localhost:5000

db_query() {
  docker-compose -p dev-backend exec database \
    psql --csv -U postgres -d gallery -c "$1"
}

be_query() {
  curl -sw "%{http_code}" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    -X $1 "$URL_BASE/$2" -d $3
}

test_create_user() {
  make reset &> /dev/null
  first_code=$(
    be_query 'POST' 'users' '{"name":"tristan","email":"tristan@tic.sh"}'
  )
  second_code=$(
    be_query 'POST' 'users' '{"name":"tristan","email":"tristan@tic.sh"}'
  )
  insert=$(\
    db_query 'select * from public.user' | wc -l\
  )
  if [[ $insert -eq 2 && $first_code -eq 204 && $second_code -eq 409 ]]; then
    echo 'OK test_create_user'
  else
    echo 'FAIL test_create_user'
  fi
}

make down &> /dev/null && make up &> /dev/null
test_create_user
