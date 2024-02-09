---
title: 'MoneyPrinter Documentation'
description: 'MoneyPrinter Documentation'
---


# Documentation related to the Money Printer UI


## Getting started



### We have two options to get started 


#### Option one: ***Local installation***



#### Install requirements
```bash
pip install -r requirements.txt
```
#### Copy .env.example and fill out values
```bash
cp .env.example .env
```
#### Run the backend server
```bash
cd Backend
python main.py
```
#### Run the frontend server
```bash
cd ../Frontend
python -m http.server 3000
```
#### Run the nuxt front end 
```bash
cd ../UI
npm install
npm run dev

```



#### Option one: ***Docker container***


1. Build the docker image
```bash
docker-compose build --no-cache
```
2. Run the docker container
```bash
docker-compose up -d
```

3. The fallowing port urls will be available


[Backend](http://localhost:8080) 

[Frontend](http://localhost:3000) -> Basic frontend -> The port will be 3000 by default in the env but you can change it in the .env

[Frontend](http://localhost:5000) -> Nuxt frontend -> The port will be 5000 by default in the env but you can change it in the .env