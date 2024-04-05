FROM ubuntu:22.04
RUN apt update
RUN apt install -y python-is-python3 python3-pip git curl ca-certificates
RUN curl -L -o tmp/keep-it-markdown-0.5.4.tar.gz refs/tags/0.5.4.tar.gz
RUN tar -zxvf tmp/keep-it-markdown-0.5.4.tar.gz
RUN pip install -r keep-it-markdown-0.5.4/requirements.txt
RUN pip install requests==2.23.0
RUN pip install keyrings.alt
RUN pip install git+simon-weber/gpsoauth.git@8a5212481f80312e06ba6e0a29fbcfca1f210fd1
