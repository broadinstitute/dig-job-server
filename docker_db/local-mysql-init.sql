CREATE DATABASE job_server;
CREATE USER 'job_server'@'%' IDENTIFIED BY 'job_server';
GRANT ALL PRIVILEGES ON job_server.* TO 'job_server'@'%' WITH GRANT OPTION;
CREATE DATABASE job_server_test;
GRANT ALL PRIVILEGES ON job_server_test.* TO 'job_server'@'%' WITH GRANT OPTION;
