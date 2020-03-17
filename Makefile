up:
	docker-compose up -d

stop:
	docker-compose stop

rebuild:
	docker-compose up -d --build

up_scale:
	docker-compose up -d --scale scruffy=5

stop_scale:
	docker-compose stop

rebuild_scale:
	docker-compose up -d --build --scale scruffy=5

clean:
	docker-compose down
