@echo off
go build -ldflags "-H=windowsgui -s -w" -o nifty-reader.exe .
