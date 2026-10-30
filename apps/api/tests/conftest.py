import os

os.environ["SECRET_KEY"] = "test-secret-key-for-deposit360-local-tests"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
