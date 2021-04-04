#!/bin/bash

URL_BASE=http://localhost:5000

success() { echo -e "\e[32mOK   $1\e[0m"; }
failure() { echo -e "\e[31mFAIL $1\e[0m"; }

db_query() {
  docker-compose -p dev-backend exec database \
    psql --csv -U postgres -d gallery -c "$1"
}

be_query() {
  data=$([[ "$1" == "POST" || "$1" == "PUT" ]] && echo -d $3)
  curl -sw "%{http_code}" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    -X $1 "$URL_BASE/$2" $data; echo
}

test_create_user() {
  make reset &> /dev/null
  first_code=$(
    be_query 'POST' 'users' '{"name":"tristan","email":"tristan@tic.sh"}'
  )
  second_code=$(
    be_query 'POST' 'users' '{"name":"tristan","email":"tristan@tic.sh"}'
  )
  insert=$(db_query 'select * from public.user' | wc -l)
  if [[ $insert -eq 2 && $first_code -eq 204 && $second_code -eq 409 ]]; then
    success 'test_create_user'
  else
    failure 'test_create_user'
  fi
}

test_list_users() {
  make reset &> /dev/null
  result=$(be_query 'GET' 'users')
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  if [[ $code == 200 ]]; then
    success 'test_list_users'
  else
    failure 'test_list_users'
  fi
}

make down &> /dev/null && make up &> /dev/null
test_create_user
test_list_users
