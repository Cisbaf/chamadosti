git pull
docker compose build
docker compose stop
# --remove-orphans tira do ar os containers antigos (worker, flower, redis, selenium) que não existem mais no compose
docker compose up -d --remove-orphans
