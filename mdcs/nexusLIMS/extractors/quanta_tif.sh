#!/usr/bin/env bash

sed -e '1i[User]' -e '1,/\[User\]/d' "${1}"

