FROM python:3.9-slim

# Install go
RUN apt-get update && apt-get install -y \
    wget \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://go.dev/dl/go1.22.4.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.22.4.linux-amd64.tar.gz
RUN rm go1.22.4.linux-amd64.tar.gz
# Set go path
ENV PATH=$PATH:/usr/local/go/bin

# Install pyadi-jif with d2/go support
WORKDIR /jif
RUN git clone https://github.com/analogdevicesinc/pyadi-jif.git -b tfcollins/webapps
WORKDIR /jif/pyadi-jif/adijif/d2
RUN go build -buildmode=c-shared -o d2lib.so d2lib.go
WORKDIR /jif/pyadi-jif
RUN pip install -e '.[cplex]'


WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY app .

ENV PORT 8000
ENV HOST 0.0.0.0

CMD [ "sh", "-c", "streamlit run --server.port ${PORT} --server.address ${HOST} /app/main.py" ]