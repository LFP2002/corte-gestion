#!/bin/sh
# Ejecutar dentro de db con sh; secretos solo desde entorno, sin imprimirlos.
set -eu
MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot <<SQL
GRANT ALL PRIVILEGES ON \`test_${MARIADB_DATABASE}\`.* TO '$MARIADB_USER'@'%';
SQL
