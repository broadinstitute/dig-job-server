
FROM public.ecr.aws/sam/build-python3.9:latest

RUN yum install -y mysql-devel gcc python3-devel
