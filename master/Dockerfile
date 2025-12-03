FROM python:3.10-slim
WORKDIR /app
COPY master.py .
RUN pip install flask requests
CMD ["python", "master.py"]