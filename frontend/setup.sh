#!/bin/bash

sudo apt install npm
npm install vite
npm run dev -- --host

or 

sudo systemctl daemon-reload
sudo systemctl enable frontend
sudo systemctl start frontend