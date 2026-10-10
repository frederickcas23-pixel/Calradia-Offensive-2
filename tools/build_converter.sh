#!/bin/bash
# Builds the setup tool for Linux (dev) and Windows (shipped), embedding the current sheets.
set -e; cd "$(dirname "$0")/../converter"
mkdir -p sheets; cp ../sheets/assets.json ../sheets/sounds.json sheets/
gofmt -l . ; go vet ./...
go build -o ../build/cs2calradia-setup .
GOOS=windows GOARCH=amd64 go build -ldflags "-s -w" -o ../build/cs2calradia-setup.exe .
ls -la ../build/cs2calradia-setup.exe | awk '{print $5, $9}'
