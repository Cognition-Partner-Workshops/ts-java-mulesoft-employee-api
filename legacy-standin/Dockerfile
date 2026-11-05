FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY legacy-standin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY legacy-standin/app.py .
COPY legacy-standin/tests /app/tests
COPY tools/parity/compare.py /app/compare.py
COPY src/main/mule/employee-services-api.xml /app/flows.xml
COPY src/main/resources/web /app/web
USER nobody
CMD ["python", "app.py"]
