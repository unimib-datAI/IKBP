FROM python:3

WORKDIR /home/app

COPY . .

RUN pip install --no-cache-dir --upgrade -r /home/app/requirements.txt

CMD python main.py --host 0.0.0.0 --port 80 --distribuzione_territoriale_uffici $DISTRIBUZIONE_TERRITORIALE_UFFICI