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

authenticate() {
  make reset &> /dev/null
  signin > /dev/null; login > /dev/null;
  pin=$(rd_query keys '*' | tr -d '\r')
  echo $(token $pin) | head -c -4 | jq -e '.access_token' | tr -d '"'
}

test_list_users() {
  auth=$(authenticate)
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
  auth=$(authenticate)
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Nouvel An 2021"}')
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  expect='{ "count": 0, "name": "Nouvel An 2021", "preview": null, "slug": "nouvel-an-2021" } '
  if [[ $code -eq 201 && "$body" == "$expect" ]]; then
    success 'test_create_album'
  else
    failure 'test_create_album'
  fi
}

test_list_albums() {
  auth=$(authenticate)
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"A"}')
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"B"}')
  result=$(be_query "$auth" 'GET' 'albums')
  expect='[ { "count": 0, "name": "A", "preview": null, "slug": "a" }, { "count": 0, "name": "B", "preview": null, "slug": "b" } ] '
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_list_albums'
  else
    failure 'test_list_albums'
  fi
}

test_get_album() {
  auth=$(authenticate)
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Album Test"}')
  slug=$(echo $result | head -c -4 | jq '.slug' | tr -d '"')
  result=$(be_query "$auth" 'GET' "albums/$slug")
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  expect='{ "count": 0, "name": "Album Test", "preview": null, "slug": "album-test" } '
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_get_album'
  else
    failure 'test_get_album'
  fi
}

test_upload_picture() {
  auth=$(authenticate)
  filehash=$(md5sum test.png | cut -d ' ' -f 1)
  curl -H "Authorization: Bearer $auth" \
    -X PUT http://localhost:5000/pic/$filehash -F 'file=@test.png'
  curl -H "Authorization: Bearer $auth" \
    -so '/tmp/test.png' http://localhost:5000/pic/$filehash
  if [[ "$(md5sum '/tmp/test.png' | cut -d ' ' -f 1)" == "$filehash" ]]; then
    success 'test_upload_picture'
  else
    failure 'test_upload_picture'
  fi
}

test_link_pic_to_album() {
  auth=$(authenticate)
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Test"}')
  slug=$(echo $result | head -c -4 | jq '.slug' | tr -d '"')

  # send file
  filehash=$(md5sum test.png | cut -d ' ' -f 1)
  curl -s -H "Authorization: Bearer $auth" \
    -X PUT http://localhost:5000/pic/$filehash -F 'file=@test.png'

  # add pic to album
  result=$(be_query "$auth" 'PATCH' "albums/$slug/pics" "{\"+\":[\"$filehash\"]}")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  if [[ $code -eq 204 ]]; then
    success 'test_add_pics_to_album'
  else
    failure 'test_add_pics_to_album'
  fi

  # verify that pic has been added
  result=$(be_query "$auth" 'GET' "albums/$slug/pics")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  expect="{ \"pics\": [ \"$filehash\" ] } "
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_get_pics_from_album'
  else
    failure 'test_get_pics_from_album'
  fi

  # verify number of pics in album details
  result=$(be_query "$auth" 'GET' "albums/$slug")
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  expect="{ \"count\": 1, \"name\": \"Test\", \"preview\": \"$filehash\", \"slug\": \"test\" } "
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_get_album_with_pics'
  else
    failure 'test_get_album_with_pics'
  fi

  # remove pic from album
  result=$(be_query "$auth" 'PATCH' "albums/$slug/pics" "{\"-\":[\"$filehash\"]}")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  if [[ $code -eq 204 ]]; then
    success 'test_remove_pics_to_album'
  else
    failure 'test_remove_pics_to_album'
  fi

  # verify that pic has been removed
  result=$(be_query "$auth" 'GET' "albums/$slug/pics")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  expect="{ \"pics\": [] } "
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_get_pics_from_album'
  else
    failure 'test_get_pics_from_album'
  fi
}

test_remove_album() {
  auth=$(authenticate)

  # add album
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Test"}')
  slug=$(echo $result | head -c -4 | jq '.slug' | tr -d '"')

  # send file
  filehash=$(md5sum test.png | cut -d ' ' -f 1)
  curl -s -H "Authorization: Bearer $auth" \
    -X PUT http://localhost:5000/pic/$filehash -F 'file=@test.png'

  # add pic to album
  result=$(be_query "$auth" 'PATCH' "albums/$slug/pics" "{\"+\":[\"$filehash\"]}")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  if [[ $code -eq 204 ]]; then
    success 'test_add_pics_to_album'
  else
    failure 'test_add_pics_to_album'
  fi

  # delete album
  result=$(be_query "$auth" 'DELETE' "albums/$slug")
  code=$(echo $result | tail -c 4)
  result=$(be_query "$auth" 'GET' 'albums')
  body=$(echo $result | head -c -4)
  if [[ $code -eq 204 && "$body" == "[] " ]]; then
    success 'test_remove_album'
  else
    failure 'test_remove_album'
  fi

  # add album again
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Test"}')
  slug=$(echo $result | head -c -4 | jq '.slug' | tr -d '"')

  # verify that pic did not survive album's deletion
  result=$(be_query "$auth" 'GET' "albums/$slug/pics")
  code=$(echo $result | tail -c 4)
  body=$(echo $result | head -c -4)
  expect="{ \"pics\": [] } "
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_remove_album_is_persistant'
  else
    failure 'test_remove_album_is_persistant'
  fi
}

test_upload_unamed_album() {
  auth=$(authenticate)
  result=$(be_query "$auth" 'POST' 'albums' '{"name":""}')
  code=$(echo $result | tail -c 4)
  if [[ $code -eq 400 ]]; then
    success 'test_upload_unamed_album'
  else
    failure 'test_upload_unamed_album'
  fi
}

test_export_config() {
  auth=$(authenticate)

  # create a test album
  result=$(be_query "$auth" 'POST' 'albums' '{"name":"Test"}')
  slug=$(echo $result | head -c -4 | jq '.slug' | tr -d '"')

  # add picture to album
  filehash=$(md5sum test.png | cut -d ' ' -f 1)
  curl -H "Authorization: Bearer $auth" \
    -X PUT http://localhost:5000/pic/$filehash -F 'file=@test.png'
  tmp=$(be_query "$auth" 'PATCH' "albums/$slug/pics" "{\"+\":[\"$filehash\"]}")

  # export config
  result=$(be_query "$auth" 'GET' 'config')
  expect='{ "albums": [ { "name": "Test", "pics": [ "7e81b0a01a4cec4c142f6f54607aa3ae" ], "slug": "test" } ], "users": [ "test" ] } '
  body=$(echo $result | head -c -4)
  code=$(echo $result | tail -c 4)
  if [[ $code -eq 200 && "$body" == "$expect" ]]; then
    success 'test_export_config'
  else
    failure 'test_export_config'
  fi
}

test_signin
test_login_access
test_list_users
test_create_album
test_list_albums
test_get_album
test_upload_picture
test_link_pic_to_album
test_remove_album
test_upload_unamed_album
test_export_config
