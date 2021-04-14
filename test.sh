#!/bin/bash

URL_BASE=http://localhost:5000

success() { echo -e "\e[32mOK   $1\e[0m"; }
failure() { echo -e "\e[31mFAIL $1\e[0m"; }

dc_exec() { docker-compose exec "$@"; }

rd_query() { dc_exec kvstore redis-cli --raw "$@"; }
db_query() { dc_exec database psql --csv -U postgres -d gallery -c "$1"; }
be_query() {
  token=$1; method=$2; path=$3; data=$4
  if [[ "$method" == "POST" || "$method" == "PUT" || "$method" == "PATCH" ]]
  then
    curl -sw "%{http_code}" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json' \
      -H "Authorization: Bearer $token" \
      -X "$method" "$URL_BASE/$path" --data "$data"
  else
    curl -sw "%{http_code}" \
      -H 'Accept: application/json' \
      -H "Authorization: Bearer $token" \
      -X "$method" "$URL_BASE/$path"
  fi
}

signin() { be_query '' 'POST' 'signin' '{"name":"test","email":"test@te.st"}'; }
login() { be_query '' 'POST' 'login' '{"name":"test"}'; }
token() { be_query '' 'POST' 'token' '{"code":"'$1'"}'; }

test_signin() {
  make reset &> /dev/null
  first_code=$(signin); second_code=$(signin)
  insert=$(db_query 'select * from public.user' | wc -l)
  if [[ $insert -eq 2 && $first_code -eq 204 && $second_code -eq 409 ]]; then
    success 'test_signin'
  else
    failure 'test_signin'
  fi
}


test_login_access() {
  make reset &> /dev/null
  # ask to login, generate an OTP
  signin > /dev/null; result=$(login)
  pin=$(rd_query keys '*' | tr -d '\r') # get the OTP
  if [[ $(echo $result | tail -c 4) -eq 204 && -n $pin ]]; then
    success 'test_login'
  else
    failure 'test_login'
  fi
  result=$(token $pin)
  res=$(echo $result | head -c -4 | jq -e '.access_token' &> /dev/null; echo $?)
  if [[ $(echo $result | tail -c 4) -eq 201  && $res -eq 0 ]]; then
    success 'test_access'
  else
    failure 'test_access'
  fi
}

test_list_users() {
  make reset &> /dev/null
  signin > /dev/null; login > /dev/null;
  pin=$(rd_query keys '*' | tr -d '\r')
  auth=$(echo $(token $pin) | head -c -4 | jq -e '.access_token' | tr -d '"')
  result=$(be_query $auth 'GET' 'users')
  body=$(echo $result | head -c -4 | tr -d ' ')
  code=$(echo $result | tail -c 4)
  if [[ $code -eq 200 && "$body" == '{"users":["test"]}' ]]; then
    success 'test_list_users'
  else
    failure 'test_list_users'
  fi
}

test_create_album() {
  make reset &> /dev/null
  signin > /dev/null; login > /dev/null;
  pin=$(rd_query keys '*' | tr -d '\r')
  auth=$(echo $(token $pin) | head -c -4 | jq -e '.access_token' | tr -d '"')
  result=$(be_query $auth 'POST' 'albums' '{"name":"Nouvel An 2021"}')
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  expect='{"slug": "nouvel-an-2021", "name": "Nouvel An 2021"}'
  if [[ $code -eq 201 && "$body" == "$expect" ]]; then
    success 'test_create_album'
  else
    failure 'test_create_album'
  fi
}

test_signin
test_login_access
test_list_users
test_create_album
