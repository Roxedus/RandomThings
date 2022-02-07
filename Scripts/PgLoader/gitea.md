# MariaDB to postgres

1. Set up a throw-away gitea instance to seed the postgres db.

    ```ini
    [database]
    DB_TYPE = postgres
    HOST    = postgres:5432
    NAME    = gitea
    USER    = gitea
    PASSWD  = gitea
    ```

2. Load the Postgres database with contents from the MariaDB using the `gitea.load` file with pgloader.
3. Start gitea set up to use the Postgres db
4. Use built-in funtion to recreate tables

    ```sh
    docker exec -u <giteauser> -it -w /tmp gitea -v $PWD:/tmp bash -c '/app/gitea/gitea doctor recreate-table -c /data/gitea/conf/app.ini'
    ```
