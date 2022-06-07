#!/bin/bash

echo "Messages:"
echo "-----------------------------------------"
sqlite3 "$1" "select * from messages;"
echo "-----------------------------------------"
echo 
echo "Attachments:"
echo "-----------------------------------------"
sqlite3 "$1" "select * from attachments;"
echo "-----------------------------------------"
