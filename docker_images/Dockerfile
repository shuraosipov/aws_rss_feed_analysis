FROM --platform=linux/amd64 ubuntu

# install python, jq, curl, pip
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    python3 python3-pip \
    unzip

# install awscli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install

WORKDIR /var/task

