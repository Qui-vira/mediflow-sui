web: gunicorn -w 2 -b 0.0.0.0:$PORT frontend.app:app
coordinator: python agents/coordinator.py
intake: python agents/intake.py
verification: python agents/verification.py
resource: python agents/resource.py
